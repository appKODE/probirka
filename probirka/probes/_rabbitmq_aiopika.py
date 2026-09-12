from datetime import timedelta
from typing import Any, Optional, Union

import aio_pika

from probirka._probes import ProbeBase
from probirka.probes._common import ClientOrFactory, ProbeFailure, require_exactly_one, resolve


class RabbitmqAiopikaProbe(ProbeBase):
    """
    Check RabbitMQ availability with `aio-pika <https://github.com/mosquito/aio-pika>`_.

    Opens and closes a channel on an existing connection (or a callable returning one), or on a
    short-lived connection established from ``url``. A closed existing connection is a failure.
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

        :param client: ``aio_pika`` connection (``AbstractConnection``) or a callable returning one.
        :param url: AMQP URL, e.g. ``amqp://guest:guest@localhost/``. Mutually exclusive with ``client``.
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
    async def _open_channel(connection: Any) -> None:
        if connection.is_closed:
            raise ProbeFailure('connection is closed')
        channel = await connection.channel()
        await channel.close()

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            await self._open_channel(resolve(self._client))
            return True
        connection = await aio_pika.connect(self._url)
        try:
            await self._open_channel(connection)
        finally:
            await connection.close()
        return True
