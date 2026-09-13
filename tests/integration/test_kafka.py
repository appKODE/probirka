import pytest

pytest.importorskip('aiokafka')

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient

from probirka import KafkaAiokafkaProbe


@pytest.mark.asyncio
async def test_bootstrap_servers(kafka_bootstrap: str) -> None:
    result = await KafkaAiokafkaProbe(bootstrap_servers=kafka_bootstrap).run_check()
    list_result = await KafkaAiokafkaProbe(bootstrap_servers=[kafka_bootstrap]).run_check()

    assert result.ok is True
    assert result.error is None
    assert list_result.ok is True


@pytest.mark.asyncio
async def test_producer_client(kafka_bootstrap: str) -> None:
    producer = AIOKafkaProducer(bootstrap_servers=kafka_bootstrap)
    await producer.start()
    try:
        result = await KafkaAiokafkaProbe(producer).run_check()
    finally:
        await producer.stop()

    assert result.ok is True


@pytest.mark.asyncio
async def test_consumer_client(kafka_bootstrap: str) -> None:
    consumer = AIOKafkaConsumer(bootstrap_servers=kafka_bootstrap)
    await consumer.start()
    try:
        result = await KafkaAiokafkaProbe(lambda: consumer).run_check()
    finally:
        await consumer.stop()

    assert result.ok is True


@pytest.mark.asyncio
async def test_admin_client(kafka_bootstrap: str) -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=kafka_bootstrap)
    await admin.start()
    try:
        result = await KafkaAiokafkaProbe(admin).run_check()
    finally:
        await admin.close()

    assert result.ok is True


@pytest.mark.asyncio
async def test_connection_refused(unreachable_port: int) -> None:
    result = await KafkaAiokafkaProbe(bootstrap_servers=f'127.0.0.1:{unreachable_port}', timeout=10).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('KafkaConnectionError')
