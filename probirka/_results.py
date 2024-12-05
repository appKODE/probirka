from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    started_at: datetime
    elapsed: timedelta
    name: str
    error: Optional[str]


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    info: Dict[str, Any]
    started_at: datetime
    total_elapsed: timedelta
    checks: Sequence[ProbeResult]
