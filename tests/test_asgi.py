import json

from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple

import pytest

from probirka import Probirka, make_asgi_app
from tests.helpers import FailureProbe, SlowProbe, SuccessProbe

ASGIApp = Callable[..., Any]


class Response(NamedTuple):
    """What the ASGI messages of a single request add up to."""

    status_code: int
    headers: dict[bytes, bytes]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body)


async def call(
    app: ASGIApp,
    method: str = 'GET',
    path: str = '/',
) -> Response:
    """Drive the app through one HTTP request, the way a server would."""
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1',
        'method': method,
        'scheme': 'http',
        'path': path,
        'raw_path': path.encode(),
        'query_string': b'',
        'root_path': '',
        'headers': [],
        'client': ('127.0.0.1', 54321),
        'server': ('testserver', 80),
    }
    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {'type': 'http.request', 'body': b'', 'more_body': False}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    await app(scope, receive, send)

    start, *body_messages = messages
    assert start['type'] == 'http.response.start'
    return Response(
        status_code=start['status'],
        headers=dict(start['headers']),
        body=b''.join(message.get('body', b'') for message in body_messages),
    )


@pytest.fixture
def probirka() -> Probirka:
    return Probirka()


@pytest.mark.asyncio
async def test_successful_response(probirka: Probirka) -> None:
    probirka.add_info('some_field', 'value')
    probirka.add_probes(SuccessProbe())

    response = await call(make_asgi_app(probirka))

    assert response.status_code == 200
    assert response.headers[b'content-type'] == b'application/json'
    assert response.headers[b'content-length'] == str(len(response.body)).encode()
    data = response.json()
    assert data['ok'] is True
    assert data['info']['some_field'] == 'value'
    assert data['error'] is None
    assert isinstance(data['elapsed'], float)
    assert isinstance(datetime.fromisoformat(data['started_at']), datetime)
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is True
    assert isinstance(data['checks'][0]['elapsed'], float)


@pytest.mark.asyncio
async def test_error_response(probirka: Probirka) -> None:
    probirka.add_probes(FailureProbe())

    response = await call(make_asgi_app(probirka))

    assert response.status_code == 500
    data = response.json()
    assert data['ok'] is False
    assert len(data['checks']) == 1
    assert data['checks'][0]['ok'] is False


@pytest.mark.asyncio
async def test_custom_status_codes(probirka: Probirka) -> None:
    probirka.add_probes(SuccessProbe())

    response = await call(make_asgi_app(probirka, success_code=201, error_code=400))

    assert response.status_code == 201
    assert response.json()['ok'] is True


@pytest.mark.asyncio
async def test_without_results(probirka: Probirka) -> None:
    probirka.add_probes(SuccessProbe())

    response = await call(make_asgi_app(probirka, return_results=False))

    assert response.status_code == 200
    assert response.body == b''
    assert response.headers[b'content-length'] == b'0'
    assert b'content-type' not in response.headers


@pytest.mark.asyncio
async def test_with_custom_parameters(probirka: Probirka) -> None:
    probirka.add_probes(SuccessProbe())
    probirka.add_probes(SuccessProbe(), groups=['group1'])

    response = await call(
        make_asgi_app(
            probirka,
            timeout=30,
            with_groups=['group1'],
            skip_required=True,
        )
    )

    assert response.status_code == 200
    data = response.json()
    assert data['ok'] is True
    # only the group1 probe ran
    assert len(data['checks']) == 1


@pytest.mark.asyncio
async def test_timeout_returns_error_code(probirka: Probirka) -> None:
    probirka.add_probes(SlowProbe())

    response = await call(make_asgi_app(probirka, timeout=0.1))  # type: ignore[arg-type]

    assert response.status_code == 500
    data = response.json()
    assert data['error'] == 'TimeoutError: probirka run timed out after 0.1s'
    assert data['checks'][0]['ok'] is False
    assert data['checks'][0]['error'] == 'TimeoutError: probirka run timed out after 0.1s'


