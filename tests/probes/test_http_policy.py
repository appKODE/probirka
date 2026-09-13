import asyncio
import socket
from collections.abc import Callable, Iterable
from ipaddress import IPv4Network, ip_address
from typing import Any
from urllib.parse import SplitResult

import pytest

import probirka._probes._http_policy as policy_module
from probirka import HttpProbePolicy, HttpProbePolicyViolation, ProbeFailure
from probirka._probes._http_policy import normalize_host, resolve_host

ALLOWLIST = ('api.example.com', '*.internal.example.org')
STRICT = HttpProbePolicy(block_private_networks=True)


def fake_resolver(mapping: dict[str, Iterable[str]]) -> tuple[Callable[..., Any], list[tuple[str, int | None]]]:
    calls: list[tuple[str, int | None]] = []

    async def resolve(host: str, port: int | None = None) -> tuple[Any, ...]:
        calls.append((host, port))
        return tuple(ip_address(address) for address in mapping[host])

    return resolve, calls


def test_defaults_are_soft() -> None:
    policy = HttpProbePolicy()

    assert policy.allowed_schemes == frozenset({'http', 'https'})
    assert policy.allowed_hosts is None
    assert policy.block_private_networks is False
    assert policy.blocked_networks == ()
    assert policy.allowed_networks == ()
    assert policy.follow_redirects is False
    assert policy.max_redirects == 5
    assert policy.needs_resolution is False


def test_violation_is_a_probe_failure() -> None:
    assert issubclass(HttpProbePolicyViolation, ProbeFailure)


@pytest.mark.parametrize(
    'url',
    [
        'http://localhost/',
        'https://svc:8443/p?q=1',
        'http://[::1]:8080/',
        'http://10.0.0.1/',
        'http://169.254.169.254/',
    ],
)
def test_default_policy_accepts_any_http_url(url: str) -> None:
    parts = HttpProbePolicy().check_url(url)

    assert isinstance(parts, SplitResult)


@pytest.mark.parametrize('url', ['ftp://svc/', 'file:///etc/passwd', 'localhost:8080/health', '/health'])
def test_scheme_not_allowed(url: str) -> None:
    with pytest.raises(HttpProbePolicyViolation, match=r'scheme .* is not allowed'):
        HttpProbePolicy().check_url(url)


def test_allowed_schemes_are_case_insensitive() -> None:
    policy = HttpProbePolicy(allowed_schemes=('HTTPS',))

    policy.check_url('HTTPS://svc/')
    with pytest.raises(HttpProbePolicyViolation, match="scheme 'http' is not allowed"):
        policy.check_url('http://svc/')


def test_empty_allowed_schemes_is_rejected() -> None:
    with pytest.raises(ValueError, match='allowed_schemes'):
        HttpProbePolicy(allowed_schemes=())


@pytest.mark.parametrize('url', ['http:///path', 'http://[::1/', 'http://svc:abc/', 'http://svc:99999/'])
def test_malformed_or_hostless_url_is_refused(url: str) -> None:
    with pytest.raises(HttpProbePolicyViolation):
        HttpProbePolicy().check_url(url)


def test_malformed_url_is_masked_in_the_message() -> None:
    with pytest.raises(HttpProbePolicyViolation, match=r'http://u:\*\*\*@svc:abc/'):
        HttpProbePolicy().check_url('http://u:hunter2@svc:abc/')


@pytest.mark.parametrize(
    'url', ['http://api.example.com/', 'http://API.Example.COM./x', 'http://a.b.internal.example.org/']
)
def test_allowed_hosts_exact_and_wildcard(url: str) -> None:
    HttpProbePolicy(allowed_hosts=ALLOWLIST).check_url(url)


@pytest.mark.parametrize(
    'url', ['http://example.com/', 'http://notapi.example.com/', 'http://internal.example.org/', 'http://evil.com/']
)
def test_hosts_outside_the_allowlist_are_refused(url: str) -> None:
    with pytest.raises(HttpProbePolicyViolation, match='is not in allowed_hosts'):
        HttpProbePolicy(allowed_hosts=ALLOWLIST).check_url(url)


def test_allowed_hosts_accepts_bracketed_ipv6() -> None:
    HttpProbePolicy(allowed_hosts=('[::1]',)).check_url('http://[::1]:8080/')


@pytest.mark.parametrize(
    'host',
    [
        '127.0.0.1',
        '[::1]',
        '[::ffff:127.0.0.1]',
        '169.254.169.254',
        '10.0.0.1',
        '172.16.0.1',
        '192.168.1.1',
        '100.64.0.1',
        '[fc00::1]',
        '[fe80::1]',
        '0.0.0.0',
        '[::]',
        '224.0.0.1',
        '[ff02::1]',
    ],
)
def test_block_private_networks_refuses_literal(host: str) -> None:
    with pytest.raises(HttpProbePolicyViolation, match=r'^address .* is not a global address$'):
        STRICT.check_url(f'http://{host}/')


@pytest.mark.parametrize('host', ['8.8.8.8', '[2001:4860:4860::8888]', 'svc', '2130706433'])
def test_block_private_networks_accepts_global_and_names(host: str) -> None:
    # '2130706433' is 127.0.0.1 for the resolver, not for ``ipaddress``: it is caught at resolution time
    STRICT.check_url(f'http://{host}/')


