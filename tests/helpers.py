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
