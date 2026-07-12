from __future__ import annotations

import json

from alerts.config import load_alert_config
from alerts.service import run_alert_cycle
from data.alert_store import load_market_regime, load_portfolio_monitor
from data.history_store import compare_scans, load_latest_scan, load_previous_scan


def main() -> int:
    latest = load_latest_scan()
    current_scan_id = None
    if not latest.empty and "scan_id" in latest.columns:
        current_scan_id = str(latest.iloc[0]["scan_id"])
    previous = load_previous_scan(current_scan_id)
    comparison = compare_scans(latest, previous)

    result = run_alert_cycle(
        comparison=comparison,
        monitor=load_portfolio_monitor(),
        regime=load_market_regime(),
        config=load_alert_config(),
        send=True,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
