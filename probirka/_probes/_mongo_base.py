from __future__ import annotations

from abc import abstractmethod
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, require_exactly_one
from probirka._redact import secrets_from_url

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from datetime import timedelta


class MongoProbeBase(ClientProbeBase):
    """
    Shared logic for MongoDB probes: run the ``ping`` admin command.

    Subclasses adapt a concrete driver by implementing :meth:`_new_client` and :meth:`_close_client`.
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

        :param client: A MongoDB client or a zero-argument callable returning one.
        :param url: MongoDB URI, e.g. ``mongodb://localhost:27017``. Mutually exclusive with ``client``.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe. For the ``url`` mode it is also passed to the driver as
            ``serverSelectionTimeoutMS`` so that the failure is reported by the driver, not as a bare timeout.
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
        assert self._url is not None  # noqa: S101 -- narrowed by require_exactly_one in __init__
        kwargs: dict[str, Any] = {}
        if self._timeout is not None:
            kwargs['serverSelectionTimeoutMS'] = self._timeout * 1000
        client = self._new_client(self._url, **kwargs)
        try:
            yield client
        finally:
            await self._close_client(client)

    async def _check_client(self, client: Any) -> None:
        await client.admin.command('ping')
