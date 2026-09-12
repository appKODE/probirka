from typing import Any

import httpx

from probirka._probes._http_base import HttpProbeBase


class HttpHttpxProbe(HttpProbeBase):
    """
    HTTP check with `httpx <https://www.python-httpx.org/>`_.

    Sends a request with an existing :class:`httpx.AsyncClient` (or a callable returning one)
    or a temporary one, and fails unless the status code is in ``expected_status``.
    """

    def _temporary_client(self) -> httpx.AsyncClient:
        # the probe timeout is the only limit; httpx would otherwise apply its own 5 s default
        return httpx.AsyncClient(timeout=self._timeout)

    async def _request_status(self, client: Any) -> int:
        response = await client.request(self._method, self._url, headers=self._headers)
        return int(response.status_code)
