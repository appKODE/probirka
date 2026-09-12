from collections.abc import Callable
from unittest.mock import MagicMock

import pytest

import probirka


def _probe(name: str, *args: object, **kwargs: object) -> Callable[[], object]:
    def factory() -> object:
        cls = getattr(probirka, name)
        return cls(*args, allow_failure=True, **kwargs)

    factory.__name__ = name
    return factory


@pytest.mark.parametrize(
    ('package', 'factory'),
    [
        (None, _probe('TcpProbe', '127.0.0.1', 1)),
        ('httpx', _probe('HttpHttpxProbe', 'http://svc/health', client=MagicMock())),
        ('httpx', _probe('HttpHttpx2Probe', 'http://svc/health', client=MagicMock())),
        ('aiohttp', _probe('HttpAiohttpProbe', 'http://svc/health', client=MagicMock())),
        ('asyncpg', _probe('PostgresAsyncpgProbe', MagicMock())),
        ('redis', _probe('RedisProbe', MagicMock())),
        ('aio_pika', _probe('RabbitmqAiopikaProbe', MagicMock())),
        ('aiokafka', _probe('KafkaAiokafkaProbe', MagicMock())),
        ('motor', _probe('MongoMotorProbe', MagicMock())),
        ('pymongo', _probe('MongoPymongoProbe', MagicMock())),
    ],
    ids=lambda value: value.__name__ if callable(value) else str(value),
)
def test_ready_made_probes_accept_allow_failure(package: str | None, factory: Callable[[], object]) -> None:
    if package is not None:
        pytest.importorskip(package)

    probe = factory()

    assert probe.allow_failure is True  # type: ignore[attr-defined]
