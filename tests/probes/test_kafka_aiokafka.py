from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip('aiokafka')

import aiokafka.admin
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.admin import AIOKafkaAdminClient
from aiokafka.errors import KafkaConnectionError

import probirka._probes._kafka_aiokafka as kafka_module
from probirka import KafkaAiokafkaProbe


class FakeAdmin(AIOKafkaAdminClient):
    """Real subclass so that the probe's isinstance dispatch recognises it; records its instances."""

    instances: list = []  # type: ignore[type-arg]

    def __init__(self, **kwargs: object) -> None:  # noqa: PLW0231 -- the real ctor needs a running loop
        self.kwargs = kwargs
        self.start = AsyncMock()
        self.describe_cluster = AsyncMock(return_value={})
        self.close = AsyncMock()
        self.instances.append(self)


@pytest.fixture
def fake_admin(monkeypatch: pytest.MonkeyPatch) -> type:
    monkeypatch.setattr(FakeAdmin, 'instances', [])
    monkeypatch.setattr(kafka_module, 'AIOKafkaAdminClient', FakeAdmin)
    return FakeAdmin


def test_requires_client_or_bootstrap_servers() -> None:
    with pytest.raises(ValueError):
        KafkaAiokafkaProbe()
    with pytest.raises(ValueError):
        KafkaAiokafkaProbe(client=MagicMock(), bootstrap_servers='localhost:9092')


@pytest.mark.asyncio
async def test_producer_success() -> None:
    producer = MagicMock(spec=AIOKafkaProducer)
    producer.client = MagicMock()
    producer.client.fetch_all_metadata = AsyncMock()

    result = await KafkaAiokafkaProbe(producer).run_check()

    assert result.ok is True
    assert result.name == 'KafkaAiokafkaProbe'
    producer.client.fetch_all_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_consumer_success() -> None:
    consumer = MagicMock(spec=AIOKafkaConsumer)
    consumer.topics = AsyncMock(return_value={'orders'})

    result = await KafkaAiokafkaProbe(lambda: consumer).run_check()

    assert result.ok is True
    consumer.topics.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_client_success() -> None:
    admin = MagicMock(spec=AIOKafkaAdminClient)
    admin.describe_cluster = AsyncMock(return_value={})

    result = await KafkaAiokafkaProbe(admin).run_check()

    assert result.ok is True
    admin.describe_cluster.assert_awaited_once()


@pytest.mark.asyncio
async def test_unsupported_client_type_is_reported() -> None:
    result = await KafkaAiokafkaProbe(object()).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('TypeError: expected AIOKafkaProducer')


@pytest.mark.asyncio
async def test_client_error_is_reported() -> None:
    producer = MagicMock(spec=AIOKafkaProducer)
    producer.client = MagicMock()
    producer.client.fetch_all_metadata = AsyncMock(side_effect=KafkaConnectionError('no brokers'))

    result = await KafkaAiokafkaProbe(producer).run_check()

    assert result.ok is False
    assert result.error is not None
    assert result.error.startswith('KafkaConnectionError:')


@pytest.mark.asyncio
async def test_bootstrap_servers_uses_temporary_admin(fake_admin: type) -> None:
    result = await KafkaAiokafkaProbe(bootstrap_servers='localhost:9092').run_check()

    assert result.ok is True
    (admin,) = fake_admin.instances
    assert admin.kwargs == {'bootstrap_servers': 'localhost:9092'}
    admin.start.assert_awaited_once()
    admin.describe_cluster.assert_awaited_once()
    admin.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_servers_closes_admin_on_error(fake_admin: type, monkeypatch: pytest.MonkeyPatch) -> None:
    class Broken(FakeAdmin):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self.describe_cluster = AsyncMock(side_effect=RuntimeError('boom'))

    monkeypatch.setattr(kafka_module, 'AIOKafkaAdminClient', Broken)

    result = await KafkaAiokafkaProbe(bootstrap_servers=['a:9092', 'b:9092']).run_check()

    assert result.ok is False
    assert result.error == 'RuntimeError: boom'
    fake_admin.instances[0].close.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_servers_closes_admin_when_start_fails(fake_admin: type, monkeypatch: pytest.MonkeyPatch) -> None:
    class Unreachable(FakeAdmin):
        def __init__(self, **kwargs: object) -> None:
            super().__init__(**kwargs)
            self.start = AsyncMock(side_effect=KafkaConnectionError('unreachable'))

    monkeypatch.setattr(kafka_module, 'AIOKafkaAdminClient', Unreachable)

    result = await KafkaAiokafkaProbe(bootstrap_servers='a:9092').run_check()

    assert result.ok is False
    fake_admin.instances[0].close.assert_awaited_once()


def test_module_uses_real_admin_client() -> None:
    assert kafka_module.AIOKafkaAdminClient is aiokafka.admin.AIOKafkaAdminClient
