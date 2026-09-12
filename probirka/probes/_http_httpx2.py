from typing import Any

import httpx2

from probirka.probes._http_base import HttpProbeBase


class HttpHttpx2Probe(HttpProbeBase):
    """
    HTTP check with `httpx2 <https://github.com/pydantic/httpx2>`_.

    Same behaviour as :class:`HttpHttpxProbe`, built on ``httpx2.AsyncClient``.
    """

    def _new_client(self) -> httpx2.AsyncClient:
        return httpx2.AsyncClient()

    async def _request_status(self, client: Any) -> int:
        response = await client.request(self._method, self._url, headers=self._headers)
        return int(response.status_code)
