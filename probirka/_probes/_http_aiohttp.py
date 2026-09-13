from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import aiohttp

from probirka._probes._http_base import HttpProbeBase


class HttpAiohttpProbe(HttpProbeBase):
    """
    HTTP check with `aiohttp <https://docs.aiohttp.org/>`_.

    Sends a request with an existing :class:`aiohttp.ClientSession` (or a callable returning one)
    or a temporary one, and fails unless the status code is in ``expected_status``.
    """

    def _temporary_client(self) -> aiohttp.ClientSession:
        # the probe timeout is the only limit; aiohttp would otherwise apply its own 5 min default
        return aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._timeout))

    async def _request(
        self,
        client: Any,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
    ) -> tuple[int, str | None]:
        async with client.request(method, url, headers=headers, allow_redirects=False) as response:
            return int(response.status), response.headers.get('Location')
