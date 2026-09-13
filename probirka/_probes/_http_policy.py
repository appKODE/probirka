"""
Security policy for the HTTP probes: which URLs a probe may request, which redirects it may follow.

A health endpoint requests whatever URL it was configured with. When that URL, or a redirect the
target answers with, points at an internal host or a cloud metadata service, the probe becomes a
server-side request forgery (SSRF) primitive. :class:`HttpProbePolicy` limits what a probe will
contact. Its defaults are deliberately soft: any ``http`` or ``https`` URL is fine and redirects are
not followed. Everything stricter is opt-in.
"""

from __future__ import annotations

import socket
from asyncio import get_running_loop
from collections.abc import Collection
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import TypeAlias, cast
from urllib.parse import SplitResult, urlsplit

from probirka._probes._common import ProbeFailure
from probirka._redact import mask_url

IPAddress: TypeAlias = IPv4Address | IPv6Address
IPNetwork: TypeAlias = IPv4Network | IPv6Network


class HttpProbePolicyViolation(ProbeFailure):
    """
    Raised when a URL, a redirect target or a resolved address is refused by :class:`HttpProbePolicy`.

    A :class:`ProbeFailure`: the check ran and the result is a failure with
    ``'HttpProbePolicyViolation: ...'`` in :attr:`ProbeResult.error`. In the probe constructor the
    same violation is reported as a :class:`ValueError`.
    """


def normalize_host(host: str) -> str:
    """
    Return ``host`` in the form used for comparisons: lowercase, without brackets or a trailing dot.

    Internationalized names are converted to their IDNA (``xn--``) form when possible.

    :param host: A host name or IP literal, possibly in ``[...]``.
    :return: The normalized host.
    """
    host = host.strip().lower().rstrip('.')
    if host.startswith('[') and host.endswith(']'):
        host = host[1:-1]
    try:
        return host.encode('idna').decode('ascii')
    except UnicodeError:
        return host


def _parse_networks(values: Collection[str | IPNetwork], name: str) -> tuple[IPNetwork, ...]:
    networks: list[IPNetwork] = []
    for value in values:
        try:
            networks.append(ip_network(value, strict=False))
        except ValueError as exc:
            msg = f'{name}: invalid network {value!r}'
            raise ValueError(msg) from exc
    return tuple(networks)


def _literal_ip(host: str) -> IPAddress | None:
    try:
        return ip_address(host)
    except ValueError:
        return None


def _unmap(address: IPAddress) -> IPAddress:
    """``::ffff:10.0.0.1`` is ``10.0.0.1``; classify it as such."""
    if isinstance(address, IPv6Address) and address.ipv4_mapped is not None:
        return address.ipv4_mapped
    return address


async def resolve_host(host: str, port: int | None = None) -> tuple[IPAddress, ...]:
    """
    Return every address ``host`` currently resolves to, in resolver order and without duplicates.

    Uses the event loop's ``getaddrinfo``; a lookup failure raises :class:`socket.gaierror`.

    :param host: The host name to resolve.
    :param port: The port, passed to the resolver as a hint.
    :return: The resolved addresses.
    """
    infos = await get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    # a link-local IPv6 address may carry a zone id, ``fe80::1%en0``, which ``ip_address`` rejects
    addresses = (ip_address(str(sockaddr[0]).partition('%')[0]) for *_, sockaddr in infos)
    return tuple(dict.fromkeys(addresses))


