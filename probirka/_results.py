from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True, order=True)
class ProbeResult:
    """
    Outcome of a single probe run.

    :param name: Probe name.
    :param ok: Whether the check passed.
    :param cached: ``True`` if served from cache, ``False`` if freshly computed with caching enabled,
        ``None`` if the probe has no TTL configured.
    :param started_at: When the check started.
    :param elapsed: How long the check took.
    :param info: Metadata added via :meth:`ProbeBase.add_info`.
    :param error: ``'ExcType: message'`` when the check failed with an exception or timed out.
    """

    name: str
    ok: bool
    cached: Optional[bool]
    started_at: datetime
    elapsed: timedelta
    info: Optional[Dict[str, Any]]
    error: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON-compatible representation of the result.

        ``started_at`` is an ISO 8601 string, ``elapsed`` is the duration in seconds.
        ``info`` is returned as is.
        """
        return {
            'name': self.name,
            'ok': self.ok,
            'cached': self.cached,
            'started_at': self.started_at.isoformat(),
            'elapsed': self.elapsed.total_seconds(),
            'info': self.info,
            'error': self.error,
        }


@dataclass(frozen=True, order=True)
class ProbirkaResult:
    """
    Aggregated outcome of a :meth:`Probirka.run` call.

    :param ok: ``True`` only if every probe passed and the overall timeout was not hit.
    :param started_at: When the run started.
    :param elapsed: How long the whole run took.
    :param info: Metadata added via :meth:`Probirka.add_info`.
    :param checks: Per-probe results in registration order.
    :param error: Reason for failure when the overall timeout was hit, otherwise ``None``.
    """

    ok: bool
    started_at: datetime
    elapsed: timedelta
    info: Optional[Dict[str, Any]]
    checks: Sequence[ProbeResult]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        JSON-compatible representation of the result, shared by all framework integrations.

        ``started_at`` is an ISO 8601 string, ``elapsed`` is the duration in seconds,
        ``checks`` is a list of :meth:`ProbeResult.to_dict`. ``info`` is returned as is.
        """
        return {
            'ok': self.ok,
            'started_at': self.started_at.isoformat(),
            'elapsed': self.elapsed.total_seconds(),
            'info': self.info,
            'checks': [check.to_dict() for check in self.checks],
            'error': self.error,
        }
