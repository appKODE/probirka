from asyncio import get_running_loop
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from probirka._probes._mongo_base import MongoProbeBase


class MongoMotorProbe(MongoProbeBase):
    """
    Check MongoDB availability with `Motor <https://motor.readthedocs.io/>`_ (``AsyncIOMotorClient``).

    Runs the ``ping`` admin command on an existing client (or a callable returning one),
    or on a short-lived client created from ``url``.
    """

    def _new_client(self, url: str, **kwargs: Any) -> Any:
        return AsyncIOMotorClient(url, **kwargs)

    async def _close_client(self, client: Any) -> None:
        # Motor's close() is the synchronous PyMongo close(): it ends server sessions over the
        # network, so it must not run on the event loop thread
        await get_running_loop().run_in_executor(None, client.close)
