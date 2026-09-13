"""End-to-end: every ready-made probe in one ``Probirka`` against the live services."""

import json
from urllib.parse import urlparse

import pytest

pytest.importorskip('asyncpg')
pytest.importorskip('redis')
pytest.importorskip('aio_pika')
pytest.importorskip('pymongo')
pytest.importorskip('motor')
pytest.importorskip('aiokafka')
pytest.importorskip('httpx')
pytest.importorskip('httpx2')
pytest.importorskip('aiohttp')

from probirka import (
    HttpAiohttpProbe,
    HttpHttpx2Probe,
    HttpHttpxProbe,
    KafkaAiokafkaProbe,
    MongoMotorProbe,
    MongoPymongoProbe,
    PostgresAsyncpgProbe,
    Probirka,
    RabbitmqAiopikaProbe,
    RedisProbe,
    TcpProbe,
)

EXPECTED_NAMES = {
    'tcp',
    'postgres',
    'redis',
    'rabbitmq',
    'mongo-pymongo',
    'mongo-motor',
    'kafka',
    'http-httpx',
    'http-httpx2',
    'http-aiohttp',
}


def make_probirka(
    postgres_dsn: str,
    redis_url: str,
    rabbitmq_url: str,
    mongo_url: str,
    kafka_bootstrap: str,
    http_url: str,
) -> Probirka:
    pg = urlparse(postgres_dsn)
    assert pg.hostname is not None
    assert pg.port is not None

    probirka = Probirka()
    probirka.add_probes(
        TcpProbe(pg.hostname, pg.port, name='tcp', timeout=5),
        PostgresAsyncpgProbe(dsn=postgres_dsn, name='postgres', timeout=5),
        RedisProbe(url=redis_url, name='redis', timeout=5),
        RabbitmqAiopikaProbe(url=rabbitmq_url, name='rabbitmq', timeout=5),
        MongoPymongoProbe(url=mongo_url, name='mongo-pymongo', timeout=5),
        MongoMotorProbe(url=mongo_url, name='mongo-motor', timeout=5),
        KafkaAiokafkaProbe(bootstrap_servers=kafka_bootstrap, name='kafka', timeout=15),
        HttpHttpxProbe(http_url, name='http-httpx', timeout=5),
        HttpHttpx2Probe(http_url, name='http-httpx2', timeout=5),
        HttpAiohttpProbe(http_url, name='http-aiohttp', timeout=5),
    )
    return probirka


@pytest.mark.asyncio
async def test_all_probes_pass(
    postgres_dsn: str,
    redis_url: str,
    rabbitmq_url: str,
    mongo_url: str,
    kafka_bootstrap: str,
    http_url: str,
) -> None:
    probirka = make_probirka(postgres_dsn, redis_url, rabbitmq_url, mongo_url, kafka_bootstrap, http_url)

    result = await probirka.run()

    assert {check.name for check in result.checks} == EXPECTED_NAMES
    failed = [(check.name, check.error) for check in result.checks if not check.ok]
    assert failed == []
    assert result.ok is True
    assert json.loads(json.dumps(result.to_dict()))['ok'] is True


@pytest.mark.asyncio
async def test_allowed_failure_does_not_break_overall_result(
    postgres_dsn: str,
    redis_url: str,
    rabbitmq_url: str,
    mongo_url: str,
    kafka_bootstrap: str,
    http_url: str,
    unreachable_port: int,
) -> None:
    probirka = make_probirka(postgres_dsn, redis_url, rabbitmq_url, mongo_url, kafka_bootstrap, http_url)
    probirka.add_probes(
        RedisProbe(url=f'redis://127.0.0.1:{unreachable_port}/0', name='optional-cache', timeout=5, allow_failure=True)
    )

    result = await probirka.run()

    optional = next(check for check in result.checks if check.name == 'optional-cache')
    assert optional.ok is False
    assert optional.allow_failure is True
    assert result.ok is True
