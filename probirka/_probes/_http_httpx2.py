from typing import Any

import httpx2

from probirka._probes._http_base import HttpProbeBase


class HttpHttpx2Probe(HttpProbeBase):
    """
    HTTP check with `httpx2 <https://github.com/pydantic/httpx2>`_.

    Same behaviour as :class:`HttpHttpxProbe`, built on ``httpx2.AsyncClient``.
    """

    def _temporary_client(self) -> httpx2.AsyncClient:
        # the probe timeout is the only limit; httpx2 would otherwise apply its own 5 s default
        return httpx2.AsyncClient(timeout=self._timeout)

    async def _request_status(self, client: Any) -> int:
        response = await client.request(self._method, self._url, headers=self._headers)
        return int(response.status_code)
