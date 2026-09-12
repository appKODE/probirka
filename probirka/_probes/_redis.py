from datetime import timedelta
from typing import Any, Optional, Union

from redis.asyncio import Redis

from probirka._probes import ProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure, require_exactly_one, resolve


class RedisProbe(ProbeBase):
    """
    Check Redis availability with `redis-py <https://github.com/redis/redis-py>`_ (``redis.asyncio``).

    Sends ``PING`` to an existing :class:`redis.asyncio.Redis` client (or a callable returning one),
    or to a short-lived client created from ``url``.
    """

    def __init__(
        self,
        client: Optional[ClientOrFactory[Any]] = None,
        *,
        url: Optional[str] = None,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param client: ``redis.asyncio.Redis`` (or cluster/sentinel client with ``ping``) or a callable returning one.
        :param url: Redis URL, e.g. ``redis://localhost:6379/0``. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        require_exactly_one(client=client, url=url)
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._client = client
        self._url = url

    @staticmethod
    async def _ping(client: Any) -> None:
        if not await client.ping():
            raise ProbeFailure('PING failed')

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            await self._ping(resolve(self._client))
            return True
        assert self._url is not None
        client = Redis.from_url(self._url)
        try:
            await self._ping(client)
        finally:
            # redis>=5 has aclose(); close() is the redis 4.x name
            close = getattr(client, 'aclose', None) or client.close
            await close()
        return True
