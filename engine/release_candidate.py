from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from engine.paper_trading import performance_metrics, trades_frame


def portfolio_snapshot(state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {
            "equity": 0.0, "cash": 0.0, "market_value": 0.0, "net_pnl": 0.0,
            "return_pct": 0.0, "open_trades": 0, "closed_trades": 0, "win_rate_pct": 0.0,
            "expectancy": 0.0, "max_drawdown_pct": 0.0,
        }
    metrics = performance_metrics(state)
    open_frame = trades_frame(state, "OPEN")
    market_value = 0.0
    if not open_frame.empty:
        if {"last_price", "quantity"}.issubset(open_frame.columns):
            prices = pd.to_numeric(open_frame["last_price"], errors="coerce").fillna(
                pd.to_numeric(open_frame.get("entry_price"), errors="coerce")
            )
            quantity = pd.to_numeric(open_frame["quantity"], errors="coerce").fillna(0)
            market_value = float((prices * quantity).sum())
        elif "position_value" in open_frame.columns:
            market_value = float(pd.to_numeric(open_frame["position_value"], errors="coerce").fillna(0).sum())
    return {**metrics, "cash": float(state.get("cash", 0) or 0), "market_value": market_value}


def export_trade_history_csv(state: dict[str, Any] | None) -> bytes:
    if not isinstance(state, dict):
        return b""
    frames = []
    for status in ("OPEN", "CLOSED"):
        frame = trades_frame(state, status)
        if not frame.empty:
            frame = frame.copy()
            frame["portfolio_status"] = status
            frames.append(frame)
    if not frames:
        return b""
    return pd.concat(frames, ignore_index=True, sort=False).to_csv(index=False).encode("utf-8")


def build_release_candidate_pdf(
    *,
    version: str,
    portfolio: dict[str, Any],
    run_history: pd.DataFrame,
    recommendations: pd.DataFrame,
    trades: pd.DataFrame,
) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PDF export requires reportlab.") from exc

    out = BytesIO()
    doc = SimpleDocTemplate(out, pagesize=A4, rightMargin=14*mm, leftMargin=14*mm, topMargin=12*mm, bottomMargin=12*mm,
                            title="Catalyst AI Release Candidate Report", author="Catalyst AI")
    styles = getSampleStyleSheet()
    story = [Paragraph("Catalyst AI - Release Candidate Report", styles["Title"]),
             Paragraph(f"Version {version}", styles["Normal"]), Spacer(1, 8)]

    def table(data: list[list[Any]], header: bool = False):
        t = Table([["-" if v is None else str(v) for v in row] for row in data], repeatRows=1 if header else 0)
        commands = [
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0,0), (-1,-1), 7.5), ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("PADDING", (0,0), (-1,-1), 4),
        ]
        if header:
            commands += [("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1e3a8a")),
                         ("TEXTCOLOR", (0,0), (-1,0), colors.white), ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold")]
        t.setStyle(TableStyle(commands))
        return t

    story += [Paragraph("Portfolio & Performance", styles["Heading2"]), table([
        ["Equity", f"GBP {float(portfolio.get('equity',0)):,.2f}"],
        ["Net P/L", f"GBP {float(portfolio.get('net_pnl',0)):,.2f}"],
        ["Return", f"{float(portfolio.get('return_pct',0)):.2f}%"],
        ["Open / Closed", f"{int(portfolio.get('open_trades',0))} / {int(portfolio.get('closed_trades',0))}"],
        ["Win rate", f"{float(portfolio.get('win_rate_pct',0)):.1f}%"],
        ["Expectancy", f"GBP {float(portfolio.get('expectancy',0)):,.2f}"],
        ["Max drawdown", f"{float(portfolio.get('max_drawdown_pct',0)):.2f}%"],
    ]), Spacer(1, 10)]

    story.append(Paragraph("Active Recommendations", styles["Heading2"]))
    if recommendations.empty:
        story.append(Paragraph("No active recommendations.", styles["Normal"]))
    else:
        cols = [c for c in ["ticker","action","score","swing_status","entry_price","target_price","stop_loss","risk_reward","expires_date"] if c in recommendations.columns]
        data = [[c.replace("_"," ").title() for c in cols]] + [[row.get(c, "-") for c in cols] for _, row in recommendations.head(12).iterrows()]
        story.append(table(data, header=True))

    story += [Spacer(1, 10), Paragraph("Recent Routine History", styles["Heading2"])]
    if run_history.empty:
        story.append(Paragraph("No persisted routine history yet.", styles["Normal"]))
    else:
        cols = [c for c in ["date","regime","symbols_scanned","buy_count","qualified_count","proof_verdict"] if c in run_history.columns]
        data = [[c.replace("_"," ").title() for c in cols]] + [[row.get(c, "-") for c in cols] for _, row in run_history.tail(10).iloc[::-1].iterrows()]
        story.append(table(data, header=True))

    story += [Spacer(1, 10), Paragraph("Trade Journal", styles["Heading2"])]
    if trades.empty:
        story.append(Paragraph("No paper trades recorded yet.", styles["Normal"]))
    else:
        cols = [c for c in ["ticker","status","entry_date","exit_date","net_pnl","return_pct","exit_reason"] if c in trades.columns]
        data = [[c.replace("_"," ").title() for c in cols]] + [[row.get(c, "-") for c in cols] for _, row in trades.tail(15).iterrows()]
        story.append(table(data, header=True))

    story += [Spacer(1, 12), Paragraph("Decision support only - not financial advice.", styles["Italic"])]
    doc.build(story)
    return out.getvalue()
