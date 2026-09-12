from datetime import timedelta
from typing import Any, List, Optional, Union

from aiokafka.admin import AIOKafkaAdminClient

from probirka._probes import ProbeBase
from probirka.probes._common import ClientOrFactory, require_exactly_one, resolve


class KafkaAiokafkaProbe(ProbeBase):
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

    @staticmethod
    async def _fetch_metadata(client: Any) -> None:
        if hasattr(client, 'describe_cluster'):  # AIOKafkaAdminClient
            await client.describe_cluster()
            return
        # AIOKafkaProducer exposes the low-level client as ``client``, AIOKafkaConsumer as ``_client``
        low_level = getattr(client, 'client', None) or getattr(client, '_client')  # noqa: B009
        await low_level.fetch_all_metadata()

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            await self._fetch_metadata(resolve(self._client))
            return True
        admin = AIOKafkaAdminClient(bootstrap_servers=self._bootstrap_servers)
        await admin.start()
        try:
            await admin.describe_cluster()
        finally:
            await admin.close()
        return True
