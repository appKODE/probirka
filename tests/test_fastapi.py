import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from probirka import Probirka, ProbeBase
from probirka._fastapi import make_fastapi_endpoint


class SuccessProbe(ProbeBase):
    async def _check(self) -> bool:
        return True


class FailureProbe(ProbeBase):
    async def _check(self) -> bool:
        return False


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


@pytest.fixture
def test_client(probirka: Probirka) -> TestClient:
    app = FastAPI()
    endpoint = make_fastapi_endpoint(probirka)
    app.add_api_route("/health", endpoint)
    return TestClient(app)


def test_successful_response(test_client: TestClient, probirka: Probirka) -> None:
    # Подготовка
    probirka.add_info("some_field", "value")
    probirka.add_probes(SuccessProbe())

    # Выполнение
    response = test_client.get("/health")

    # Проверка
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["ok"] is True
    assert response_data["info"]["some_field"] == "value"
    assert len(response_data["checks"]) == 1
    assert response_data["checks"][0]["ok"] is True


def test_error_response(test_client: TestClient, probirka: Probirka) -> None:
    # Подготовка
    probirka.add_probes(FailureProbe())

    # Выполнение
    response = test_client.get("/health")

    # Проверка
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    response_data = response.json()
    assert response_data["ok"] is False
    assert len(response_data["checks"]) == 1
    assert response_data["checks"][0]["ok"] is False


def test_custom_status_codes(probirka: Probirka) -> None:
    # Подготовка
    app = FastAPI()
    endpoint = make_fastapi_endpoint(
        probirka,
        success_code=status.HTTP_201_CREATED,
        error_code=status.HTTP_400_BAD_REQUEST
    )
    app.add_api_route("/health", endpoint)
    client = TestClient(app)

    probirka.add_probes(SuccessProbe())

    # Выполнение
    response = client.get("/health")

    # Проверка
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["ok"] is True


def test_without_results(probirka: Probirka) -> None:
    # Подготовка
    app = FastAPI()
    endpoint = make_fastapi_endpoint(
        probirka,
        return_results=False
    )
    app.add_api_route("/health", endpoint)
    client = TestClient(app)

    probirka.add_probes(SuccessProbe())

    # Выполнение
    response = client.get("/health")

    # Проверка
    assert response.status_code == status.HTTP_200_OK
    assert response.content == b""


def test_with_custom_parameters(probirka: Probirka) -> None:
    # Подготовка
    success_probe_1 = SuccessProbe()
    success_probe_2 = SuccessProbe()

    probirka.add_probes(success_probe_1)  # required probe
    probirka.add_probes(success_probe_2, groups=["group1"])  # optional probe

    app = FastAPI()
    endpoint = make_fastapi_endpoint(
        probirka,
        timeout=30,
        with_groups=["group1"],
        skip_required=True
    )
    app.add_api_route("/health", endpoint)
    client = TestClient(app)

    # Выполнение
    response = client.get("/health")

    # Проверка
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["ok"] is True
    # Проверяем, что запустился только один проб из группы group1
    assert len(response_data["checks"]) == 1
