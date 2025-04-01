from abc import abstractmethod
from asyncio import iscoroutinefunction, wait_for
from datetime import datetime, timedelta
from typing import Callable, Optional, Union, Dict, Any, Protocol

from probirka._results import ProbeResult


class Probe(Protocol):
    """
    Protocol defining the interface for a probe.
    """

    @property
    def info(self) -> Optional[Dict[str, Any]]: ...

    def add_info(self, name: str, value: Any) -> None: ...

    async def run_check(self) -> ProbeResult: ...


class ProbeBase:
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

        if self._last_result is not None:
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
                        info=self._last_result.info or {},
                        cached=bool(self._success_ttl is not None or self._failed_ttl is not None),
                    )

        started_at = now
        error = None
        task = self._check()
        try:
            result = await wait_for(
                fut=task,
                timeout=self._timeout,
            )
            if result is None:
                result = True
        except Exception as exc:
            result = False
            error = str(exc)

        probe_result = ProbeResult(
            ok=False if result is None else result,
            started_at=started_at,
            elapsed=datetime.now() - started_at,
            name=self._name,
            error=error,
            info=self._info or {},
            cached=False,
        )

        if self._success_ttl is not None or self._failed_ttl is not None:
            ttl = self._success_ttl if probe_result.ok else self._failed_ttl
            if ttl is not None:
                self._last_result = probe_result

        return probe_result


class CallableProbe(ProbeBase):
    """
    A probe that wraps a callable function.
    """

    def __init__(
        self,
        func: Callable[[], Optional[bool]],
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
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
        return self._func()
