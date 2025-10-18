from typing import List

import pytest

from probirka import Probirka, ProbeBase

# Django expects a module-level urlpatterns
urlpatterns: List[object] = []
from probirka._django import make_django_view


class SuccessProbe(ProbeBase):
    async def _check(self) -> bool:
        return True


class FailureProbe(ProbeBase):
    async def _check(self) -> bool:
        return False


def _ensure_django_configured() -> None:
    # Minimal lazy configuration for Django in tests
    from django.conf import settings

    if settings.configured:  # type: ignore[attr-defined]
        return

    settings.configure(  # type: ignore[attr-defined]
        DEBUG=False,
        SECRET_KEY='test-secret-key',
        ROOT_URLCONF=__name__,
        ALLOWED_HOSTS=['*'],
        INSTALLED_APPS=[],
        MIDDLEWARE=[],
        TEMPLATES=[],
        USE_TZ=True,
    )

    import django

    django.setup()


# Build URLs dynamically per-test using a helper
def _make_urls(patterns: List[object]) -> None:
    global urlpatterns  # Django discovers this symbol by name
    urlpatterns = list(patterns)  # type: ignore[assignment]
    from django.urls import clear_url_caches, set_urlconf

    clear_url_caches()
    set_urlconf(__name__)


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


def test_successful_response(probirka: Probirka) -> None:
    _ensure_django_configured()

    from django.test import Client
    from django.urls import path

    probirka.add_info('some_field', 'value')
    probirka.add_probes(SuccessProbe())

    view = make_django_view(probirka)
    _make_urls([path('health/', view)])

    client = Client()
    response = client.get('/health/')

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    assert data['info']['some_field'] == 'value'
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is True


def test_error_response(probirka: Probirka) -> None:
    _ensure_django_configured()

    from django.test import Client
    from django.urls import path

    probirka.add_probes(FailureProbe())

    view = make_django_view(probirka)
    _make_urls([path('health/', view)])

    client = Client()
    response = client.get('/health/')

    assert response.status_code == 500
    data = response.json()
    assert data['ok'] is False
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is False


def test_custom_status_codes(probirka: Probirka) -> None:
    _ensure_django_configured()

    from django.test import Client
    from django.urls import path

    probirka.add_probes(SuccessProbe())

    view = make_django_view(
        probirka,
        success_code=201,
        error_code=400,
    )
    _make_urls([path('health/', view)])

    client = Client()
    response = client.get('/health/')

    assert response.status_code == 201
    data = response.json()
    assert data['ok'] is True


def test_without_results(probirka: Probirka) -> None:
    _ensure_django_configured()

    from django.test import Client
    from django.urls import path

    probirka.add_probes(SuccessProbe())

    view = make_django_view(
        probirka,
        return_results=False,
    )
    _make_urls([path('health/', view)])

    client = Client()
    response = client.get('/health/')

    assert response.status_code == 200
    assert response.content == b''


def test_with_custom_parameters(probirka: Probirka) -> None:
    _ensure_django_configured()

    from django.test import Client
    from django.urls import path

    success_probe_1 = SuccessProbe()
    success_probe_2 = SuccessProbe()

    probirka.add_probes(success_probe_1)  # required probe
    probirka.add_probes(success_probe_2, groups=['group1'])  # optional probe

    view = make_django_view(
        probirka,
        timeout=30,
        with_groups=['group1'],
        skip_required=True,
    )
    _make_urls([path('health/', view)])

    client = Client()
    response = client.get('/health/')

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    # Ensure only one probe ran (the optional one from group1)
    assert len(data['checks']) == 1


