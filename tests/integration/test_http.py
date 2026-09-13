from typing import Any

import pytest

_PROBES: list[Any] = []

for package, probe_name in (
    ('httpx', 'HttpHttpxProbe'),
    ('httpx2', 'HttpHttpx2Probe'),
    ('aiohttp', 'HttpAiohttpProbe'),
):
    try:
        __import__(package)
    except ImportError:  # pragma: no cover
        continue
    import probirka

    _PROBES.append(pytest.param(getattr(probirka, probe_name), id=package))


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_get_200(probe_cls: type, http_url: str) -> None:
    result = await probe_cls(http_url).run_check()

    assert result.ok is True
    assert result.error is None


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_head(probe_cls: type, http_url: str) -> None:
    result = await probe_cls(http_url, method='HEAD').run_check()

    assert result.ok is True


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_unexpected_status(probe_cls: type, http_url: str) -> None:
    result = await probe_cls(http_url, expected_status=(404,)).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 200'


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_not_found(probe_cls: type, http_url: str) -> None:
    result = await probe_cls(http_url.rstrip('/') + '/no-such-page').run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 404'


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_not_found_is_expected(probe_cls: type, http_url: str) -> None:
    result = await probe_cls(http_url.rstrip('/') + '/no-such-page', expected_status=[200, 404]).run_check()

    assert result.ok is True


@pytest.mark.parametrize('probe_cls', _PROBES)
@pytest.mark.asyncio
async def test_connection_refused(probe_cls: type, unreachable_port: int) -> None:
    result = await probe_cls(f'http://127.0.0.1:{unreachable_port}/', timeout=5).run_check()

    assert result.ok is False
    assert result.error is not None
    assert 'ProbeFailure' not in result.error
