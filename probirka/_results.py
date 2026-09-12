from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True, order=True)
class ProbeResult:
    """
    Outcome of a single probe run.

    :param name: Probe name.
    :param ok: Whether the check passed.
    :param cached: ``True`` if served from cache, ``False`` if freshly computed with caching enabled,
        ``None`` if the probe has no TTL configured.
    :param started_at: When the check started, timezone-aware in the local zone of the host.
    :param elapsed: How long the check took, measured with a monotonic clock.
    :param info: Metadata added via :meth:`ProbeBase.add_info`.
    :param error: ``'ExcType: message'`` when the check failed with an exception or timed out.
    :param allow_failure: ``True`` if this probe is allowed to fail without affecting
        :attr:`ProbirkaResult.ok`. Effective value for the run: the probe's own setting,
        overridden by the group it was run in when that group sets ``allow_failure``.
    """

    name: str
    ok: bool
    cached: bool | None
    started_at: datetime
    elapsed: timedelta
    info: dict[str, Any] | None
    error: str | None
    allow_failure: bool = False

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-compatible representation of the result.

        ``started_at`` is an ISO 8601 string carrying the UTC offset, ``elapsed`` is the duration
        in seconds. ``info`` is returned as is.
        """
        return {
            'name': self.name,
            'ok': self.ok,
            'cached': self.cached,
            'started_at': self.started_at.isoformat(),
            'elapsed': self.elapsed.total_seconds(),
            'info': self.info,
            'error': self.error,
            'allow_failure': self.allow_failure,
        }


@dataclass(frozen=True, order=True)
class ProbirkaResult:
    """
    Aggregated outcome of a :meth:`Probirka.run` call.

    :param ok: ``True`` if every probe without ``allow_failure`` passed. Probes with
        ``allow_failure`` may fail or time out without affecting it.
    :param started_at: When the run started, timezone-aware in the local zone of the host.
    :param elapsed: How long the whole run took, measured with a monotonic clock.
    :param info: Metadata added via :meth:`Probirka.add_info`.
    :param checks: Per-probe results in registration order.
    :param error: Timeout message when the overall timeout was hit (even if only probes
        with ``allow_failure`` did not finish), otherwise ``None``.
    """

    ok: bool
    started_at: datetime
    elapsed: timedelta
    info: dict[str, Any] | None
    checks: Sequence[ProbeResult]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        JSON-compatible representation of the result, shared by all framework integrations.

        ``started_at`` is an ISO 8601 string carrying the UTC offset, ``elapsed`` is the duration
        in seconds, ``checks`` is a list of :meth:`ProbeResult.to_dict`. ``info`` is returned as is.
        """
        return {
            'ok': self.ok,
            'started_at': self.started_at.isoformat(),
            'elapsed': self.elapsed.total_seconds(),
            'info': self.info,
            'checks': [check.to_dict() for check in self.checks],
            'error': self.error,
        }
