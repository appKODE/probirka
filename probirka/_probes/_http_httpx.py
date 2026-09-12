from typing import Any

import httpx

from probirka._probes._http_base import HttpProbeBase


class HttpHttpxProbe(HttpProbeBase):
    """
    HTTP check with `httpx <https://www.python-httpx.org/>`_.

    Sends a request with an existing :class:`httpx.AsyncClient` (or a callable returning one)
    or a temporary one, and fails unless the status code is in ``expected_status``.
    """

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient()

    async def _request_status(self, client: Any) -> int:
        response = await client.request(self._method, self._url, headers=self._headers)
        return int(response.status_code)
