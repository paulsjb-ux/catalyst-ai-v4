from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib


@dataclass(frozen=True)
class AlertEvent:
    alert_type: str
    severity: str
    title: str
    message: str
    ticker: str = ""
    source: str = "catalyst"
    created_at: str = ""
    fingerprint: str = ""

    def normalised(self) -> "AlertEvent":
        created_at = self.created_at or datetime.now(timezone.utc).isoformat()
        ticker = self.ticker.upper().strip()
        raw = "|".join([
            self.alert_type.strip().upper(),
            ticker,
            self.title.strip(),
            self.message.strip(),
        ])
        fingerprint = self.fingerprint or hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
        return AlertEvent(
            alert_type=self.alert_type.strip().upper(),
            severity=self.severity.strip().upper(),
            title=self.title.strip(),
            message=self.message.strip(),
            ticker=ticker,
            source=self.source.strip() or "catalyst",
            created_at=created_at,
            fingerprint=fingerprint,
        )

    def to_dict(self) -> dict:
        return asdict(self.normalised())
