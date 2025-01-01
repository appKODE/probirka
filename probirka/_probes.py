from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction, wait_for
from datetime import datetime
from typing import Callable, Optional, Protocol

from probirka._results import ProbeResult


class Probe(
    Protocol,
):
    """
    Protocol for a probe that can be run to check health.
    """

    async def run_check(
        self,
    ) -> ProbeResult: ...


class ProbeBase(
    ABC,
):
    """
    Abstract base class for a probe.
    """

    def __init__(
        self,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Initialize the probe.

        :param name: The name of the probe.
        :param timeout: The timeout for the probe.
        """
        self._timeout = timeout
        self._name = name or self.__class__.__name__

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
        started_at = datetime.now()
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
        finally:
            task.close()
        return ProbeResult(
            ok=False if result is None else result,
            started_at=started_at,
            elapsed=datetime.now() - started_at,
            name=self._name,
            error=error,
        )


class CallableProbe(
    ProbeBase,
):
    """
    A probe that wraps a callable function.
    """

    def __init__(
        self, func: Callable[[], Optional[bool]], name: Optional[str] = None, timeout: Optional[int] = None
    ) -> None:
        """
        Initialize the callable probe.

        :param func: The callable function to wrap.
        :param name: The name of the probe.
        :param timeout: The timeout for the probe.
        """
        self._func = func
        super().__init__(
            name=name or func.__name__,
            timeout=timeout,
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
