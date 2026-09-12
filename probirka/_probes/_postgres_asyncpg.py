from datetime import timedelta
from typing import Any, Optional, Union

import asyncpg

from probirka._probes import ProbeBase
from probirka._probes._common import ClientOrFactory, require_exactly_one, resolve


class PostgresAsyncpgProbe(ProbeBase):
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

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            await resolve(self._client).fetchval('SELECT 1')
            return True
        conn = await asyncpg.connect(self._dsn)
        try:
            await conn.fetchval('SELECT 1')
        finally:
            await conn.close()
        return True
