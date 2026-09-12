from __future__ import annotations

from abc import abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any

from probirka._probes import ProbeBase
from probirka._probes._common import ClientOrFactory, resolve


class ClientProbeBase(ProbeBase):
    """
    Shared lifecycle for probes that talk to a service through a client object.

    Subclasses store the user's client (or factory) in ``_client`` and implement two hooks:
    :meth:`_temporary_client`, an async context manager that opens and closes a short-lived
    client from the connection string, and :meth:`_check_client`, the actual check.
    An existing client is never closed by the probe.
    """

    _client: ClientOrFactory[Any] | None = None

    @abstractmethod
    def _temporary_client(self) -> AbstractAsyncContextManager[Any]:
        """Open a short-lived client from the connection string; used when no client was passed."""
        raise NotImplementedError

    @abstractmethod
    async def _check_client(self, client: Any) -> None:
        """Run the check against ``client``; raise on failure."""
        raise NotImplementedError

    async def _check(self) -> bool | None:
        if self._client is not None:
            await self._check_client(resolve(self._client))
            return True
        async with self._temporary_client() as client:
            await self._check_client(client)
        return True
