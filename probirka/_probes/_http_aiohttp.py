from typing import Any

import aiohttp

from probirka._probes._http_base import HttpProbeBase


class HttpAiohttpProbe(HttpProbeBase):
    """
    HTTP check with `aiohttp <https://docs.aiohttp.org/>`_.

    Sends a request with an existing :class:`aiohttp.ClientSession` (or a callable returning one)
    or a temporary one, and fails unless the status code is in ``expected_status``.
    """

    def _new_client(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession()

    async def _request_status(self, client: Any) -> int:
        async with client.request(self._method, self._url, headers=self._headers) as response:
            return int(response.status)