@pytest.mark.asyncio
@pytest.mark.parametrize('method', ['POST', 'PUT', 'DELETE'])
async def test_non_get_method_not_allowed(probirka: Probirka, method: str) -> None:
    probirka.add_probes(SuccessProbe())

    response = await call(make_asgi_app(probirka), method=method)

    assert response.status_code == 405
    assert response.headers[b'allow'] == b'GET, HEAD'
    assert response.body == b''


@pytest.mark.asyncio
async def test_head_keeps_the_headers_of_a_get(probirka: Probirka) -> None:
    probirka.add_probes(SuccessProbe())
    app = make_asgi_app(probirka)

    get_response = await call(app)
    head_response = await call(app, method='HEAD')

    assert head_response.status_code == 200
    assert head_response.body == b''
    # same headers a GET would have carried, only without the body; the exact content-length
    # differs between runs because the elapsed time is not the same number of digits
    assert head_response.headers.keys() == get_response.headers.keys()
    assert head_response.headers[b'content-type'] == b'application/json'
    assert int(head_response.headers[b'content-length']) > 0


@pytest.mark.asyncio
async def test_head_of_a_failing_check_keeps_the_error_code(probirka: Probirka) -> None:
    probirka.add_probes(FailureProbe())

    response = await call(make_asgi_app(probirka), method='HEAD')

    assert response.status_code == 500
    assert response.body == b''


@pytest.mark.asyncio
@pytest.mark.parametrize('path', ['/', '/health', '/health/anything'])
async def test_path_is_ignored(probirka: Probirka, path: str) -> None:
    probirka.add_probes(SuccessProbe())

    response = await call(make_asgi_app(probirka), path=path)

    assert response.status_code == 200
    assert response.json()['ok'] is True


@pytest.mark.asyncio
async def test_lifespan_is_acknowledged(probirka: Probirka) -> None:
    app = make_asgi_app(probirka)
    incoming = [{'type': 'lifespan.startup'}, {'type': 'lifespan.shutdown'}]
    sent: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return incoming.pop(0)

    async def send(message: dict[str, Any]) -> None:
        sent.append(message)

    await app({'type': 'lifespan', 'asgi': {'version': '3.0'}}, receive, send)

    assert [message['type'] for message in sent] == [
        'lifespan.startup.complete',
        'lifespan.shutdown.complete',
    ]


@pytest.mark.asyncio
async def test_unsupported_scope_type(probirka: Probirka) -> None:
    app = make_asgi_app(probirka)

    async def receive() -> dict[str, Any]:
        raise AssertionError('must not be called')

    async def send(message: dict[str, Any]) -> None:
        raise AssertionError('must not be called')

    with pytest.raises(RuntimeError, match='http and lifespan'):
        await app({'type': 'websocket'}, receive, send)


def test_starlette_route(probirka: Probirka) -> None:
    pytest.importorskip('starlette')
    from starlette.applications import Starlette
    from starlette.routing import Route
    from starlette.testclient import TestClient

    probirka.add_probes(SuccessProbe())
    app = Starlette(routes=[Route('/health', make_asgi_app(probirka), methods=['GET', 'HEAD'])])
    client = TestClient(app)

    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['ok'] is True
    # an exact route, unlike a mount: no redirect and no sub-paths
    assert client.post('/health').status_code == 405
    assert client.get('/health/sub').status_code == 404


def test_starlette_mount_redirects_the_bare_path(probirka: Probirka) -> None:
    pytest.importorskip('starlette')
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.testclient import TestClient

    probirka.add_probes(SuccessProbe())
    app = Starlette(routes=[Mount('/health', make_asgi_app(probirka))])
    client = TestClient(app)

    assert client.get('/health/').status_code == 200
    # documented trap: a mount answers on the trailing slash and redirects the bare path,
    # which a health check that does not follow redirects would read as success
    assert client.get('/health', follow_redirects=False).status_code == 307


def test_fastapi_mount(probirka: Probirka) -> None:
    pytest.importorskip('fastapi')
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    probirka.add_probes(SuccessProbe())
    app = FastAPI()
    app.mount('/health', make_asgi_app(probirka))
    client = TestClient(app)

    response = client.get('/health/')
    assert response.status_code == 200
    assert response.json()['ok'] is True
    # a mounted app is invisible to OpenAPI
    assert '/health' not in client.get('/openapi.json').json()['paths']
