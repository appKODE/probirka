from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('aio_pika')

import aio_pika

from probirka.probes import RabbitmqAiopikaProbe


def make_connection(is_closed: bool = False) -> MagicMock:
    connection = MagicMock()
    connection.is_closed = is_closed
    channel = MagicMock()
    channel.close = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)
    connection.close = AsyncMock()
    return connection


def test_requires_client_or_url() -> None:
    with pytest.raises(ValueError):
        RabbitmqAiopikaProbe()
    with pytest.raises(ValueError):
        RabbitmqAiopikaProbe(client=MagicMock(), url='amqp://x')


@pytest.mark.asyncio
async def test_connection_success() -> None:
    connection = make_connection()

    result = await RabbitmqAiopikaProbe(connection).run_check()

    assert result.ok is True
    assert result.name == 'RabbitmqAiopikaProbe'
    connection.channel.assert_awaited_once()
    connection.channel.return_value.close.assert_awaited_once()
    connection.close.assert_not_awaited()  # not ours to close


@pytest.mark.asyncio
async def test_connection_factory() -> None:
    connection = make_connection()

    result = await RabbitmqAiopikaProbe(lambda: connection).run_check()

    assert result.ok is True


@pytest.mark.asyncio
async def test_closed_connection_is_failure() -> None:
    result = await RabbitmqAiopikaProbe(make_connection(is_closed=True)).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: connection is closed'


@pytest.mark.asyncio
async def test_channel_error_is_reported() -> None:
    connection = make_connection()
    connection.channel = AsyncMock(side_effect=aio_pika.exceptions.AMQPConnectionError('lost'))

    result = await RabbitmqAiopikaProbe(connection).run_check()

    assert result.ok is False
    assert result.error == 'AMQPConnectionError: lost'


@pytest.mark.asyncio
async def test_url_connects_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connection()
    connect = AsyncMock(return_value=connection)
    monkeypatch.setattr(aio_pika, 'connect', connect)

    result = await RabbitmqAiopikaProbe(url='amqp://guest:guest@localhost/').run_check()

    assert result.ok is True
    connect.assert_awaited_once_with('amqp://guest:guest@localhost/')
    connection.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_url_closes_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = make_connection()
    connection.channel = AsyncMock(side_effect=RuntimeError('boom'))
    monkeypatch.setattr(aio_pika, 'connect', AsyncMock(return_value=connection))

    result = await RabbitmqAiopikaProbe(url='amqp://localhost/').run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: boom'
    connection.close.assert_awaited_once()
