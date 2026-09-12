from abc import abstractmethod
from datetime import timedelta
from typing import Any, AsyncContextManager, Collection, Mapping, Optional, Union

from probirka._probes import ProbeBase
from probirka.probes._common import ClientOrFactory, ProbeFailure, resolve


class HttpProbeBase(ProbeBase):
    """
    Shared logic for HTTP probes: send one request and compare the status code.

    Subclasses adapt a concrete client library by implementing :meth:`_new_client`
    (a temporary client for when none was passed) and :meth:`_request_status`.
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = 'GET',
        expected_status: Collection[int] = (200,),
        headers: Optional[Mapping[str, str]] = None,
        client: Optional[ClientOrFactory[Any]] = None,
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param url: URL to request.
        :param method: HTTP method, ``GET`` by default.
        :param expected_status: Status codes treated as healthy, ``(200,)`` by default.
        :param headers: Extra request headers.
        :param client: An existing client/session (or a callable returning one). If omitted, a
            temporary one is created per check.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._url = url
        self._method = method
        self._expected_status = frozenset(expected_status)
        self._headers = dict(headers) if headers else None
        self._client = client

    @abstractmethod
    def _new_client(self) -> AsyncContextManager[Any]:
        """Create a temporary client, used when no client was passed."""
        raise NotImplementedError

    @abstractmethod
    async def _request_status(self, client: Any) -> int:
        """Send the request with ``client`` and return the response status code."""
        raise NotImplementedError

    async def _check(self) -> Optional[bool]:
        if self._client is not None:
            status = await self._request_status(resolve(self._client))
        else:
            async with self._new_client() as client:
                status = await self._request_status(client)
        if status not in self._expected_status:
            raise ProbeFailure(f'unexpected status {status}')
        return True
