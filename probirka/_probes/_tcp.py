from __future__ import annotations

from asyncio import open_connection
from typing import TYPE_CHECKING

from probirka._probes._base import ProbeBase

if TYPE_CHECKING:
    from datetime import timedelta


class TcpProbe(ProbeBase):
    """
    Check that a TCP connection to ``host:port`` can be established.

    Uses only the standard library, so it works without any extra packages.
    Connection errors (``ConnectionRefusedError``, ``socket.gaierror``, ...) are reported
    in :attr:`ProbeResult.error`.
    """

    def __init__(
        self,
        host: str,
        port: int,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> None:
        """
        Initialize the probe.

        :param host: Host name or IP address to connect to.
        :param port: TCP port.
        :param name: The name of the probe. Defaults to ``'TcpProbe'``.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        :param allow_failure: If True, a failure of this probe does not affect the overall result.
        """
        super().__init__(
            name=name,
            timeout=timeout,
            success_ttl=success_ttl,
            failed_ttl=failed_ttl,
            allow_failure=allow_failure,
        )
        self._host = host
        self._port = port

    async def _check(self) -> bool | None:
        _, writer = await open_connection(self._host, self._port)
        writer.close()
        await writer.wait_closed()
        return True
