from abc import abstractmethod
from datetime import timedelta
from typing import Any, Optional, Union

from probirka._probes import ProbeBase
from probirka.probes._common import ClientOrFactory, require_exactly_one, resolve


class MongoProbeBase(ProbeBase):
    """
    Shared logic for MongoDB probes: run the ``ping`` admin command.

    Subclasses adapt a concrete driver by implementing :meth:`_new_client` and :meth:`_close_client`.
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

        :param client: A MongoDB client or a zero-argument callable returning one.
        :param url: MongoDB URI, e.g. ``mongodb://localhost:27017``. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe. For the ``url`` mode it is also used as the driver's
            ``serverSelectionTimeoutMS`` so that the driver's 30 s default does not hide it.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        require_exactly_one(client=client, url=url)
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._client = client
        self._url = url

    @abstractmethod
    def _new_client(self, url: str, timeout: Optional[int]) -> Any:
        """Create a temporary client for ``url``."""
        raise NotImplementedError

    @abstractmethod
    async def _close_client(self, client: Any) -> None:
        """Close a temporary client."""
        raise NotImplementedError

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            await resolve(self._client).admin.command('ping')
            return True
        client = self._new_client(self._url, self._timeout)  # type: ignore[arg-type]
        try:
            await client.admin.command('ping')
        finally:
            await self._close_client(client)
        return True
