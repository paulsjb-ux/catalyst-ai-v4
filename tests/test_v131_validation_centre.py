from pathlib import Path

import pandas as pd

from engine.proof_validation import build_proof_report
from engine.validation_report import (
    build_validation_pdf,
    comparison_rows,
    list_validation_reports,
    load_json_report,
    save_validation_report,
    summary_frame,
)


def _trades() -> pd.DataFrame:
    return pd.DataFrame({
        "ticker": ["JPM", "MSFT", "JPM", "MSFT"],
        "entry_date": ["2023-01-01", "2023-02-01", "2024-01-01", "2024-02-01"],
        "exit_date": ["2023-01-10", "2023-02-10", "2024-01-10", "2024-02-10"],
        "score": [82, 84, 83, 85],
        "confidence_regime": ["BULL", "BULL", "RANGE", "RANGE"],
        "return_pct": [2.0, -0.5, 1.5, -0.25],
    })


def test_comparison_rows_and_frame():
    current = build_proof_report(_trades(), build_version="13.1")
    baseline = build_proof_report(_trades().assign(return_pct=[1.0, -1.0, 0.5, -0.5]), build_version="9.2.1")
    rows = comparison_rows(current, baseline)
    assert any(row["metric"] == "Profit factor" for row in rows)
    frame = summary_frame(current, baseline)
    assert list(frame.columns) == ["metric", "current", "baseline", "change"]


def test_save_list_and_load_report(tmp_path: Path):
    report = build_proof_report(_trades(), build_version="13.1")
    path = save_validation_report(report, history_dir=tmp_path)
    assert path.exists()
    loaded = load_json_report(path)
    assert loaded and loaded["metadata"]["build"] == "13.1"
    history = list_validation_reports(tmp_path)
    assert len(history) == 1
    assert history.iloc[0]["verdict"] == report["verdict"]


def test_validation_pdf_is_created():
    report = build_proof_report(_trades(), build_version="13.1")
    pdf = build_validation_pdf(report)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
