from abc import abstractmethod
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any, AsyncIterator, Dict, Optional, Union

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, require_exactly_one


class MongoProbeBase(ClientProbeBase):
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
        :param timeout: The timeout for the probe. For the ``url`` mode it is also passed to the driver as
            ``serverSelectionTimeoutMS`` so that the failure is reported by the driver, not as a bare timeout.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        require_exactly_one(client=client, url=url)
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._client = client
        self._url = url

    @abstractmethod
    def _new_client(self, url: str, **kwargs: Any) -> Any:
        """Create a temporary client for ``url`` with the driver keyword arguments."""
        raise NotImplementedError

    @abstractmethod
    async def _close_client(self, client: Any) -> None:
        """Close a temporary client."""
        raise NotImplementedError

    @asynccontextmanager
    async def _temporary_client(self) -> AsyncIterator[Any]:
        assert self._url is not None
        kwargs: Dict[str, Any] = {}
        if self._timeout is not None:
            kwargs['serverSelectionTimeoutMS'] = self._timeout * 1000
        client = self._new_client(self._url, **kwargs)
        try:
            yield client
        finally:
            await self._close_client(client)

    async def _check_client(self, client: Any) -> None:
        await client.admin.command('ping')
