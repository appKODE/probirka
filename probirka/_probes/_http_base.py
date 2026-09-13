from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import SplitResult, urljoin

from probirka._probes._client_base import ClientProbeBase
from probirka._probes._common import ClientOrFactory, ProbeFailure
from probirka._probes._http_policy import HttpProbePolicy, HttpProbePolicyViolation, normalize_host
from probirka._redact import mask_url, secrets_from_headers, secrets_from_url

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping
    from datetime import timedelta

_DEFAULT_POLICY = HttpProbePolicy()
_SEE_OTHER = 303
_LEGACY_REDIRECTS = frozenset({301, 302})  # clients turn POST into GET here, as browsers do
_REDIRECT_STATUSES = _LEGACY_REDIRECTS | {_SEE_OTHER, 307, 308}
_DEFAULT_PORTS = {'http': 80, 'https': 443}


def _origin(parts: SplitResult) -> tuple[str, str | None, int | None]:
    scheme = parts.scheme.lower()
    host = normalize_host(parts.hostname) if parts.hostname else None
    return scheme, host, parts.port or _DEFAULT_PORTS.get(scheme)


def _redirect_method(status: int, method: str) -> str:
    """Return the method for the next hop, following the same rules as httpx and aiohttp."""
    upper = method.upper()
    if status == _SEE_OTHER and upper != 'HEAD':
        return 'GET'
    if status in _LEGACY_REDIRECTS and upper == 'POST':
        return 'GET'
    return method


class HttpProbeBase(ClientProbeBase):
    """
    Shared logic for HTTP probes: send a request and compare the status code.

    Redirects are never left to the client library. The probe sends every request with
    automatic following disabled and, when its :class:`HttpProbePolicy` allows redirects, follows
    them itself so that each target is checked against the policy first.

    Subclasses adapt a concrete client library by implementing :meth:`_temporary_client`
    (a client for when none was passed, honouring the probe ``timeout``) and :meth:`_request`.
    """

    def __init__(
        self,
        url: str,
        *,
        method: str = 'GET',
        expected_status: int | Collection[int] = (200,),
        headers: Mapping[str, str] | None = None,
        client: ClientOrFactory[Any] | None = None,
        policy: HttpProbePolicy | None = None,
        name: str | None = None,
        timeout: int | None = None,
        success_ttl: int | timedelta | None = None,
        failed_ttl: int | timedelta | None = None,
        allow_failure: bool = False,
    ) -> None:
        """
        Initialize the probe.

        :param url: URL to request. Must be absolute and allowed by ``policy``.
        :param method: HTTP method, ``GET`` by default.
        :param expected_status: Status code or codes treated as healthy, ``(200,)`` by default.
        :param headers: Extra request headers. Not sent to a different origin after a redirect.
        :param client: An existing client/session (or a callable returning one). If omitted, a
            temporary one is created per check with the probe ``timeout`` as its request timeout.
        :param policy: What the probe may request, see :class:`HttpProbePolicy`. The default
            allows any ``http``/``https`` URL and does not follow redirects.
        :param name: The name of the probe. Defaults to the class name.
        :param timeout: The timeout for the probe.
        :param success_ttl: Cache duration for successful results.
        :param failed_ttl: Cache duration for failed results.
        :param allow_failure: If True, a failure of this probe does not affect the overall result.
        :raises ValueError: If ``url`` is refused by ``policy``.
        """
        super().__init__(
            name=name,
            timeout=timeout,
            success_ttl=success_ttl,
            failed_ttl=failed_ttl,
            allow_failure=allow_failure,
        )
        self._policy = policy if policy is not None else _DEFAULT_POLICY
        try:
            self._policy.check_url(url)
        except HttpProbePolicyViolation as exc:
            msg = f'url refused by policy: {exc}'
            raise ValueError(msg) from exc
        self._url = url
        self._method = method
        self._expected_status = frozenset([expected_status] if isinstance(expected_status, int) else expected_status)
        self._headers = dict(headers) if headers else None
        self._client = client
        self._register_secrets(*secrets_from_url(url), *secrets_from_headers(self._headers))

    async def _request(
        self,
        client: Any,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
    ) -> tuple[int, str | None]:
        """
        Send one request with ``client`` without following redirects.

        :return: The response status code and the ``Location`` header, or ``None`` if absent.
        """
        raise NotImplementedError

    async def _check_redirect(self, url: str) -> SplitResult:
        try:
            return await self._policy.check(url)
        except HttpProbePolicyViolation as exc:
            msg = f'redirect to {mask_url(url)} refused: {exc}'
            raise HttpProbePolicyViolation(msg) from None

    async def _check_client(self, client: Any) -> None:
        policy = self._policy
        method, url, headers = self._method, self._url, self._headers
        origin = _origin(await policy.check(url))
        hops = 0
        while True:
            status, location = await self._request(client, method, url, headers)
            if not (policy.follow_redirects and status in _REDIRECT_STATUSES and location):
                break
            hops += 1
            if hops > policy.max_redirects:
                msg = f'too many redirects (more than {policy.max_redirects})'
                raise HttpProbePolicyViolation(msg)
            url = urljoin(url, location)
            if _origin(await self._check_redirect(url)) != origin:
                headers = None  # credentials meant for the original host must not leak elsewhere
            method = _redirect_method(status, method)
        if status not in self._expected_status:
            msg = f'unexpected status {status}'
            raise ProbeFailure(msg)
