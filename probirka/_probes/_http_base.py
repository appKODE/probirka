from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import timedelta
from typing import Any

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure


class HttpProbeBase(ClientProbeBase):
    """
    Shared logic for HTTP probes: send one request and compare the status code.

    Subclasses adapt a concrete client library by implementing :meth:`_temporary_client`
    (a client for when none was passed, honouring the probe ``timeout``) and :meth:`_request_status`.
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = 'GET',
        expected_status: int | Collection[int] = (200,),
        headers: Mapping[str, str] | None = None,
        client: ClientOrFactory[Any] | None = None,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
    ) -> None:
        """
        Initialize the probe.

        :param url: URL to request.
        :param method: HTTP method, ``GET`` by default.
        :param expected_status: Status code or codes treated as healthy, ``(200,)`` by default.
        :param headers: Extra request headers.
        :param client: An existing client/session (or a callable returning one). If omitted, a
            temporary one is created per check with the probe ``timeout`` as its request timeout.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._url = url
        self._method = method
        self._expected_status = frozenset([expected_status] if isinstance(expected_status, int) else expected_status)
        self._headers = dict(headers) if headers else None
        self._client = client

    async def _request_status(self, client: Any) -> int:
        """Send the request with ``client`` and return the response status code."""
        raise NotImplementedError

    async def _check_client(self, client: Any) -> None:
        status = await self._request_status(client)
        if status not in self._expected_status:
            raise ProbeFailure(f'unexpected status {status}')
