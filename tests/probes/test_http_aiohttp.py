from collections.abc import AsyncIterator

import pytest

pytest.importorskip('aiohttp')

import aiohttp
import pytest_asyncio
from aiohttp import web
from aiohttp.test_utils import TestServer

from probirka import HttpAiohttpProbe, HttpProbePolicy

FOLLOW = HttpProbePolicy(follow_redirects=True)


@pytest_asyncio.fixture
async def server() -> AsyncIterator[TestServer]:
    app = web.Application()

    async def ok(_: web.Request) -> web.Response:
        return web.Response(status=200)

    async def teapot(request: web.Request) -> web.Response:
        return web.Response(status=418, text=request.headers.get('X-Token', ''))

    async def redirect(_: web.Request) -> web.Response:
        raise web.HTTPFound('/ok')

    async def redirect_loop(_: web.Request) -> web.Response:
        raise web.HTTPFound('/redirect-loop')

    async def redirect_external(_: web.Request) -> web.Response:
        raise web.HTTPFound('http://169.254.169.254/')

    app.router.add_get('/ok', ok)
    app.router.add_get('/redirect', redirect)
    app.router.add_get('/redirect-loop', redirect_loop)
    app.router.add_get('/redirect-external', redirect_external)
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


@pytest.mark.asyncio
async def test_temporary_session_gets_probe_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    created = []
    real_session = aiohttp.ClientSession

    def _session(**kwargs: object) -> aiohttp.ClientSession:
        created.append(kwargs)
        return real_session(**kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(aiohttp, 'ClientSession', _session)

    await HttpAiohttpProbe('http://127.0.0.1:1/health', timeout=3).run_check()

    assert created[0]['timeout'] == aiohttp.ClientTimeout(total=3)


@pytest.mark.asyncio
async def test_redirects_are_not_followed_by_default(server: TestServer) -> None:
    async with aiohttp.ClientSession() as session:  # aiohttp itself would follow
        result = await HttpAiohttpProbe(str(server.make_url('/redirect')), client=session).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 302'


@pytest.mark.asyncio
async def test_follow_redirects_with_session_and_temporary_session(server: TestServer) -> None:
    url = str(server.make_url('/redirect'))
    async with aiohttp.ClientSession() as session:
        with_session = await HttpAiohttpProbe(url, client=session, policy=FOLLOW).run_check()
    temporary = await HttpAiohttpProbe(url, policy=FOLLOW).run_check()

    assert with_session.ok is True
    assert temporary.ok is True


@pytest.mark.asyncio
async def test_too_many_redirects(server: TestServer) -> None:
    policy = HttpProbePolicy(follow_redirects=True, max_redirects=2)

    result = await HttpAiohttpProbe(str(server.make_url('/redirect-loop')), policy=policy).run_check()

    assert result.error == 'HttpProbePolicyViolation: too many redirects (more than 2)'


@pytest.mark.asyncio
async def test_redirect_to_a_blocked_network_is_refused(server: TestServer) -> None:
    # the test server is on 127.0.0.1, so loopback has to be exempted for the first hop
    policy = HttpProbePolicy(
        follow_redirects=True, block_private_networks=True, allowed_networks=('127.0.0.0/8', '::1/128')
    )

    result = await HttpAiohttpProbe(str(server.make_url('/redirect-external')), policy=policy).run_check()

    assert result.error == (
        'HttpProbePolicyViolation: redirect to http://169.254.169.254/ refused: '
        'address 169.254.169.254 is not a global address'
    )
