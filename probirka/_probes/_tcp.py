from asyncio import open_connection
from datetime import timedelta
from typing import Optional, Union

from probirka._probes import ProbeBase


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
        name: Optional[str] = None,
        timeout: Optional[int] = None,
        success_ttl: Optional[Union[int, timedelta]] = None,
        failed_ttl: Optional[Union[int, timedelta]] = None,
    ) -> None:
        """
        Initialize the probe.

        :param host: Host name or IP address to connect to.
        :param port: TCP port.
        :param name: The name of the probe. Defaults to ``'TcpProbe'``.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        """
        super().__init__(name=name, timeout=timeout, success_ttl=success_ttl, failed_ttl=failed_ttl)
        self._host = host
        self._port = port

    async def _check(self) -> Optional[bool]:
        _, writer = await open_connection(self._host, self._port)
        writer.close()
        await writer.wait_closed()
        return True
