from urllib.parse import urlparse

import pytest

from probirka import TcpProbe


@pytest.mark.asyncio
async def test_tcp_to_postgres(postgres_dsn: str) -> None:
    parsed = urlparse(postgres_dsn)
    assert parsed.hostname is not None
    assert parsed.port is not None

    result = await TcpProbe(parsed.hostname, parsed.port).run_check()

    assert result.ok is True
    assert result.error is None
