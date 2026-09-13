from __future__ import annotations

from typing import TYPE_CHECKING, Any

from redis.asyncio import Redis

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure, require_exactly_one
from probirka._redact import secrets_from_url

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager
    from datetime import timedelta


class RedisProbe(ClientProbeBase):
    """
    Check Redis availability with `redis-py <https://github.com/redis/redis-py>`_ (``redis.asyncio``).

    Sends ``PING`` to an existing :class:`redis.asyncio.Redis` client (or a callable returning one),
    or to a short-lived client created from ``url``.
    """

    def __init__(
        self,
        client: ClientOrFactory[Any] | None = None,
        *,
        url: str | None = None,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> None:
        """
        Initialize the probe.

        :param client: ``redis.asyncio.Redis`` (or cluster/sentinel client with ``ping``) or a callable returning one.
        :param url: Redis URL, e.g. ``redis://localhost:6379/0``. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        :param allow_failure: If True, a failure of this probe does not affect the overall result.
        """
        require_exactly_one(client=client, url=url)
        super().__init__(
            name=name,
            timeout=timeout,
            success_ttl=success_ttl,
            failed_ttl=failed_ttl,
            allow_failure=allow_failure,
        )
        self._client = client
        self._url = url
        self._register_secrets(*secrets_from_url(url))

    def _temporary_client(self) -> AbstractAsyncContextManager[Any]:
        assert self._url is not None  # noqa: S101 -- narrowed by require_exactly_one in __init__
        # ``Redis`` is an async context manager since redis-py 4.2; ``__aexit__`` closes the client
        return Redis.from_url(self._url)

    async def _check_client(self, client: Any) -> None:
        if not await client.ping():
            msg = 'PING failed'
            raise ProbeFailure(msg)
