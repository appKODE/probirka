from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncIterator, Optional, Union

import asyncpg

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, require_exactly_one


class PostgresAsyncpgProbe(ClientProbeBase):
    """
    Check PostgreSQL availability with `asyncpg <https://github.com/MagicStack/asyncpg>`_.

    Runs ``SELECT 1`` on an existing :class:`asyncpg.Pool` / :class:`asyncpg.Connection`
    (or a callable returning one), or on a short-lived connection opened from ``dsn``.
    """

    def __init__(
        self,
        client: Optional[ClientOrFactory[Any]] = None,
        *,
        dsn: Optional[str] = None,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param client: ``asyncpg.Pool``, ``asyncpg.Connection`` or a zero-argument callable returning one.
        :param dsn: PostgreSQL DSN, e.g. ``postgresql://user:pass@host:5432/db``. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        require_exactly_one(client=client, dsn=dsn)
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._client = client
        self._dsn = dsn

    @asynccontextmanager
    async def _temporary_client(self) -> AsyncIterator[Any]:
        conn = await asyncpg.connect(self._dsn)
        try:
            yield conn
        finally:
            await conn.close()

    async def _check_client(self, client: Any) -> None:
        await client.fetchval('SELECT 1')
