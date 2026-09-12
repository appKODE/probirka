from typing import Callable

import pytest

pytest.importorskip('httpx')

import httpx

from probirka import HttpHttpxProbe


def make_client(status: int, seen: list) -> httpx.AsyncClient:  # type: ignore[type-arg]
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(status)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_success_with_client() -> None:
    seen: list = []  # type: ignore[type-arg]
    probe = HttpHttpxProbe('http://svc/health', client=make_client(200, seen))

    result = await probe.run_check()

    assert result.ok is True
    assert result.name == 'HttpHttpxProbe'
    assert seen[0].method == 'GET'
    assert str(seen[0].url) == 'http://svc/health'


@pytest.mark.asyncio
async def test_method_headers_and_expected_status() -> None:
    seen: list = []  # type: ignore[type-arg]
    probe = HttpHttpxProbe(
        'http://svc/health',
        method='HEAD',
        headers={'X-Token': 'secret'},
        expected_status={204, 200},
        client=make_client(204, seen),
    )

    result = await probe.run_check()

    assert result.ok is True
    assert seen[0].method == 'HEAD'
    assert seen[0].headers['x-token'] == 'secret'


@pytest.mark.asyncio
async def test_unexpected_status_is_failure() -> None:
    probe = HttpHttpxProbe('http://svc/health', client=make_client(503, []))

    result = await probe.run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 503'


@pytest.mark.asyncio
async def test_client_factory() -> None:
    client = make_client(200, [])
    factory: Callable[[], httpx.AsyncClient] = lambda: client  # noqa: E731

    result = await HttpHttpxProbe('http://svc/health', client=factory).run_check()

    assert result.ok is True


@pytest.mark.asyncio
async def test_transport_error_is_reported() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('refused', request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    result = await HttpHttpxProbe('http://svc/health', client=client).run_check()

    assert result.ok is False
    assert result.error == 'ConnectError: refused'


@pytest.mark.asyncio
async def test_temporary_client_is_created_with_probe_timeout_and_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    created = []

    class _Client(httpx.AsyncClient):
        def __init__(self, timeout: object) -> None:
            super().__init__(transport=httpx.MockTransport(lambda _: httpx.Response(200)), timeout=timeout)
            created.append(self)

    monkeypatch.setattr(httpx, 'AsyncClient', _Client)

    result = await HttpHttpxProbe('http://svc/health', timeout=7).run_check()

    assert result.ok is True
    assert len(created) == 1
    assert created[0].is_closed
    assert created[0].timeout == httpx.Timeout(7)


@pytest.mark.asyncio
async def test_temporary_client_without_probe_timeout_has_no_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    created = []

    class _Client(httpx.AsyncClient):
        def __init__(self, timeout: object) -> None:
            super().__init__(transport=httpx.MockTransport(lambda _: httpx.Response(200)), timeout=timeout)
            created.append(self)

    monkeypatch.setattr(httpx, 'AsyncClient', _Client)

    await HttpHttpxProbe('http://svc/health').run_check()

    assert created[0].timeout == httpx.Timeout(None)


@pytest.mark.asyncio
async def test_expected_status_accepts_single_int() -> None:
    result = await HttpHttpxProbe('http://svc/health', expected_status=204, client=make_client(204, [])).run_check()

    assert result.ok is True
