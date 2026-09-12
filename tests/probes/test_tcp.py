import asyncio
import socket

import pytest

from probirka import TcpProbe


@pytest.mark.asyncio
async def test_tcp_probe_success() -> None:
    server = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await TcpProbe('127.0.0.1', port).run_check()
    finally:
        server.close()
        await server.wait_closed()

    assert result.ok is True
    assert result.error is None
    assert result.name == 'TcpProbe'


@pytest.mark.asyncio
async def test_tcp_probe_connection_refused() -> None:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]

    result = await TcpProbe('127.0.0.1', port, name='closed').run_check()

    assert result.ok is False
    assert result.name == 'closed'
    assert result.error is not None
    assert 'ConnectionRefusedError' in result.error or 'OSError' in result.error


@pytest.mark.asyncio
async def test_tcp_probe_timeout() -> None:
    # 10.255.255.1 is a non-routable address: SYN is never answered
    result = await TcpProbe('10.255.255.1', 9, timeout=1).run_check()

    assert result.ok is False
    assert result.error is not None
    assert 'timed out' in result.error or 'Error' in result.error
