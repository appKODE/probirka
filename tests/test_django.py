from collections.abc import Callable
from datetime import datetime

import pytest

pytest.importorskip('django')

import django
from django.conf import settings

from probirka import Probirka
from tests.helpers import FailureProbe, LeakyConfig, SlowProbe, SuccessProbe

if not settings.configured:
    settings.configure(
        DEBUG=False,
        SECRET_KEY='test-secret-key',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=[],
        MIDDLEWARE=[],
        TEMPLATES=[],
        USE_TZ=True,
    )
    django.setup()

from django.http import HttpRequest, HttpResponse
from django.test import Client
from django.urls import clear_url_caches, path

from probirka import make_django_view

# Django resolves ROOT_URLCONF to this module and reads this symbol by name
urlpatterns: list[object] = []

View = Callable[[HttpRequest], object]


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


@pytest.fixture
def make_client() -> Callable[[View], Client]:
    def _inner(view: View) -> Client:
        urlpatterns[:] = [path('health', view)]
        clear_url_caches()
        return Client()

    return _inner


def test_successful_response(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_info('some_field', 'value')
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka))

    response = client.get('/health')

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert data['info']['some_field'] == 'value'
    assert data['error'] is None
    assert isinstance(data['elapsed'], float)
    assert isinstance(datetime.fromisoformat(data['started_at']), datetime)
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is True
    assert isinstance(data['checks'][0]['elapsed'], float)


def test_error_response(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(FailureProbe())
    client = make_client(make_django_view(probirka))

    response = client.get('/health')

    assert response.status_code == 500
    data = response.json()
    assert data['ok'] is False
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is False


def test_custom_status_codes(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka, success_code=201, error_code=400))

    response = client.get('/health')

    assert response.status_code == 201
    assert response.json()['ok'] is True


def test_without_results(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka, return_results=False))

    response = client.get('/health')

    assert response.status_code == 200
    assert response.content == b''


def test_with_custom_parameters(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(SuccessProbe())  # required probe
    probirka.add_probes(SuccessProbe(), groups=['group1'])  # optional probe
    client = make_client(
        make_django_view(
            probirka,
            timeout=30,
            with_groups=['group1'],
            skip_required=True,
        )
    )

    response = client.get('/health')

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    # Only the optional probe from group1 ran
    assert len(data['checks']) == 1


def test_timeout_returns_error_code(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(SlowProbe())
    client = make_client(make_django_view(probirka, timeout=0.1))  # type: ignore[arg-type]

    response = client.get('/health')

    assert response.status_code == 500
    data = response.json()
    assert data['ok'] is False
    assert data['error'] == 'TimeoutError: probirka run timed out after 0.1s'
    assert data['checks'][0]['ok'] is False
    assert data['checks'][0]['error'] == 'TimeoutError: probirka run timed out after 0.1s'


@pytest.mark.parametrize('method', ['post', 'put', 'delete'])
def test_non_get_method_not_allowed(probirka: Probirka, make_client: Callable[[View], Client], method: str) -> None:
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka))

    response: HttpResponse = getattr(client, method)('/health')

    assert response.status_code == 405
    assert response['Allow'] == 'GET, HEAD'


def test_head_allowed(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka))

    response = client.head('/health')

    assert response.status_code == 200
    assert response.content == b''


def test_secrets_are_masked_in_response(probirka: Probirka, make_client: Callable[[View], Client]) -> None:
    probirka.add_info('password', 'hunter2')
    probirka.add_info('dsn', 'postgresql://app:hunter2@db/app')
    probirka.add_info('config', LeakyConfig())
    probirka.add_probes(SuccessProbe())
    client = make_client(make_django_view(probirka))

    response = client.get('/health')

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/json'
    assert b'hunter2' not in response.content
    assert response.json()['info'] == {
        'password': '***',
        'dsn': 'postgresql://app:***@db/app',
        'config': 'postgresql://app:***@db:5432/app',
    }
