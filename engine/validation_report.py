from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import json
from pathlib import Path
from typing import Any

import pandas as pd


DEFAULT_HISTORY_DIR = Path("storage/validation/history")


def comparison_rows(current: dict[str, Any], baseline: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return a compact, stable comparison against a previous proof report."""
    baseline = baseline or {}
    current_overall = current.get("overall", {}) or {}
    baseline_overall = baseline.get("overall", {}) or {}
    current_stress = current.get("stress", {}) or {}
    baseline_stress = baseline.get("stress", {}) or {}

    specs = [
        ("Trades", current_overall.get("trades"), baseline_overall.get("trades"), False),
        ("Win rate %", current_overall.get("win_rate_pct"), baseline_overall.get("win_rate_pct"), True),
        ("Total return %", current_overall.get("total_return_pct"), baseline_overall.get("total_return_pct"), True),
        ("Profit factor", current_overall.get("profit_factor"), baseline_overall.get("profit_factor"), True),
        ("Average trade %", current_overall.get("average_return_pct"), baseline_overall.get("average_return_pct"), True),
        ("Max drawdown %", current_overall.get("max_drawdown_pct"), baseline_overall.get("max_drawdown_pct"), True),
        ("Stress profit factor", current_stress.get("profit_factor"), baseline_stress.get("profit_factor"), True),
        ("Stress return %", current_stress.get("total_return_pct"), baseline_stress.get("total_return_pct"), True),
        ("Profitable year ratio", current.get("profitable_year_ratio"), baseline.get("profitable_year_ratio"), True),
    ]
    rows: list[dict[str, Any]] = []
    for metric, current_value, baseline_value, calculate_delta in specs:
        delta: float | None = None
        if calculate_delta:
            try:
                delta = round(float(current_value) - float(baseline_value), 4)
            except (TypeError, ValueError):
                delta = None
        rows.append({
            "metric": metric,
            "current": current_value,
            "baseline": baseline_value,
            "change": delta,
        })
    return rows


def summary_frame(report: dict[str, Any], baseline: dict[str, Any] | None = None) -> pd.DataFrame:
    rows = comparison_rows(report, baseline)
    return pd.DataFrame(rows)


def load_json_report(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    if not target.exists():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_validation_report(
    report: dict[str, Any],
    *,
    history_dir: str | Path = DEFAULT_HISTORY_DIR,
) -> Path:
    directory = Path(history_dir)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    build = str(report.get("metadata", {}).get("build", "unknown")).replace("/", "-")
    path = directory / f"catalyst_validation_v{build}_{stamp}.json"
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return path


def list_validation_reports(history_dir: str | Path = DEFAULT_HISTORY_DIR) -> pd.DataFrame:
    directory = Path(history_dir)
    if not directory.exists():
        return pd.DataFrame(columns=["file", "build", "generated_utc", "verdict", "checks", "path"])
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("catalyst_validation_*.json"), reverse=True):
        report = load_json_report(path)
        if not report:
            continue
        metadata = report.get("metadata", {}) or {}
        rows.append({
            "file": path.name,
            "build": metadata.get("build", "-"),
            "generated_utc": metadata.get("generated_utc", "-"),
            "verdict": report.get("verdict", "-"),
            "checks": f"{report.get('checks_passed', 0)}/{report.get('checks_total', 0)}",
            "path": str(path),
        })
    return pd.DataFrame(rows)


def build_validation_pdf(
    report: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab. Install requirements.txt.") from exc

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Catalyst AI Validation Report",
        author="Catalyst AI",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10))
    metadata = report.get("metadata", {}) or {}
    overall = report.get("overall", {}) or {}
    stress = report.get("stress", {}) or {}
    story = [
        Paragraph("Catalyst AI Validation Report", styles["Title"]),
        Paragraph(
            f"Build v{metadata.get('build', '-')} | Generated {metadata.get('generated_utc', '-')} | "
            f"Configuration {metadata.get('configuration_hash', '-')} | Trades {metadata.get('trades_hash', '-')}",
            styles["Small"],
        ),
        Spacer(1, 7),
        Paragraph(f"Verdict: {report.get('verdict', '-')} ({report.get('checks_passed', 0)}/{report.get('checks_total', 0)} checks)", styles["Heading2"]),
    ]

    metrics = [
        ["Trades", overall.get("trades", "-"), "Win rate", overall.get("win_rate_pct", "-")],
        ["Total return", f"{overall.get('total_return_pct', '-')}%", "Profit factor", overall.get("profit_factor", "-")],
        ["Average trade", f"{overall.get('average_return_pct', '-')}%", "Max drawdown", f"{overall.get('max_drawdown_pct', '-')}%"],
        ["Stress return", f"{stress.get('total_return_pct', '-')}%", "Stress PF", stress.get("profit_factor", "-")],
    ]
    table = Table(metrics, colWidths=[38*mm, 38*mm, 42*mm, 38*mm])
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#bfdbfe")),
        ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (2,0), (2,-1), colors.HexColor("#eff6ff")),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME", (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    story.extend([table, Spacer(1, 9)])

    checks = [["Check", "Result"]] + [[k.replace("_", " ").title(), "PASS" if v else "FAIL"] for k, v in (report.get("checks", {}) or {}).items()]
    check_table = Table(checks, colWidths=[75*mm, 30*mm], repeatRows=1)
    check_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1d4ed8")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("PADDING", (0,0), (-1,-1), 4),
    ]))
    story.extend([Paragraph("Proof checks", styles["Heading2"]), check_table, Spacer(1, 9)])

    if baseline:
        comparison = summary_frame(report, baseline)
        data = [["Metric", "Current", "Baseline", "Change"]] + comparison.astype(object).where(pd.notna(comparison), "-").values.tolist()
        comp_table = Table(data, repeatRows=1)
        comp_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0,0), (-1,-1), 7.5),
            ("PADDING", (0,0), (-1,-1), 3.5),
        ]))
        story.extend([Paragraph("Comparison with baseline", styles["Heading2"]), comp_table, Spacer(1, 9)])

    def add_breakdown(title: str, records: list[dict[str, Any]], limit: int = 15) -> None:
        if not records:
            return
        frame = pd.DataFrame(records).head(limit)
        preferred = [c for c in [frame.columns[0], "trades", "win_rate_pct", "average_return_pct", "total_return_pct", "profit_factor", "max_drawdown_pct"] if c in frame.columns]
        frame = frame[preferred]
        data = [[str(c).replace("_", " ").title() for c in frame.columns]] + frame.astype(object).where(pd.notna(frame), "-").values.tolist()
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), .3, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0,0), (-1,-1), 7),
            ("PADDING", (0,0), (-1,-1), 3),
        ]))
        story.extend([Paragraph(title, styles["Heading2"]), t, Spacer(1, 7)])

    story.append(PageBreak())
    add_breakdown("Year-by-year performance", report.get("by_year", []), 20)
    add_breakdown("Score-band performance", report.get("by_score_band", []), 20)
    add_breakdown("Ticker performance", report.get("by_ticker", []), 20)
    add_breakdown("Regime performance", report.get("by_regime", []), 20)
    add_breakdown("Holding-period performance", report.get("by_holding_period", []), 20)
    add_breakdown("Adaptive confidence performance", report.get("by_adaptive_confidence", []), 20)
    add_breakdown("Adaptive restrictions", report.get("decision_filter_diagnostics", []), 20)
    add_breakdown("Stress-driver decomposition", report.get("stress_decomposition", []), 20)
    add_breakdown("Feature attribution", report.get("feature_attribution", []), 20)
    add_breakdown("Confidence calibration", report.get("confidence_calibration", []), 20)
    story.extend([
        Spacer(1, 8),
        Paragraph("Disclosures", styles["Heading2"]),
        *[Paragraph(f"• {line}", styles["Small"]) for line in report.get("disclosures", [])],
    ])
    doc.build(story)
    return output.getvalue()
