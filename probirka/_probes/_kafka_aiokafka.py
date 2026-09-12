from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncIterator, List, Optional, Union

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, require_exactly_one


class KafkaAiokafkaProbe(ClientProbeBase):
    """
    Check Kafka availability with `aiokafka <https://github.com/aio-libs/aiokafka>`_.

    Fetches cluster metadata through an existing, already started ``AIOKafkaProducer``,
    ``AIOKafkaConsumer`` or ``AIOKafkaAdminClient`` (or a callable returning one), or through a
    short-lived admin client connected to ``bootstrap_servers``.
    """

    def __init__(
        self,
        client: Optional[ClientOrFactory[Any]] = None,
        *,
        bootstrap_servers: Optional[Union[str, List[str]]] = None,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param client: Started ``AIOKafkaProducer``/``AIOKafkaConsumer``/``AIOKafkaAdminClient`` or a callable
            returning one.
        :param bootstrap_servers: ``host:port`` or a list of them. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        require_exactly_one(client=client, bootstrap_servers=bootstrap_servers)
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._client = client
        self._bootstrap_servers = bootstrap_servers

    @asynccontextmanager
    async def _temporary_client(self) -> AsyncIterator[Any]:
        admin = AIOKafkaAdminClient(bootstrap_servers=self._bootstrap_servers)
        try:
            await admin.start()
            yield admin
        finally:
            await admin.close()

    async def _check_client(self, client: Any) -> None:
        # every branch fetches cluster metadata through a public API
        if isinstance(client, AIOKafkaAdminClient):
            await client.describe_cluster()
        elif isinstance(client, AIOKafkaProducer):
            await client.client.fetch_all_metadata()
        elif isinstance(client, AIOKafkaConsumer):
            await client.topics()
        else:
            raise TypeError(
                f'expected AIOKafkaProducer, AIOKafkaConsumer or AIOKafkaAdminClient, got {type(client).__name__}'
            )
