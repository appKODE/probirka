"""Redirect handling and policy enforcement of the httpx-based probes, with a mock transport."""

from ipaddress import ip_address
from typing import Any

import pytest

import probirka
import probirka._probes._http_policy as policy_module
from probirka import HttpProbePolicy

Routes = dict[str, tuple[int, str | None]]
"""URL -> (status, Location header)."""

FOLLOW = HttpProbePolicy(follow_redirects=True)


@pytest.fixture(params=['httpx', 'httpx2'])
def lib(request: pytest.FixtureRequest) -> Any:
    return pytest.importorskip(request.param)


@pytest.fixture
def probe_cls(lib: Any) -> type:
    return {'httpx': probirka.HttpHttpxProbe, 'httpx2': probirka.HttpHttpx2Probe}[lib.__name__]


def make_client(lib: Any, routes: Routes, seen: list, **kwargs: Any) -> Any:  # type: ignore[type-arg]
    def handler(request: Any) -> Any:
        seen.append(request)
        status, location = routes[str(request.url)]
        return lib.Response(status, headers={'Location': location} if location else {})

    return lib.AsyncClient(transport=lib.MockTransport(handler), **kwargs)


def fake_resolver(monkeypatch: pytest.MonkeyPatch, mapping: dict[str, list[str]]) -> None:
    async def resolve(host: str, port: int | None = None) -> tuple[Any, ...]:
        return tuple(ip_address(address) for address in mapping[host])

    monkeypatch.setattr(policy_module, 'resolve_host', resolve)


@pytest.mark.parametrize(
    ('url', 'policy', 'message'),
    [
        ('ftp://svc/', None, "scheme 'ftp' is not allowed"),
        ('http://evil/', HttpProbePolicy(allowed_hosts=('svc',)), "host 'evil' is not in allowed_hosts"),
        ('http://127.0.0.1/', HttpProbePolicy(block_private_networks=True), 'address 127.0.0.1 is not a global'),
    ],
)
def test_refused_url_is_a_value_error_at_construction(
    probe_cls: type, url: str, policy: HttpProbePolicy | None, message: str
) -> None:
    with pytest.raises(ValueError, match=f'url refused by policy: {message}'):
        probe_cls(url, policy=policy)


@pytest.mark.asyncio
async def test_redirects_are_not_followed_by_default(lib: Any, probe_cls: type) -> None:
    seen: list = []  # type: ignore[type-arg]
    # even when the client itself is configured to follow
    client = make_client(lib, {'http://svc/a': (302, '/b')}, seen, follow_redirects=True)

    result = await probe_cls('http://svc/a', client=client).run_check()

    assert result.ok is False
    assert result.error == 'ProbeFailure: unexpected status 302'
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_follow_redirects_resolves_relative_location(lib: Any, probe_cls: type) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, '/b'), 'http://svc/b': (204, None)}, seen)

    result = await probe_cls('http://svc/a', client=client, policy=FOLLOW, expected_status=204).run_check()

    assert result.ok is True
    assert [str(request.url) for request in seen] == ['http://svc/a', 'http://svc/b']


@pytest.mark.parametrize(
    ('status', 'method', 'next_method'),
    [
        (303, 'POST', 'GET'),
        (301, 'POST', 'GET'),
        (302, 'POST', 'GET'),
        (302, 'GET', 'GET'),
        (307, 'POST', 'POST'),
        (308, 'POST', 'POST'),
        (303, 'HEAD', 'HEAD'),
    ],
)
@pytest.mark.asyncio
async def test_method_on_the_next_hop(lib: Any, probe_cls: type, status: int, method: str, next_method: str) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (status, '/b'), 'http://svc/b': (200, None)}, seen)

    result = await probe_cls('http://svc/a', method=method, client=client, policy=FOLLOW).run_check()

    assert result.ok is True
    assert [request.method for request in seen] == [method, next_method]


@pytest.mark.asyncio
async def test_headers_are_kept_on_the_same_origin(lib: Any, probe_cls: type) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, 'http://svc:80/b'), 'http://svc/b': (200, None)}, seen)

    result = await probe_cls('http://svc/a', headers={'X-Token': 't'}, client=client, policy=FOLLOW).run_check()

    assert result.ok is True
    assert seen[1].headers['x-token'] == 't'


