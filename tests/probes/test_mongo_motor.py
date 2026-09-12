from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('motor')

from pymongo.errors import ServerSelectionTimeoutError

import probirka.probes._mongo_motor as mongo_module
from probirka.probes import MongoMotorProbe


def make_client(side_effect: object = None) -> MagicMock:
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={'ok': 1.0}, side_effect=side_effect)
    client.close = MagicMock()  # synchronous in Motor
    return client


def test_requires_client_or_url() -> None:
    with pytest.raises(ValueError):
        MongoMotorProbe()
    with pytest.raises(ValueError):
        MongoMotorProbe(client=MagicMock(), url='mongodb://x')


@pytest.mark.asyncio
async def test_client_success() -> None:
    client = make_client()

    result = await MongoMotorProbe(client).run_check()

    assert result.ok is True
    assert result.name == 'MongoMotorProbe'
    client.admin.command.assert_awaited_once_with('ping')
    client.close.assert_not_called()


@pytest.mark.asyncio
async def test_client_error_is_reported() -> None:
    client = make_client(side_effect=ServerSelectionTimeoutError('no primary'))

    result = await MongoMotorProbe(lambda: client).run_check()

    assert result.ok is False
    assert result.error == 'ServerSelectionTimeoutError: no primary'


@pytest.mark.asyncio
async def test_url_creates_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(mongo_module, 'AsyncIOMotorClient', client_cls)

    result = await MongoMotorProbe(url='mongodb://localhost:27017', timeout=3).run_check()

    assert result.ok is True
    client_cls.assert_called_once_with('mongodb://localhost:27017', serverSelectionTimeoutMS=3000)
    client.close.assert_called_once()


@pytest.mark.asyncio
async def test_url_closes_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(side_effect=RuntimeError('boom'))
    monkeypatch.setattr(mongo_module, 'AsyncIOMotorClient', MagicMock(return_value=client))

    result = await MongoMotorProbe(url='mongodb://localhost:27017').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: boom'
    client.close.assert_called_once()
