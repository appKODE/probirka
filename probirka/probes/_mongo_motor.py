from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorClient

from probirka.probes._common import only_set
from probirka.probes._mongo_base import MongoProbeBase


class MongoMotorProbe(MongoProbeBase):
    """
    Check MongoDB availability with `Motor <https://motor.readthedocs.io/>`_ (``AsyncIOMotorClient``).

    Runs the ``ping`` admin command on an existing client (or a callable returning one),
    or on a short-lived client created from ``url``.
    """

    def _new_client(self, url: str, timeout: Optional[int]) -> Any:
        return AsyncIOMotorClient(
            url,
            **only_set(serverSelectionTimeoutMS=timeout * 1000 if timeout is not None else None),
        )

    async def _close_client(self, client: Any) -> None:
        client.close()  # synchronous in Motor
