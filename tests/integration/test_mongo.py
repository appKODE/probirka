from typing import Any

import pytest

pymongo = pytest.importorskip('pymongo')

from probirka import MongoPymongoProbe

_CASES: list[Any] = [pytest.param(MongoPymongoProbe, pymongo.AsyncMongoClient, id='pymongo')]

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ImportError:  # pragma: no cover
    pass
else:
    from probirka import MongoMotorProbe

    _CASES.append(pytest.param(MongoMotorProbe, AsyncIOMotorClient, id='motor'))


@pytest.mark.parametrize(('probe_cls', 'client_cls'), _CASES)
@pytest.mark.asyncio
async def test_url(probe_cls: type, client_cls: type, mongo_url: str) -> None:
    result = await probe_cls(url=mongo_url).run_check()

    assert result.ok is True
    assert result.error is None


@pytest.mark.parametrize(('probe_cls', 'client_cls'), _CASES)
@pytest.mark.asyncio
async def test_client(probe_cls: type, client_cls: type, mongo_url: str) -> None:
    client = client_cls(mongo_url)
    try:
        result = await probe_cls(client).run_check()
        factory_result = await probe_cls(lambda: client).run_check()
        # still usable afterwards
        assert (await client.admin.command('ping'))['ok'] == 1
    finally:
        close = client.close()
        if close is not None:  # pymongo.AsyncMongoClient.close is a coroutine, motor's is sync
            await close

    assert result.ok is True
    assert factory_result.ok is True


@pytest.mark.parametrize(('probe_cls', 'client_cls'), _CASES)
@pytest.mark.asyncio
async def test_unreachable_is_failure(probe_cls: type, client_cls: type, unreachable_port: int) -> None:
    # ``timeout`` is forwarded as serverSelectionTimeoutMS, so the driver and the probe time out at the same
    # moment: either the driver's error or the probe's own timeout may win the race
    result = await probe_cls(url=f'mongodb://127.0.0.1:{unreachable_port}', timeout=2).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith(('ServerSelectionTimeoutError', 'TimeoutError: probe timed out'))