def test_blocked_networks_from_strings_and_objects() -> None:
    policy = HttpProbePolicy(blocked_networks=('10.1.2.3/8', IPv4Network('192.168.0.0/16')))

    assert policy.blocked_networks == (IPv4Network('10.0.0.0/8'), IPv4Network('192.168.0.0/16'))
    assert policy.needs_resolution is True
    with pytest.raises(HttpProbePolicyViolation, match=r'^address 10.1.2.3 is in blocked network 10.0.0.0/8$'):
        policy.check_url('http://10.1.2.3/')
    policy.check_url('http://127.0.0.1/')


def test_invalid_network_names_the_field() -> None:
    with pytest.raises(ValueError, match="blocked_networks: invalid network 'nope'"):
        HttpProbePolicy(blocked_networks=('nope',))
    with pytest.raises(ValueError, match='allowed_networks'):
        HttpProbePolicy(allowed_networks=('10.0.0.0/33',))


def test_ipv6_network_never_matches_ipv4() -> None:
    HttpProbePolicy(blocked_networks=('::/0',)).check_url('http://8.8.8.8/')


def test_allowed_networks_win_over_blocking() -> None:
    policy = HttpProbePolicy(block_private_networks=True, allowed_networks=['10.0.0.0/8'])
    policy.check_url('http://10.1.2.3/')
    with pytest.raises(HttpProbePolicyViolation):
        policy.check_url('http://127.0.0.1/')

    policy = HttpProbePolicy(blocked_networks=('0.0.0.0/0',), allowed_networks=('8.8.8.0/24',))
    policy.check_url('http://8.8.8.8/')
    with pytest.raises(HttpProbePolicyViolation):
        policy.check_url('http://1.1.1.1/')


def test_ipv4_mapped_address_follows_ipv4_rules() -> None:
    with pytest.raises(HttpProbePolicyViolation, match=r'blocked network 10.0.0.0/8'):
        HttpProbePolicy(blocked_networks=('10.0.0.0/8',)).check_url('http://[::ffff:10.0.0.1]/')


def test_negative_max_redirects_is_rejected() -> None:
    with pytest.raises(ValueError, match='max_redirects'):
        HttpProbePolicy(max_redirects=-1)


def test_normalized_policies_compare_equal_and_hash() -> None:
    a = HttpProbePolicy(allowed_schemes=['HTTPS'], allowed_hosts=['Svc.'], blocked_networks=['10.0.0.0/8'])
    b = HttpProbePolicy(
        allowed_schemes=('https',), allowed_hosts=('svc',), blocked_networks=(IPv4Network('10.0.0.0/8'),)
    )

    assert a == b
    assert hash(a) == hash(b)


def test_blocked_reason_is_none_for_a_global_address() -> None:
    assert STRICT.blocked_reason(ip_address('8.8.8.8')) is None
    assert STRICT.blocked_reason(ip_address('10.0.0.1')) == 'is not a global address'


def test_normalize_host() -> None:
    assert normalize_host('[::1]') == '::1'
    assert normalize_host('Example.COM.') == 'example.com'
    assert normalize_host('пример.рф') == 'xn--e1afmkfd.xn--p1ai'


@pytest.mark.asyncio
async def test_check_refuses_when_any_resolved_address_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve, calls = fake_resolver({'svc': ['8.8.8.8', '10.0.0.5']})
    monkeypatch.setattr(policy_module, 'resolve_host', resolve)

    with pytest.raises(HttpProbePolicyViolation, match=r'^svc resolves to 10.0.0.5, which is not a global address$'):
        await STRICT.check('http://svc:8080/')

    assert calls == [('svc', 8080)]


@pytest.mark.asyncio
async def test_check_passes_when_every_address_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve, _ = fake_resolver({'svc': ['8.8.8.8', '2001:4860:4860::8888']})
    monkeypatch.setattr(policy_module, 'resolve_host', resolve)

    parts = await STRICT.check('http://svc/')

    assert parts.hostname == 'svc'


@pytest.mark.asyncio
async def test_no_resolution_without_network_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    async def resolve(host: str, port: int | None = None) -> tuple[Any, ...]:
        raise AssertionError('must not resolve')

    monkeypatch.setattr(policy_module, 'resolve_host', resolve)

    await HttpProbePolicy().check('http://svc/')
    await HttpProbePolicy(allowed_hosts=('svc',), allowed_networks=('10.0.0.0/8',)).check('http://svc/')


@pytest.mark.asyncio
async def test_no_resolution_for_an_ip_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve, calls = fake_resolver({})
    monkeypatch.setattr(policy_module, 'resolve_host', resolve)

    await HttpProbePolicy(block_private_networks=True, allowed_networks=('127.0.0.0/8',)).check('http://127.0.0.1/')

    assert calls == []


@pytest.mark.asyncio
async def test_resolve_host_localhost() -> None:
    addresses = await resolve_host('localhost')

    assert ip_address('127.0.0.1') in addresses or ip_address('::1') in addresses


@pytest.mark.asyncio
async def test_resolve_host_strips_zone_ids_and_duplicates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def getaddrinfo(host: str, port: int | None, **kwargs: Any) -> list[Any]:
        entry = (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('fe80::1%lo0', 0, 0, 1))
        return [entry, entry]

    monkeypatch.setattr(asyncio.get_running_loop(), 'getaddrinfo', getaddrinfo)

    assert await resolve_host('x') == (ip_address('fe80::1'),)
