import asyncio

from probirka import ProbeBase


class SuccessProbe(ProbeBase):
    async def _check(self) -> bool:
        return True


class FailureProbe(ProbeBase):
    async def _check(self) -> bool:
        return False


class SlowProbe(ProbeBase):
    async def _check(self) -> bool:
        await asyncio.sleep(1)
        return True


class LeakyConfig:
    """An object whose ``str()`` and ``__dict__`` both carry a password, like a settings object would."""

    def __init__(self) -> None:
        self.dsn = 'postgresql://app:hunter2@db:5432/app'
        self.password = 'hunter2'

    def __str__(self) -> str:
        return self.dsn