@dataclass(frozen=True)
class HttpProbePolicy:
    """
    What an HTTP probe may request. Pass it to a probe as ``policy=``.

    The URL given to the probe is checked against the policy when the probe is created (a
    violation is a :class:`ValueError`), and every URL the probe is about to request, redirect
    targets included, is checked again before the request (a violation is a
    :class:`HttpProbePolicyViolation` in :attr:`ProbeResult.error`). With the defaults any
    ``http`` or ``https`` URL passes and redirects are not followed.

    Network rules (``block_private_networks``, ``blocked_networks``, ``allowed_networks``) apply
    to IP literals in the URL and, when at least one blocking rule is set, to the addresses a host
    name resolves to. The name is resolved by the probe before the request, and the request is
    refused if *any* resolved address is blocked. The client library resolves the name again on
    its own, so a resolver that answers differently the second time (DNS rebinding) can still
    reach a blocked address; the policy is not a substitute for network-level controls.

    :param allowed_schemes: URL schemes a probe may request; ``('http', 'https')`` by default.
    :param allowed_hosts: Host names a probe may request, exactly (``api.example.com``) or as a
        wildcard for any subdomain (``*.example.com`` matches ``a.example.com`` and
        ``a.b.example.com`` but not ``example.com``). ``None``, the default, allows any host.
    :param block_private_networks: Refuse addresses that are not globally routable: loopback,
        RFC 1918 and ``fc00::/7`` private ranges, link-local (including the ``169.254.169.254``
        cloud metadata address), carrier-grade NAT, multicast, unspecified and reserved ranges.
        ``False`` by default.
    :param blocked_networks: Networks to refuse, as ``'10.0.0.0/8'`` strings or
        :mod:`ipaddress` network objects.
    :param allowed_networks: Networks that are always allowed, taking precedence over both
        ``block_private_networks`` and ``blocked_networks``.
    :param follow_redirects: Follow ``301``, ``302``, ``303``, ``307`` and ``308`` responses.
        Every redirect target is checked against the policy first; request headers are not sent
        to a different origin. ``False`` by default: a redirect is then an ordinary status code
        compared with ``expected_status``.
    :param max_redirects: How many redirects to follow at most; ``5`` by default.
    """

    allowed_schemes: Collection[str] = ('http', 'https')
    allowed_hosts: Collection[str] | None = None
    block_private_networks: bool = False
    blocked_networks: Collection[str | IPNetwork] = ()
    allowed_networks: Collection[str | IPNetwork] = ()
    follow_redirects: bool = False
    max_redirects: int = 5

    def __post_init__(self) -> None:
        schemes = frozenset(scheme.lower() for scheme in self.allowed_schemes)
        if not schemes:
            msg = 'allowed_schemes must not be empty'
            raise ValueError(msg)
        object.__setattr__(self, 'allowed_schemes', schemes)
        if self.allowed_hosts is not None:
            object.__setattr__(self, 'allowed_hosts', frozenset(normalize_host(host) for host in self.allowed_hosts))
        object.__setattr__(self, 'blocked_networks', _parse_networks(self.blocked_networks, 'blocked_networks'))
        object.__setattr__(self, 'allowed_networks', _parse_networks(self.allowed_networks, 'allowed_networks'))
        if self.max_redirects < 0:
            msg = 'max_redirects must be >= 0'
            raise ValueError(msg)

    @property
    def needs_resolution(self) -> bool:
        """Whether a host name has to be resolved before the request to enforce the network rules."""
        return self.block_private_networks or bool(self.blocked_networks)

    def check_url(self, url: str) -> SplitResult:
        """
        Check a URL without touching the network: scheme, host, allowlist and IP literals.

        :param url: The URL about to be requested.
        :return: The parsed URL, so that callers do not parse it twice.
        :raises HttpProbePolicyViolation: If the URL is malformed or refused.
        """
        try:
            parts = urlsplit(url)
            parts.port  # noqa: B018 -- raises ValueError for a non-numeric or out-of-range port
        except ValueError as exc:
            msg = f'malformed URL {mask_url(url)}: {exc}'
            raise HttpProbePolicyViolation(msg) from None
        if parts.scheme.lower() not in self.allowed_schemes:
            msg = f'scheme {parts.scheme!r} is not allowed'
            raise HttpProbePolicyViolation(msg)
        if not parts.hostname:
            msg = f'URL {mask_url(url)} has no host'
            raise HttpProbePolicyViolation(msg)
        host = normalize_host(parts.hostname)
        if self.allowed_hosts is not None and not self._host_allowed(host):
            msg = f'host {host!r} is not in allowed_hosts'
            raise HttpProbePolicyViolation(msg)
        literal = _literal_ip(host)
        if literal is not None:
            self.check_address(literal)
        return parts

    def _host_allowed(self, host: str) -> bool:
        for entry in cast('frozenset[str]', self.allowed_hosts):
            if entry.startswith('*.'):
                if host.endswith(entry[1:]):
                    return True
            elif host == entry:
                return True
        return False

    def blocked_reason(self, address: IPAddress) -> str | None:
        """
        Explain why ``address`` may not be contacted, or return ``None`` if it may.

        :param address: A resolved or literal IP address.
        :return: A short reason such as ``'is not a global address'``, or ``None``.
        """
        address = _unmap(address)
        if any(address in network for network in cast('tuple[IPNetwork, ...]', self.allowed_networks)):
            return None
        # multicast counts as global in ``ipaddress``, so it has to be refused explicitly
        if self.block_private_networks and (not address.is_global or address.is_multicast):
            return 'is not a global address'
        for network in cast('tuple[IPNetwork, ...]', self.blocked_networks):
            if address in network:
                return f'is in blocked network {network}'
        return None

    def check_address(self, address: IPAddress, *, host: str | None = None) -> None:
        """
        Refuse ``address`` if the network rules block it.

        :param address: A resolved or literal IP address.
        :param host: The host name that resolved to it, for the error message.
        :raises HttpProbePolicyViolation: If the address is blocked.
        """
        reason = self.blocked_reason(address)
        if reason is None:
            return
        if host is None:
            msg = f'address {address} {reason}'
            raise HttpProbePolicyViolation(msg)
        msg = f'{host} resolves to {address}, which {reason}'
        raise HttpProbePolicyViolation(msg)

    async def check_resolution(self, parts: SplitResult) -> None:
        """
        Resolve the host of a URL that passed :meth:`check_url` and refuse it if any address is blocked.

        Does nothing when no network rule needs resolution, or when the host is an IP literal
        (already checked by :meth:`check_url`).

        :param parts: The parsed URL returned by :meth:`check_url`.
        :raises HttpProbePolicyViolation: If a resolved address is blocked.
        :raises socket.gaierror: If the host cannot be resolved.
        """
        if not self.needs_resolution or not parts.hostname:
            return
        host = normalize_host(parts.hostname)
        if _literal_ip(host) is not None:
            return
        for address in await resolve_host(host, parts.port):
            self.check_address(address, host=host)

    async def check(self, url: str) -> SplitResult:
        """
        Run every check on a URL: :meth:`check_url`, then :meth:`check_resolution`.

        :param url: The URL about to be requested.
        :return: The parsed URL.
        :raises HttpProbePolicyViolation: If the URL is refused.
        """
        parts = self.check_url(url)
        await self.check_resolution(parts)
        return parts
