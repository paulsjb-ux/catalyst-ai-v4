from __future__ import annotations

import pandas as pd
import streamlit as st

from data.daily_routine_store import load_latest_routine
from engine.executive_dashboard import ranked_opportunities
from engine.pdf_report import build_trading_desk_pdf
from ui.components import section_header, status_card


def clear_runtime_caches() -> None:
    st.cache_data.clear()
    st.cache_resource.clear()
    for key in [
        "scan_results", "trade_plans", "market_regime", "report_market_regime",
        "report_trade_plans", "report_validation", "report_validation_summary",
    ]:
        st.session_state.pop(key, None)


def render_professional_tools(version: str) -> None:
    section_header("Professional Tools", "One-click refresh, PDF export and release controls.")
    c1, c2 = st.columns(2)
    if c1.button("Refresh application data", type="primary", width="stretch"):
        clear_runtime_caches()
        status_card("Application caches cleared. Reloading fresh data.", "positive")
        st.rerun()

    payload = load_latest_routine()
    frame = payload.get("scan", pd.DataFrame())
    plans = payload.get("plans", pd.DataFrame())
    regime = payload.get("regime", {})
    summary = payload.get("summary", {})
    frame = frame if isinstance(frame, pd.DataFrame) else pd.DataFrame()
    plans = plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    opportunities = ranked_opportunities(frame, plans)

    try:
        pdf = build_trading_desk_pdf(
            version=version,
            summary=summary if isinstance(summary, dict) else {},
            regime=regime if isinstance(regime, dict) else {},
            opportunities=opportunities,
        )
        c2.download_button(
            "Download trading desk PDF",
            data=pdf,
            file_name="catalyst_ai_trading_desk.pdf",
            mime="application/pdf",
            width="stretch",
        )
    except RuntimeError as exc:
        c2.warning(str(exc))
