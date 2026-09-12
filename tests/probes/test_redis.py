from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('redis')

import redis.asyncio

from probirka.probes import RedisProbe


def test_requires_client_or_url() -> None:
    with pytest.raises(ValueError):
        RedisProbe()
    with pytest.raises(ValueError):
        RedisProbe(client=MagicMock(), url='redis://x')


@pytest.mark.asyncio
async def test_client_success() -> None:
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)

    result = await RedisProbe(client).run_check()

    assert result.ok is True
    assert result.name == 'RedisProbe'
    client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_factory() -> None:
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)

    result = await RedisProbe(lambda: client).run_check()

    assert result.ok is True


@pytest.mark.asyncio
async def test_ping_false_is_failure() -> None:
    client = MagicMock()
    client.ping = AsyncMock(return_value=False)

    result = await RedisProbe(client).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: PING failed'


@pytest.mark.asyncio
async def test_client_error_is_reported() -> None:
    client = MagicMock()
    client.ping = AsyncMock(side_effect=redis.ConnectionError('refused'))

    result = await RedisProbe(client).run_check()

    assert result.ok is False
    assert result.error == 'ConnectionError: refused'


@pytest.mark.asyncio
async def test_url_creates_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.aclose = AsyncMock()
    from_url = MagicMock(return_value=client)
    monkeypatch.setattr(redis.asyncio.Redis, 'from_url', from_url)

    result = await RedisProbe(url='redis://localhost:6379/0').run_check()

    assert result.ok is True
    from_url.assert_called_once_with('redis://localhost:6379/0')
    client.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_url_falls_back_to_close_on_old_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock(spec=['ping', 'close'])
    client.ping = AsyncMock(side_effect=RuntimeError('down'))
    client.close = AsyncMock()
    monkeypatch.setattr(redis.asyncio.Redis, 'from_url', MagicMock(return_value=client))

    result = await RedisProbe(url='redis://localhost').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: down'
    client.close.assert_awaited_once()
