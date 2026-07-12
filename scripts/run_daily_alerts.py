from __future__ import annotations

import argparse
import json

from alerts.config import load_alert_config
from alerts.runner import run_alert_job
from data.alert_store import load_market_regime, load_portfolio_monitor
from data.history_store import compare_scans, load_latest_scan, load_previous_scan


def build_inputs():
    latest = load_latest_scan()
    current_scan_id = None
    if not latest.empty and "scan_id" in latest.columns:
        current_scan_id = str(latest.iloc[0]["scan_id"])
    previous = load_previous_scan(current_scan_id)
    return compare_scans(latest, previous), load_portfolio_monitor(), load_market_regime()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Catalyst AI scheduled alerts")
    parser.add_argument("--trigger", default="scheduler", help="Status label for this run")
    args = parser.parse_args()

    comparison, monitor, regime = build_inputs()
    result = run_alert_job(
        comparison=comparison,
        monitor=monitor,
        regime=regime,
        config=load_alert_config(),
        trigger=args.trigger,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
