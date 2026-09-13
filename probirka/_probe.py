"""The core a probe is built on: the protocol, the base implementation, the callable wrapper, the failure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from asyncio import get_running_loop, wait_for
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from inspect import isawaitable, iscoroutinefunction
from time import monotonic
from typing import Any, Protocol, TypeAlias

from probirka._redact import redact_secrets
from probirka._results import ProbeResult

ProbeCallable: TypeAlias = Callable[[], bool | Awaitable[bool | None] | None]
"""Zero-argument sync or async callable returning ``True``/``None`` on success, ``False`` on failure."""


def format_error(exc: BaseException) -> str:
    """
    Format an exception for the ``error`` field of a result.

    Always includes the exception type so that exceptions with an empty
    message (``TimeoutError``, ``NotImplementedError``, ...) stay informative.

    :param exc: The exception to format.
    :return: ``'ExcType: message'`` or just ``'ExcType'`` when the message is empty.
    """
    message = str(exc)
    return f'{type(exc).__name__}: {message}' if message else type(exc).__name__


class ProbeFailure(Exception):
    """
    Raised by a probe when the dependency answered, but not the way a healthy one should.

    Examples: Redis replied to ``PING`` with something other than ``True``, an HTTP endpoint
    returned an unexpected status code. The message ends up in :attr:`ProbeResult.error`.
    """


class Probe(Protocol):
    """Protocol defining the interface for a probe."""

    @property
    def name(self) -> str:
        """Probe name used in results."""
        ...

    @property
    def info(self) -> dict[str, Any] | None:
        """Metadata attached to the probe, ``None`` if nothing was added."""
        ...

    def add_info(self, name: str, value: Any) -> None:
        """Attach a key/value pair to the probe result."""
        ...

    async def run_check(self) -> ProbeResult:
        """Run the check and return its result; must not raise."""
        ...


class ProbeBase(ABC):
    """Base implementation of a probe."""

    def __init__(
        self,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> None:
        """
        Initialize the probe.

        :param name: The name of the probe.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Cache duration for failed results. If None, failed results are not cached.
        :param allow_failure: If True, a failure of this probe does not affect the overall
            :attr:`ProbirkaResult.ok`; the failure is still visible in the probe's own result.
        """
        self._timeout = timeout
        self._allow_failure = allow_failure
        self._name = name or self.__class__.__name__
        self._success_ttl = timedelta(seconds=success_ttl) if isinstance(success_ttl, int) else success_ttl
        self._failed_ttl = timedelta(seconds=failed_ttl) if isinstance(failed_ttl, int) else failed_ttl
        self._last_result: ProbeResult | None = None
        self._cache_until: float | None = None
        self._info: dict[str, Any] | None = None
        self._secrets: tuple[str, ...] = ()

    @property
    def name(
        self,
    ) -> str:
        """
        Get the name of the probe.

        :return: The name of the probe.
        """
        return self._name

    @property
    def allow_failure(
        self,
    ) -> bool:
        """
        Whether this probe may fail without affecting the overall result.

        :return: The ``allow_failure`` setting of the probe.
        """
        return self._allow_failure

    def add_info(
        self,
        name: str,
        value: Any,
    ) -> None:
        """
        Add information to the probe result.

        :param name: The name of the information.
        :param value: The value of the information.
        """
        if self._info is None:
            self._info = {}
        self._info[name] = value

    @property
    def info(
        self,
    ) -> dict[str, Any] | None:
        """
        Get the information added to the probe result.

        :return: The information added to the probe result.
        """
        return self._info

    def _register_secrets(
        self,
        *values: str,
    ) -> None:
        """
        Remember values that must never appear in :attr:`ProbeResult.error`.

        Ready-made probes register the password of their connection string and the values of
        their request headers; a custom probe can register whatever it hands to a client
        library. When a check fails, every occurrence of these values in the exception message
        is replaced with ``'***'``. Values shorter than four characters are ignored.

        :param values: The secret values.
        """
        self._secrets = (*self._secrets, *values)

    @abstractmethod
    async def _check(
        self,
    ) -> bool | None:
        """
        Perform the check.

        :return: The result of the check.
        """
        raise NotImplementedError

    async def run_check(
        self,
    ) -> ProbeResult:
        """
        Run the check and return the result.

        :return: The result of the check.
        """
        use_cache = bool(self._success_ttl or self._failed_ttl)

        if self._last_result and self._cache_until is not None and monotonic() < self._cache_until:
            return ProbeResult(
                ok=self._last_result.ok,
                started_at=self._last_result.started_at,
                elapsed=self._last_result.elapsed,
                name=self._last_result.name,
                error=self._last_result.error,
                info=self._last_result.info,
                cached=True,
                allow_failure=self._allow_failure,
            )

        started_at = datetime.now(UTC).astimezone()
        start = monotonic()
        error = None
        try:
            result = await wait_for(
                fut=self._check(),
                timeout=self._timeout,
            )
            ok = True if result is None else bool(result)
        except TimeoutError:
            ok = False
            error = f'TimeoutError: probe timed out after {self._timeout}s'
        except Exception as exc:  # noqa: BLE001 -- a probe never raises, the error goes to the result
            ok = False
            error = redact_secrets(format_error(exc), self._secrets)

        probe_result = ProbeResult(
            ok=ok,
            started_at=started_at,
            elapsed=timedelta(seconds=monotonic() - start),
            name=self._name,
            error=error,
            info=self._info,
            cached=False if use_cache else None,
            allow_failure=self._allow_failure,
        )

        if use_cache:
            ttl = self._success_ttl if probe_result.ok else self._failed_ttl
            if ttl is not None:
                self._last_result = probe_result
                self._cache_until = monotonic() + ttl.total_seconds()

        return probe_result


class CallableProbe(ProbeBase):
    """
    A probe that wraps a callable function.

    Coroutine functions are awaited directly. Plain functions are executed in the
    event loop's default executor so they neither block the loop nor escape the
    probe timeout. If a plain callable returns an awaitable (for example an object
    with an ``async def __call__`` or a function returning a coroutine), that
    awaitable is awaited too. Note that on timeout the worker thread keeps running
    until the function returns; only the wait is cancelled.
    """

    def __init__(
        self,
        func: ProbeCallable,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> None:
        """
        Initialize the probe.

        :param func: Sync or async callable returning ``True``/``None`` on success, ``False`` on failure.
        :param name: The name of the probe. Defaults to ``func.__name__``, falling back to the
            class name for callables without one (``functools.partial``, objects with ``__call__``).
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Cache duration for failed results. If None, failed results are not cached.
        :param allow_failure: If True, a failure of this probe does not affect the overall result.
        """
        self._func = func
        super().__init__(
            name=name or getattr(func, '__name__', type(func).__name__),
            timeout=timeout,
            success_ttl=success_ttl,
            failed_ttl=failed_ttl,
            allow_failure=allow_failure,
        )

    async def _check(
        self,
    ) -> bool | None:
        """
        Perform the check by calling the function.

        :return: The result of the function call.
        """
        if iscoroutinefunction(self._func):
            return await self._func()
        result = await get_running_loop().run_in_executor(None, self._func)
        if isawaitable(result):
            return await result
        return result
