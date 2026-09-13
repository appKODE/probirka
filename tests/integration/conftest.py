"""
Integration tests run the probes against live services.

They are skipped unless ``PROBIRKA_INTEGRATION=1`` is set. Service addresses default to the ports
published by ``tests/integration/compose.yaml`` and by the ``services:`` block of the CI workflow;
override them with the ``PROBIRKA_IT_*`` variables below.
"""

import os
import socket
from pathlib import Path

import pytest

ENABLE_VAR = 'PROBIRKA_INTEGRATION'
HERE = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    enabled = os.environ.get(ENABLE_VAR) == '1'
    skip = pytest.mark.skip(reason=f'set {ENABLE_VAR}=1 and start tests/integration/compose.yaml')
    for item in items:
        if HERE not in Path(str(item.fspath)).parents:
            continue
        item.add_marker(pytest.mark.integration)
        if not enabled:
            item.add_marker(skip)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@pytest.fixture(scope='session')
def postgres_dsn() -> str:
    return _env('PROBIRKA_IT_POSTGRES_DSN', 'postgresql://probirka:probirka@localhost:5432/probirka')


@pytest.fixture(scope='session')
def redis_url() -> str:
    return _env('PROBIRKA_IT_REDIS_URL', 'redis://localhost:6379/0')


@pytest.fixture(scope='session')
def rabbitmq_url() -> str:
    return _env('PROBIRKA_IT_RABBITMQ_URL', 'amqp://guest:guest@localhost:5672/')


@pytest.fixture(scope='session')
def mongo_url() -> str:
    return _env('PROBIRKA_IT_MONGO_URL', 'mongodb://localhost:27017')


@pytest.fixture(scope='session')
def kafka_bootstrap() -> str:
    return _env('PROBIRKA_IT_KAFKA_BOOTSTRAP', 'localhost:9092')


@pytest.fixture(scope='session')
def http_url() -> str:
    return _env('PROBIRKA_IT_HTTP_URL', 'http://localhost:8080/')


@pytest.fixture
def unreachable_port() -> int:
    """A port on 127.0.0.1 that was just bound and released: connecting to it is refused."""
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]
