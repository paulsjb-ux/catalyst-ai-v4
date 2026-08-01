from __future__ import annotations
import pandas as pd
from engine.proof_validation import build_proof_report, configuration_hash, stress_test, trades_hash


def sample_trades() -> pd.DataFrame:
    return pd.DataFrame({
        "ticker": ["MSFT", "JPM", "MSFT", "JPM", "AAPL", "MSFT"],
        "entry_date": pd.to_datetime(["2023-01-01", "2023-03-01", "2024-01-01", "2024-03-01", "2025-01-01", "2025-03-01"]),
        "exit_date": pd.to_datetime(["2023-01-10", "2023-03-10", "2024-01-10", "2024-03-10", "2025-01-10", "2025-03-10"]),
        "score": [82, 84, 87, 82, 91, 84],
        "score_band": ["80-84", "80-84", "85-89", "80-84", "90-94", "80-84"],
        "confidence_regime": ["BULL", "RANGE", "BULL", "RANGE", "BULL", "BULL"],
        "v92_portfolio_return_pct": [1.0, 0.5, -0.3, 0.7, -0.2, 0.8],
    })


def test_report_contains_required_diagnostics():
    report = build_proof_report(sample_trades(), build_version="9.2.1", configuration={"minimum_score": 78})
    assert report["metadata"]["build"] == "9.2.1"
    assert report["overall"]["trades"] == 6
    assert report["by_year"]
    assert report["by_ticker"]
    assert report["by_score_band"]
    assert report["by_regime"]
    assert report["checks_total"] == 6


def test_stress_test_reduces_average_return():
    raw = sample_trades()["v92_portfolio_return_pct"].mean()
    stressed = stress_test(sample_trades())
    assert stressed["average_return_pct"] < raw


def test_hashes_are_reproducible():
    frame = sample_trades()
    assert trades_hash(frame) == trades_hash(frame.copy())
    assert configuration_hash({"b": 2, "a": 1}) == configuration_hash({"a": 1, "b": 2})
