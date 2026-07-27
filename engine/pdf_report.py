from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd


def _safe(value: Any, default: str = "-") -> str:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass
    return str(value)


def build_trading_desk_pdf(
    *,
    version: str,
    summary: dict[str, Any] | None = None,
    regime: dict[str, Any] | None = None,
    opportunities: pd.DataFrame | None = None,
) -> bytes:
    """Create a compact Catalyst AI trading-desk PDF report."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab. Install requirements.txt.") from exc

    summary = summary or {}
    regime = regime or {}
    opportunities = opportunities if isinstance(opportunities, pd.DataFrame) else pd.DataFrame()

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title="Catalyst AI Trading Desk Report",
        author="Catalyst AI",
    )
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Catalyst AI - Trading Desk Report", styles["Title"]),
        Paragraph(f"Version {_safe(version)}", styles["Normal"]),
        Spacer(1, 8),
    ]

    market_rows = [
        ["Market regime", _safe(regime.get("regime"))],
        ["Risk posture", _safe(regime.get("risk_label"))],
        ["Market score", _safe(regime.get("market_score"))],
        ["Scanned", _safe(summary.get("scanned"))],
        ["BUY", _safe(summary.get("buy_count"))],
        ["WATCH", _safe(summary.get("watch_count"))],
    ]
    market_table = Table(market_rows, colWidths=[55 * mm, 105 * mm])
    market_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eff6ff")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([Paragraph("Market Summary", styles["Heading2"]), market_table, Spacer(1, 12)])

    story.append(Paragraph("Top Opportunities", styles["Heading2"]))
    if opportunities.empty:
        story.append(Paragraph("No ranked opportunities are available.", styles["Normal"]))
    else:
        columns = [c for c in ["ticker", "signal", "confidence", "score", "trend", "risk_reward"] if c in opportunities.columns]
        frame = opportunities[columns].head(10).copy()
        data = [[str(c).replace("_", " ").title() for c in columns]]
        for _, row in frame.iterrows():
            data.append([_safe(row.get(c)) for c in columns])
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    story.extend([
        Spacer(1, 14),
        Paragraph("Decision support only - not financial advice.", styles["Italic"]),
    ])
    doc.build(story)
    return output.getvalue()
