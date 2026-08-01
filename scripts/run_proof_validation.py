from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

from engine.proof_validation import build_proof_report
from version import APP_VERSION


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Catalyst AI proof and performance report from a trade CSV.")
    parser.add_argument("trades_csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/proof_validation.json"))
    args = parser.parse_args()
    trades = pd.read_csv(args.trades_csv)
    report = build_proof_report(trades, build_version=APP_VERSION, configuration={"source": str(args.trades_csv)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"{report['verdict']} — {report['checks_passed']}/{report['checks_total']} checks passed")
    print(args.output)
    return 0 if report["verdict"] != "FAIL" else 2


if __name__ == "__main__":
    raise SystemExit(main())
