from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Sequence


@dataclass(frozen=True, order=True)
class ProbeResult:
    name: str
    ok: bool
    cached: Optional[bool]
    started_at: datetime
    elapsed: timedelta
    info: Optional[Dict[str, Any]]
    error: Optional[str]


@dataclass(frozen=True, order=True)
class ProbirkaResult:
    ok: bool
    started_at: datetime
    elapsed: timedelta
    info: Optional[Dict[str, Any]]
    checks: Sequence[ProbeResult]
