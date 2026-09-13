from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx2

from probirka._probes._http_base import HttpProbeBase

if TYPE_CHECKING:
    from collections.abc import Mapping


class HttpHttpx2Probe(HttpProbeBase):
    """
    HTTP check with `httpx2 <https://github.com/pydantic/httpx2>`_.

    Same behaviour as :class:`HttpHttpxProbe`, built on ``httpx2.AsyncClient``.
    """

    def _temporary_client(self) -> httpx2.AsyncClient:
        # the probe timeout is the only limit; httpx2 would otherwise apply its own 5 s default
        return httpx2.AsyncClient(timeout=self._timeout)

    async def _request(
        self,
        client: Any,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
    ) -> tuple[int, str | None]:
        response = await client.request(method, url, headers=headers, follow_redirects=False)
        return int(response.status_code), response.headers.get('location')
