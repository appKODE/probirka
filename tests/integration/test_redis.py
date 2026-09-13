import pytest

pytest.importorskip('redis')

from redis.asyncio import Redis

from probirka import RedisProbe


@pytest.mark.asyncio
async def test_url(redis_url: str) -> None:
    result = await RedisProbe(url=redis_url).run_check()

    assert result.ok is True
    assert result.error is None


@pytest.mark.asyncio
async def test_client(redis_url: str) -> None:
    client = Redis.from_url(redis_url)
    try:
        result = await RedisProbe(client).run_check()
        factory_result = await RedisProbe(lambda: client).run_check()
        # the client stays usable: the probe does not close an existing client
        assert await client.ping() is True
    finally:
        await client.aclose()

    assert result.ok is True
    assert factory_result.ok is True


@pytest.mark.asyncio
async def test_connection_refused(unreachable_port: int) -> None:
    result = await RedisProbe(url=f'redis://127.0.0.1:{unreachable_port}/0', timeout=5).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('ConnectionError')
