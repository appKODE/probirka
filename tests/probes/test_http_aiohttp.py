from typing import AsyncIterator

import pytest

pytest.importorskip('aiohttp')

import aiohttp
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer

from probirka.probes import HttpAiohttpProbe


@pytest_asyncio.fixture
async def server() -> AsyncIterator[TestServer]:
    app = web.Application()

    async def ok(_: web.Request) -> web.Response:
        return web.Response(status=200)

    async def teapot(request: web.Request) -> web.Response:
        return web.Response(status=418, text=request.headers.get('X-Token', ''))

    app.router.add_get('/ok', ok)
    app.router.add_route('*', '/teapot', teapot)
    async with TestServer(app) as srv:
        yield srv


@pytest.mark.asyncio
async def test_success_with_session(server: TestServer) -> None:
    async with aiohttp.ClientSession() as session:
        result = await HttpAiohttpProbe(str(server.make_url('/ok')), client=session).run_check()

    assert result.ok is True
    assert result.name == 'HttpAiohttpProbe'


@pytest.mark.asyncio
async def test_session_factory(server: TestServer) -> None:
    async with aiohttp.ClientSession() as session:
        result = await HttpAiohttpProbe(str(server.make_url('/ok')), client=lambda: session).run_check()

    assert result.ok is True


@pytest.mark.asyncio
async def test_unexpected_status_is_failure(server: TestServer) -> None:
    async with aiohttp.ClientSession() as session:
        result = await HttpAiohttpProbe(str(server.make_url('/teapot')), client=session).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 418'


@pytest.mark.asyncio
async def test_method_and_expected_status(server: TestServer) -> None:
    probe = HttpAiohttpProbe(
        str(server.make_url('/teapot')),
        method='POST',
        headers={'X-Token': 'x'},
        expected_status=(418,),
    )

    result = await probe.run_check()  # temporary session

    assert result.ok is True


@pytest.mark.asyncio
async def test_connection_error_is_reported() -> None:
    result = await HttpAiohttpProbe('http://127.0.0.1:1/health').run_check()

    assert result.ok is False
    assert result.error is not None
    assert 'ClientConnectorError' in result.error
