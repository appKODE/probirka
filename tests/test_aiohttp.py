import json

import pytest

pytest.importorskip('aiohttp')

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from probirka import Probirka, make_aiohttp_endpoint
from tests.helpers import FailureProbe, LeakyConfig, SlowProbe, SuccessProbe


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


@pytest.mark.asyncio
async def test_successful_response(probirka: Probirka) -> None:
    # Arrange
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka)
    app.router.add_get('/health', endpoint)
    server = TestServer(app)

    probirka.add_info('some_field', 'value')
    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 200
        response_data = await response.json()
        assert response_data['ok'] is True
        assert response_data['info']['some_field'] == 'value'
        assert len(response_data['checks']) == 1
        assert response_data['checks'][0]['ok'] is True


@pytest.mark.asyncio
async def test_error_response(probirka: Probirka) -> None:
    # Arrange
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka)
    app.router.add_get('/health', endpoint)
    server = TestServer(app)

    probirka.add_probes(FailureProbe())

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 500
        response_data = await response.json()
        assert response_data['ok'] is False
        assert len(response_data['checks']) == 1
        assert response_data['checks'][0]['ok'] is False


@pytest.mark.asyncio
async def test_custom_status_codes(probirka: Probirka) -> None:
    # Arrange
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka, success_code=201, error_code=400)
    app.router.add_get('/health', endpoint)
    server = TestServer(app)

    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 201
        response_data = await response.json()
        assert response_data['ok'] is True


@pytest.mark.asyncio
async def test_without_results(probirka: Probirka) -> None:
    # Arrange
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka, return_results=False)
    app.router.add_get('/health', endpoint)
    server = TestServer(app)

    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 200
        assert await response.text() == ''


@pytest.mark.asyncio
async def test_with_custom_parameters(probirka: Probirka) -> None:
    # Arrange
    success_probe_1 = SuccessProbe()
    success_probe_2 = SuccessProbe()

    probirka.add_probes(success_probe_1)  # required probe
    probirka.add_probes(success_probe_2, groups=['group1'])  # optional probe

    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka, timeout=30, with_groups=['group1'], skip_required=True)
    app.router.add_get('/health', endpoint)
    server = TestServer(app)

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 200
        response_data = await response.json()
        assert response_data['ok'] is True
        # only the one probe of group1 ran
        assert len(response_data['checks']) == 1


@pytest.mark.asyncio
async def test_timeout_returns_error_code(probirka: Probirka) -> None:
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka, timeout=0.1)  # type: ignore[arg-type]
    app.router.add_get('/health', endpoint)
    server = TestServer(app)
    probirka.add_probes(SlowProbe())

    async with TestClient(server) as client, client.get('/health') as response:
        assert response.status == 500
        response_data = await response.json()
        assert response_data['ok'] is False
        assert response_data['error'] == 'TimeoutError: probirka run timed out after 0.1s'
        assert response_data['checks'][0]['ok'] is False
        assert response_data['checks'][0]['error'] == 'TimeoutError: probirka run timed out after 0.1s'


@pytest.mark.asyncio
async def test_secrets_are_masked_in_response(probirka: Probirka) -> None:
    app = web.Application()
    app.router.add_get('/health', make_aiohttp_endpoint(probirka))
    probirka.add_info('password', 'hunter2')
    probirka.add_info('dsn', 'postgresql://app:hunter2@db/app')
    probirka.add_info('config', LeakyConfig())
    probirka.add_probes(SuccessProbe())

    async with TestClient(TestServer(app)) as client, client.get('/health') as response:
        assert response.status == 200
        assert response.content_type == 'application/json'
        text = await response.text()

    assert 'hunter2' not in text
    assert json.loads(text)['info'] == {
        'password': '***',
        'dsn': 'postgresql://app:***@db/app',
        'config': 'postgresql://app:***@db:5432/app',
    }
