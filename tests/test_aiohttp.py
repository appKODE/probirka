import json
from datetime import datetime, timedelta
from typing import AsyncGenerator

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from probirka import Probirka, ProbeBase
from probirka._aiohttp import make_aiohttp_endpoint
from probirka._results import HealthCheckResult, ProbeResult


class SuccessProbe(ProbeBase):
    async def _check(self) -> bool:
        return True


class FailureProbe(ProbeBase):
    async def _check(self) -> bool:
        return False


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


@pytest.mark.asyncio
async def test_successful_response(probirka: Probirka) -> None:
    # Подготовка
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka)
    app.router.add_get("/health", endpoint)
    server = TestServer(app)

    probirka.add_info("some_field", "value")
    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client:
        # Выполнение
        async with client.get("/health") as response:
            # Проверка
            assert response.status == 200
            response_data = await response.json()
            assert response_data["ok"] is True
            assert response_data["info"]["some_field"] == "value"
            assert len(response_data["checks"]) == 1
            assert response_data["checks"][0]["ok"] is True


@pytest.mark.asyncio
async def test_error_response(probirka: Probirka) -> None:
    # Подготовка
    app = web.Application()
    endpoint = make_aiohttp_endpoint(probirka)
    app.router.add_get("/health", endpoint)
    server = TestServer(app)

    probirka.add_probes(FailureProbe())

    async with TestClient(server) as client:
        # Выполнение
        async with client.get("/health") as response:
            # Проверка
            assert response.status == 500
            response_data = await response.json()
            assert response_data["ok"] is False
            assert len(response_data["checks"]) == 1
            assert response_data["checks"][0]["ok"] is False


@pytest.mark.asyncio
async def test_custom_status_codes(probirka: Probirka) -> None:
    # Подготовка
    app = web.Application()
    endpoint = make_aiohttp_endpoint(
        probirka,
        success_code=201,
        error_code=400
    )
    app.router.add_get("/health", endpoint)
    server = TestServer(app)

    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client:
        # Выполнение
        async with client.get("/health") as response:
            # Проверка
            assert response.status == 201
            response_data = await response.json()
            assert response_data["ok"] is True


@pytest.mark.asyncio
async def test_without_results(probirka: Probirka) -> None:
    # Подготовка
    app = web.Application()
    endpoint = make_aiohttp_endpoint(
        probirka,
        return_results=False
    )
    app.router.add_get("/health", endpoint)
    server = TestServer(app)

    probirka.add_probes(SuccessProbe())

    async with TestClient(server) as client:
        # Выполнение
        async with client.get("/health") as response:
            # Проверка
            assert response.status == 200
            assert await response.text() == ""


@pytest.mark.asyncio
async def test_with_custom_parameters(probirka: Probirka) -> None:
    # Подготовка
    success_probe_1 = SuccessProbe()
    success_probe_2 = SuccessProbe()

    probirka.add_probes(success_probe_1)  # required probe
    probirka.add_probes(success_probe_2, groups=["group1"])  # optional probe

    app = web.Application()
    endpoint = make_aiohttp_endpoint(
        probirka,
        timeout=30,
        with_groups=["group1"],
        skip_required=True
    )
    app.router.add_get("/health", endpoint)
    server = TestServer(app)

    async with TestClient(server) as client:
        # Выполнение
        async with client.get("/health") as response:
            # Проверка
            assert response.status == 200
            response_data = await response.json()
            assert response_data["ok"] is True
            # Проверяем, что запустился только один проб из группы group1
            assert len(response_data["checks"]) == 1
