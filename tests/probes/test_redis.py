from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('redis')

import redis.asyncio

from probirka import RedisProbe


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


def make_url_client(ping: AsyncMock) -> MagicMock:
    """A stand-in for ``Redis.from_url(...)``: an async context manager yielding itself."""
    client = MagicMock()
    client.ping = ping
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_url_uses_client_as_context_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_url_client(AsyncMock(return_value=True))
    from_url = MagicMock(return_value=client)
    monkeypatch.setattr(redis.asyncio.Redis, 'from_url', from_url)

    result = await RedisProbe(url='redis://localhost:6379/0').run_check()

    assert result.ok is True
    from_url.assert_called_once_with('redis://localhost:6379/0')
    client.__aexit__.assert_awaited_once()


@pytest.mark.asyncio
async def test_url_closes_client_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_url_client(AsyncMock(side_effect=RuntimeError('down')))
    monkeypatch.setattr(redis.asyncio.Redis, 'from_url', MagicMock(return_value=client))

    result = await RedisProbe(url='redis://localhost').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: down'
    client.__aexit__.assert_awaited_once()


def test_real_redis_client_is_an_async_context_manager() -> None:
    assert hasattr(redis.asyncio.Redis, '__aenter__')
    assert hasattr(redis.asyncio.Redis, '__aexit__')
