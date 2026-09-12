from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('pymongo')

from pymongo.errors import ServerSelectionTimeoutError

import probirka.probes._mongo_pymongo as mongo_module
from probirka.probes import MongoPymongoProbe


def make_client(side_effect: object = None) -> MagicMock:
    client = MagicMock()
    client.admin.command = AsyncMock(return_value={'ok': 1.0}, side_effect=side_effect)
    client.close = AsyncMock()
    return client


def test_requires_client_or_url() -> None:
    with pytest.raises(ValueError):
        MongoPymongoProbe()
    with pytest.raises(ValueError):
        MongoPymongoProbe(client=MagicMock(), url='mongodb://x')


@pytest.mark.asyncio
async def test_client_success() -> None:
    client = make_client()

    result = await MongoPymongoProbe(client).run_check()

    assert result.ok is True
    assert result.name == 'MongoPymongoProbe'
    client.admin.command.assert_awaited_once_with('ping')
    client.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_client_factory() -> None:
    client = make_client()

    result = await MongoPymongoProbe(lambda: client).run_check()

    assert result.ok is True


@pytest.mark.asyncio
async def test_client_error_is_reported() -> None:
    client = make_client(side_effect=ServerSelectionTimeoutError('no primary'))

    result = await MongoPymongoProbe(client).run_check()

    assert result.ok is False
    assert result.error == 'ServerSelectionTimeoutError: no primary'


@pytest.mark.asyncio
async def test_url_creates_and_closes_client(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client()
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(mongo_module, 'AsyncMongoClient', client_cls)

    result = await MongoPymongoProbe(url='mongodb://localhost:27017', timeout=2).run_check()

    assert result.ok is True
    client_cls.assert_called_once_with('mongodb://localhost:27017', serverSelectionTimeoutMS=2000)
    client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_url_without_timeout_keeps_driver_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = make_client(side_effect=RuntimeError('boom'))
    client_cls = MagicMock(return_value=client)
    monkeypatch.setattr(mongo_module, 'AsyncMongoClient', client_cls)

    result = await MongoPymongoProbe(url='mongodb://localhost:27017').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: boom'
    client_cls.assert_called_once_with('mongodb://localhost:27017')
    client.close.assert_awaited_once()
