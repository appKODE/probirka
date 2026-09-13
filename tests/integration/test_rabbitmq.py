import pytest

pytest.importorskip('aio_pika')

import aio_pika

from probirka import RabbitmqAiopikaProbe


@pytest.mark.asyncio
async def test_url(rabbitmq_url: str) -> None:
    result = await RabbitmqAiopikaProbe(url=rabbitmq_url).run_check()

    assert result.ok is True
    assert result.error is None


@pytest.mark.asyncio
async def test_client(rabbitmq_url: str) -> None:
    connection = await aio_pika.connect(rabbitmq_url)
    try:
        result = await RabbitmqAiopikaProbe(connection).run_check()
        factory_result = await RabbitmqAiopikaProbe(lambda: connection).run_check()
        assert connection.is_closed is False
    finally:
        await connection.close()

    assert result.ok is True
    assert factory_result.ok is True


@pytest.mark.asyncio
async def test_closed_connection_is_failure(rabbitmq_url: str) -> None:
    connection = await aio_pika.connect(rabbitmq_url)
    await connection.close()

    result = await RabbitmqAiopikaProbe(connection).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: connection is closed'


@pytest.mark.asyncio
async def test_connection_refused(unreachable_port: int) -> None:
    url = f'amqp://guest:guest@127.0.0.1:{unreachable_port}/'

    result = await RabbitmqAiopikaProbe(url=url, timeout=5).run_check()

    assert result.ok is False
    assert result.error is not None
    assert 'ConnectionRefused' in result.error or 'AMQPConnectionError' in result.error or 'OSError' in result.error
