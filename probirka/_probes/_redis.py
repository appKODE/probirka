from datetime import timedelta
from typing import Any, AsyncContextManager, Optional, Union

from redis.asyncio import Redis

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure, require_exactly_one


class RedisProbe(ClientProbeBase):
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

    def _temporary_client(self) -> AsyncContextManager[Any]:
        assert self._url is not None
        # ``Redis`` is an async context manager since redis-py 4.2; ``__aexit__`` closes the client
        return Redis.from_url(self._url)

    async def _check_client(self, client: Any) -> None:
        if not await client.ping():
            raise ProbeFailure('PING failed')
