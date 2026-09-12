from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('aiokafka')

import aiokafka.admin
from aiokafka.errors import KafkaConnectionError

import probirka._probes._kafka_aiokafka as kafka_module
from probirka import KafkaAiokafkaProbe


def test_requires_client_or_bootstrap_servers() -> None:
    with pytest.raises(ValueError):
        KafkaAiokafkaProbe()
    with pytest.raises(ValueError):
        KafkaAiokafkaProbe(client=MagicMock(), bootstrap_servers='localhost:9092')


@pytest.mark.asyncio
async def test_producer_success() -> None:
    producer = MagicMock(spec=['client'])
    producer.client.fetch_all_metadata = AsyncMock()

    result = await KafkaAiokafkaProbe(producer).run_check()

    assert result.ok is True
    assert result.name == 'KafkaAiokafkaProbe'
    producer.client.fetch_all_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_success() -> None:
    consumer = MagicMock(spec=['_client'])
    consumer._client.fetch_all_metadata = AsyncMock()

    result = await KafkaAiokafkaProbe(lambda: consumer).run_check()

    assert result.ok is True
    consumer._client.fetch_all_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_client_success() -> None:
    admin = MagicMock(spec=['describe_cluster'])
    admin.describe_cluster = AsyncMock(return_value={})

    result = await KafkaAiokafkaProbe(admin).run_check()

    assert result.ok is True
    admin.describe_cluster.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_error_is_reported() -> None:
    producer = MagicMock(spec=['client'])
    producer.client.fetch_all_metadata = AsyncMock(side_effect=KafkaConnectionError('no brokers'))

    result = await KafkaAiokafkaProbe(producer).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('KafkaConnectionError:')


@pytest.mark.asyncio
async def test_bootstrap_servers_uses_temporary_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = MagicMock()
    admin.start = AsyncMock()
    admin.describe_cluster = AsyncMock(return_value={})
    admin.close = AsyncMock()
    admin_cls = MagicMock(return_value=admin)
    monkeypatch.setattr(kafka_module, 'AIOKafkaAdminClient', admin_cls)

    result = await KafkaAiokafkaProbe(bootstrap_servers='localhost:9092').run_check()

    assert result.ok is True
    admin_cls.assert_called_once_with(bootstrap_servers='localhost:9092')
    admin.start.assert_awaited_once()
    admin.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_servers_closes_admin_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    admin = MagicMock()
    admin.start = AsyncMock()
    admin.describe_cluster = AsyncMock(side_effect=RuntimeError('boom'))
    admin.close = AsyncMock()
    monkeypatch.setattr(kafka_module, 'AIOKafkaAdminClient', MagicMock(return_value=admin))

    result = await KafkaAiokafkaProbe(bootstrap_servers=['a:9092', 'b:9092']).run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: boom'
    admin.close.assert_awaited_once()


def test_module_uses_real_admin_client() -> None:
    assert kafka_module.AIOKafkaAdminClient is aiokafka.admin.AIOKafkaAdminClient
