"""
Keep secrets out of health check output.

Two complementary techniques, both stdlib-only:

* **known values** — a probe registers the password of its connection string and the values
  of its request headers, and :func:`redact_secrets` replaces them wherever they show up in a
  message from the client library (the ``no_log`` approach of Ansible);
* **shape-based** — :func:`redact_value` walks the ``info`` metadata and masks values under
  suspicious keys (``password``, ``token``, ``api_key``, ...) and passwords inside URL-like
  strings (the approach of Django's ``SafeExceptionReporterFilter`` and Sentry's
  ``EventScrubber``).

Only the password part of a URL is masked, never the user name, host or database: those are
what makes an error message useful, and it is what SQLAlchemy and Celery do as well.
"""

from __future__ import annotations

import re

from base64 import b64encode
from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import unquote, urlsplit, urlunsplit

MASK = '***'
"""What a secret is replaced with."""

MIN_SECRET_LENGTH = 4
"""Shorter values are never treated as secrets: masking them would garble unrelated text."""

_SENSITIVE_KEY = re.compile(r'api|auth|token|key|secret|pass|signature|cookie|credential', re.IGNORECASE)
"""Keys of ``info`` whose value is masked whole. The list follows Django's ``HIDDEN_SETTINGS``."""

_URL_PASSWORD = re.compile(r'(://[^/?#\s@]*:)([^/?#\s]+)(@)')
"""``scheme://user:password@host`` — group 2 is the password, ``@`` inside it included."""

_SENSITIVE_QUERY_PARAM = re.compile(
    r'([?&](?:token|access_token|key|api_key|apikey|secret|password|passwd|pwd|sig|signature|auth)=)([^&#\s]+)',
    re.IGNORECASE,
)
"""``?token=...`` and friends in a query string — group 2 is the value."""


def mask_url(url: str, mask: str = MASK) -> str:
    """
    Return ``url`` with its password replaced by ``mask``.

    Everything else is kept, so ``postgresql://app:hunter2@db:5432/app`` becomes
    ``postgresql://app:***@db:5432/app``. A URL without a password is returned unchanged.

    :param url: The URL or connection string.
    :param mask: The replacement for the password.
    :return: The masked URL.
    """
    try:
        parts = urlsplit(url)
        password = parts.password
    except ValueError:
        return _URL_PASSWORD.sub(rf'\1{mask}\3', url)
    if password is None:
        return url
    userinfo, _, hostinfo = parts.netloc.rpartition('@')
    username, _, _ = userinfo.partition(':')
    return urlunsplit(parts._replace(netloc=f'{username}:{mask}@{hostinfo}'))


def secrets_from_url(url: str | None) -> tuple[str, ...]:
    """
    The password of a URL in every form a client library may echo it.

    As written in the URL (``p%40ss``), decoded (``p@ss``), and as the HTTP basic auth
    credentials HTTP clients derive from the user info (``Basic`` + base64 of ``user:password``):
    httpx and aiohttp move ``user:pass@`` out of the URL into an ``Authorization`` header.

    :param url: The URL or connection string, ``None`` when the probe was given a client instead.
    :return: Strings to register with :meth:`ProbeBase._register_secrets`.
    """
    if not url:
        return ()
    username: str | None
    password: str | None
    try:
        parts = urlsplit(url)
        username, password = parts.username, parts.password
    except ValueError:
        match = _URL_PASSWORD.search(url)
        if match is None:
            return ()
        username, password = match.group(1)[len('://') : -len(':')], match.group(2)
    if not password:
        return ()
    decoded = unquote(password)
    basic = b64encode(f'{unquote(username or "")}:{decoded}'.encode()).decode()
    return _unique((password, decoded, basic))


def secrets_from_headers(headers: Mapping[str, str] | None) -> tuple[str, ...]:
    """
    The values of request headers, whole and without an auth scheme prefix.

    Every header value is treated as a secret: a probe sends only what is needed to be let
    in, and a ``Bearer`` token is a secret even under a custom header name. For
    ``Authorization: Bearer abc...`` both ``Bearer abc...`` and ``abc...`` are returned.

    :param headers: The request headers, ``None`` when there are none.
    :return: Strings to register with :meth:`ProbeBase._register_secrets`.
    """
    if not headers:
        return ()
    values: list[str] = []
    for value in headers.values():
        values.append(value)
        _, _, credentials = value.rpartition(' ')
        if credentials:
            values.append(credentials)
    return _unique(values)


def redact_secrets(text: str, secrets: Iterable[str]) -> str:
    """
    Replace every occurrence of the known ``secrets`` in ``text`` with :data:`MASK`.

    Longer secrets are replaced first, so a secret that contains another one does not leave
    a fragment behind.

    :param text: The text to clean, typically an exception message.
    :param secrets: Known secret values; empty and too short ones are ignored.
    :return: The cleaned text.
    """
    for secret in sorted(_unique(secrets), key=len, reverse=True):
        text = text.replace(secret, MASK)
    return text


def redact_string(text: str) -> str:
    """
    Mask passwords in URLs and sensitive query parameters found in ``text``.

    A heuristic for text whose origin is unknown, like a message from a client library or a
    value of ``info``: ``amqp://guest:guest@mq/`` becomes ``amqp://guest:***@mq/`` and
    ``?token=abc`` becomes ``?token=***``.

    :param text: The text to clean.
    :return: The cleaned text.
    """
    text = _URL_PASSWORD.sub(rf'\1{MASK}\3', text)
    return _SENSITIVE_QUERY_PARAM.sub(rf'\1{MASK}', text)


def redact_value(value: Any) -> Any:
    """
    Recursively clean a JSON-like value, as found in ``info``.

    Mappings get the value under a sensitive-looking key (``password``, ``api_key``,
    ``Authorization``, ...) replaced with :data:`MASK` whatever it is; other values are cleaned
    recursively. Lists and tuples are cleaned element-wise, strings go through
    :func:`redact_string`. Anything else — numbers, ``None``, arbitrary objects — is returned
    as is; the framework adapters clean the ``str()`` of an object when they serialize it.

    :param value: The value to clean.
    :return: A cleaned copy, or the same object when there was nothing to clean.
    """
    if isinstance(value, str):
        return redact_string(value)
    if isinstance(value, Mapping):
        return {
            key: MASK if isinstance(key, str) and _SENSITIVE_KEY.search(key) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def _unique(values: Iterable[str | None]) -> tuple[str, ...]:
    """Drop ``None``, duplicates and values shorter than :data:`MIN_SECRET_LENGTH`, keeping order."""
    seen: dict[str, None] = {}
    for value in values:
        if value and len(value) >= MIN_SECRET_LENGTH:
            seen.setdefault(value, None)
    return tuple(seen)
