from typing import Any, Optional

from pymongo import AsyncMongoClient

from probirka._probes._common import only_set
from probirka._probes._mongo_base import MongoProbeBase


class MongoPymongoProbe(MongoProbeBase):
    """
    Check MongoDB availability with the native async client of `PyMongo <https://pymongo.readthedocs.io/>`_
    (``pymongo.AsyncMongoClient``, PyMongo >= 4.9).

    Runs the ``ping`` admin command on an existing client (or a callable returning one),
    or on a short-lived client created from ``url``.
    """

    def _new_client(self, url: str, timeout: Optional[int]) -> Any:
        return AsyncMongoClient(
            url,
            **only_set(serverSelectionTimeoutMS=timeout * 1000 if timeout is not None else None),
        )

    async def _close_client(self, client: Any) -> None:
        await client.close()
