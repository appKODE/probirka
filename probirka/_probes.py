from abc import ABC, abstractmethod
from asyncio import iscoroutinefunction, wait_for
from datetime import datetime
from typing import Callable, Optional, Protocol

from probirka._results import ProbeResult


class Probe(
    Protocol,
):
    async def run_check(
        self,
    ) -> ProbeResult: ...


class ProbeBase(
    ABC,
):
    def __init__(
        self,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self._timeout = timeout
        self._name = name or self.__class__.__name__

    @abstractmethod
    async def _check(
        self,
    ) -> Optional[bool]:
        raise NotImplementedError

    async def run_check(
        self,
    ) -> ProbeResult:
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
    def __init__(
        self,
        func: Callable[[], Optional[bool]],
        name: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self._func = func
        super().__init__(
            name=name or func.__name__,
            timeout=timeout,
        )

    async def _check(
        self,
    ) -> Optional[bool]:
        if iscoroutinefunction(self._func):
            return await self._func()
        return self._func()