@pytest.mark.parametrize('target', ['http://other/b', 'https://svc/b', 'http://svc:8080/b'])
@pytest.mark.asyncio
async def test_headers_are_dropped_on_another_origin(lib: Any, probe_cls: type, target: str) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, target), target: (200, None)}, seen)

    result = await probe_cls('http://svc/a', headers={'X-Token': 't'}, client=client, policy=FOLLOW).run_check()

    assert result.ok is True
    assert 'x-token' in seen[0].headers
    assert 'x-token' not in seen[1].headers


@pytest.mark.asyncio
async def test_redirect_outside_the_allowlist_is_refused(lib: Any, probe_cls: type) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, 'http://evil/')}, seen)
    policy = HttpProbePolicy(follow_redirects=True, allowed_hosts=('svc',))

    result = await probe_cls('http://svc/a', client=client, policy=policy).run_check()

    assert result.ok is False
    assert (
        result.error
        == "HttpProbePolicyViolation: redirect to http://evil/ refused: host 'evil' is not in allowed_hosts"
    )
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_redirect_to_the_metadata_service_is_refused(
    lib: Any, probe_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_resolver(monkeypatch, {'svc': ['8.8.8.8']})
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, 'http://169.254.169.254/latest/meta-data/')}, seen)
    policy = HttpProbePolicy(follow_redirects=True, block_private_networks=True)

    result = await probe_cls('http://svc/a', client=client, policy=policy).run_check()

    assert result.error == (
        'HttpProbePolicyViolation: redirect to http://169.254.169.254/latest/meta-data/ refused: '
        'address 169.254.169.254 is not a global address'
    )
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_redirect_to_a_name_resolving_privately_is_refused(
    lib: Any, probe_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_resolver(monkeypatch, {'svc': ['8.8.8.8'], 'internal': ['10.0.0.5']})
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (302, 'http://internal/')}, seen)
    policy = HttpProbePolicy(follow_redirects=True, block_private_networks=True)

    result = await probe_cls('http://svc/a', client=client, policy=policy).run_check()

    assert result.error == (
        'HttpProbePolicyViolation: redirect to http://internal/ refused: '
        'internal resolves to 10.0.0.5, which is not a global address'
    )
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_first_hop_is_resolved_before_the_request(
    lib: Any, probe_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_resolver(monkeypatch, {'svc': ['8.8.8.8', '10.0.0.5']})
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/a': (200, None)}, seen)

    result = await probe_cls(
        'http://svc/a', client=client, policy=HttpProbePolicy(block_private_networks=True)
    ).run_check()

    assert result.error == 'HttpProbePolicyViolation: svc resolves to 10.0.0.5, which is not a global address'
    assert seen == []


@pytest.mark.parametrize(('max_redirects', 'requests'), [(2, 3), (0, 1)])
@pytest.mark.asyncio
async def test_too_many_redirects(lib: Any, probe_cls: type, max_redirects: int, requests: int) -> None:
    seen: list = []  # type: ignore[type-arg]
    client = make_client(lib, {'http://svc/r': (302, '/r')}, seen)
    policy = HttpProbePolicy(follow_redirects=True, max_redirects=max_redirects)

    result = await probe_cls('http://svc/r', client=client, policy=policy).run_check()

    assert result.error == f'HttpProbePolicyViolation: too many redirects (more than {max_redirects})'
    assert len(seen) == requests


@pytest.mark.asyncio
async def test_redirect_without_location_is_a_final_status(lib: Any, probe_cls: type) -> None:
    client = make_client(lib, {'http://svc/a': (302, None)}, [])

    result = await probe_cls('http://svc/a', client=client, policy=FOLLOW).run_check()

    assert result.error == 'ProbeFailure: unexpected status 302'


@pytest.mark.asyncio
async def test_credentials_in_a_refused_location_are_masked(lib: Any, probe_cls: type) -> None:
    client = make_client(lib, {'http://svc/a': (302, 'http://u:hunter2@evil/')}, [])
    policy = HttpProbePolicy(follow_redirects=True, allowed_hosts=('svc',))

    result = await probe_cls('http://svc/a', client=client, policy=policy).run_check()

    assert result.error is not None
    assert 'http://u:***@evil/' in result.error
    assert 'hunter2' not in result.error


@pytest.mark.asyncio
async def test_allow_failure_with_a_refused_redirect(lib: Any, probe_cls: type) -> None:
    client = make_client(lib, {'http://svc/a': (302, 'http://evil/')}, [])
    policy = HttpProbePolicy(follow_redirects=True, allowed_hosts=('svc',))

    result = await probe_cls('http://svc/a', client=client, policy=policy, allow_failure=True).run_check()

    assert result.ok is False
    assert result.allow_failure is True
