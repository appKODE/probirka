from abc import ABC, abstractmethod
from asyncio import TimeoutError as AsyncTimeoutError, get_running_loop, iscoroutinefunction, wait_for
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional, Protocol, Union

from probirka._results import ProbeResult


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


class Probe(Protocol):
    """
    Protocol defining the interface for a probe.
    """

    @property
    def name(self) -> str:
        """Probe name used in results."""
        ...

    @property
    def info(self) -> Optional[Dict[str, Any]]:
        """Metadata attached to the probe, ``None`` if nothing was added."""
        ...

    def add_info(self, name: str, value: Any) -> None:
        """Attach a key/value pair to the probe result."""
        ...

    async def run_check(self) -> ProbeResult:
        """Run the check and return its result; must not raise."""
        ...


class ProbeBase(ABC):
    """
    Base implementation of a probe.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param name: The name of the probe.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Cache duration for failed results. If None, failed results are not cached.
        """
        self._timeout = timeout
        self._name = name or self.__class__.__name__
        self._success_ttl = timedelta(seconds=success_ttl) if isinstance(success_ttl, int) else success_ttl
        self._failed_ttl = timedelta(seconds=failed_ttl) if isinstance(failed_ttl, int) else failed_ttl
        self._last_result: Optional[ProbeResult] = None
        self._info: Optional[Dict[str, Any]] = None

    @property
    def name(
        self,
    ) -> str:
        """
        Get the name of the probe.

        :return: The name of the probe.
        """
        return self._name

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
    ) -> Optional[Dict[str, Any]]:
        """
        Get the information added to the probe result.

        :return: The information added to the probe result.
        """
        return self._info

    @abstractmethod
    async def _check(
        self,
    ) -> Optional[bool]:
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
        now = datetime.now()
        use_cache = bool(self._success_ttl or self._failed_ttl)

        if self._last_result:
            last_check_time = self._last_result.started_at + self._last_result.elapsed
            ttl = self._success_ttl if self._last_result.ok else self._failed_ttl
            if ttl is not None:
                cache_until = last_check_time + ttl
                if now < cache_until:
                    return ProbeResult(
                        ok=self._last_result.ok,
                        started_at=self._last_result.started_at,
                        elapsed=self._last_result.elapsed,
                        name=self._last_result.name,
                        error=self._last_result.error,
                        info=self._last_result.info,
                        cached=True,
                    )

        started_at = now
        error = None
        try:
            result = await wait_for(
                fut=self._check(),
                timeout=self._timeout,
            )
            ok = True if result is None else bool(result)
        except AsyncTimeoutError:
            ok = False
            error = f'TimeoutError: probe timed out after {self._timeout}s'
        except Exception as exc:
            ok = False
            error = format_error(exc)

        probe_result = ProbeResult(
            ok=ok,
            started_at=started_at,
            elapsed=datetime.now() - started_at,
            name=self._name,
            error=error,
            info=self._info,
            cached=False if use_cache else None,
        )

        if use_cache:
            ttl = self._success_ttl if probe_result.ok else self._failed_ttl
            if ttl is not None:
                self._last_result = probe_result

        return probe_result


class CallableProbe(ProbeBase):
    """
    A probe that wraps a callable function.

    Coroutine functions are awaited directly. Plain functions are executed in the
    event loop's default executor so they neither block the loop nor escape the
    probe timeout. Note that on timeout the worker thread keeps running until the
    function returns; only the wait is cancelled.
    """

    def __init__(
        self,
        func: Callable[[], Optional[bool]],
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param func: Sync or async callable returning ``True``/``None`` on success, ``False`` on failure.
        :param name: The name of the probe. Defaults to ``func.__name__``.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results. If None, successful results are not cached.
        :param failed_ttl: Cache duration for failed results. If None, failed results are not cached.
        """
        self._func = func
        super().__init__(
            name=name or func.__name__,
            timeout=timeout,
            success_ttl=success_ttl,
            failed_ttl=failed_ttl,
        )

    async def _check(
        self,
    ) -> Optional[bool]:
        """
        Perform the check by calling the function.

        :return: The result of the function call.
        """
        if iscoroutinefunction(self._func):
            return await self._func()
        return await get_running_loop().run_in_executor(None, self._func)
