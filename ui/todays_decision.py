from __future__ import annotations

from datetime import datetime
import html

import pandas as pd
import streamlit as st

from data.daily_routine_store import load_latest_routine
from engine.todays_decision import build_todays_decision
from ui.components import empty_state, metric_card, section_header


def _money(value) -> str:
    try:
        if pd.isna(value):
            return "—"
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _load_payload() -> tuple[pd.DataFrame, pd.DataFrame, dict, dict]:
    persisted = load_latest_routine()
    scan = st.session_state.get("scan_results", persisted.get("scan", pd.DataFrame()))
    plans = st.session_state.get("trade_plans", persisted.get("plans", pd.DataFrame()))
    regime = st.session_state.get("market_regime", persisted.get("regime", {}))
    summary = st.session_state.get("daily_routine_summary", persisted.get("summary", {}))
    return (
        scan if isinstance(scan, pd.DataFrame) else pd.DataFrame(),
        plans if isinstance(plans, pd.DataFrame) else pd.DataFrame(),
        regime if isinstance(regime, dict) else {},
        summary if isinstance(summary, dict) else {},
    )


def _navigate(page: str) -> None:
    st.session_state["primary_navigation"] = page


def _go_to_daily_routine() -> None:
    _navigate("Daily Routine")


def render_todays_decision() -> None:
    section_header(
        "Today’s Decision",
        "One clear conclusion from the latest Catalyst scan. Review the evidence, then make your own decision.",
    )

    scan, plans, regime, summary = _load_payload()
    if scan.empty:
        empty_state(
            "No completed routine yet",
            "Run the Daily Routine to create today’s market decision.",
            "🚀",
        )
        st.button("Run Today’s Analysis", type="primary", use_container_width=True, on_click=_go_to_daily_routine)
        return

    decision = build_todays_decision(scan, plans, regime)
    action_icon = {"TRADE": "🟢", "WATCH": "🟡", "NO TRADE": "🔴"}[decision.action]
    finished_at = summary.get("finished_at")
    updated = "Latest saved routine"
    if finished_at:
        try:
            updated = datetime.fromisoformat(str(finished_at).replace("Z", "+00:00")).strftime("Updated %d %b %Y %H:%M")
        except ValueError:
            updated = f"Updated {finished_at}"

    st.markdown(
        f"""
        <div class="decision-hero decision-{decision.tone}">
          <div class="decision-kicker">{html.escape(updated)}</div>
          <div class="decision-action">{action_icon} {html.escape(decision.action)}</div>
          <div class="decision-headline">{html.escape(decision.headline)}</div>
          <div class="decision-guidance">{html.escape(decision.guidance)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Market", decision.market_state, f"Health {decision.market_score}/100"), unsafe_allow_html=True)
    c2.markdown(metric_card("Decision confidence", f"{decision.confidence}%", "Rules-based assessment"), unsafe_allow_html=True)
    c3.markdown(metric_card("BUY candidates", str(decision.buy_count), "Qualified by scanner"), unsafe_allow_html=True)
    c4.markdown(metric_card("WATCH candidates", str(decision.watch_count), f"{decision.scanned_count} scanned"), unsafe_allow_html=True)

    trade = decision.best_opportunity
    st.markdown("### Best Opportunity")
    if trade:
        ticker = html.escape(str(trade.get("ticker", "—")))
        signal = html.escape(str(trade.get("signal", "WATCH")))
        confidence = html.escape(str(trade.get("confidence", "—")))
        st.markdown(
            f'<div class="opportunity-title"><span>{ticker}</span><span>{signal} · Confidence {confidence}</span></div>',
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Score", f"{float(trade.get('score', 0)):.0f}/100")
        c2.metric("Entry", _money(trade.get("entry_price")))
        c3.metric("Target", _money(trade.get("target_price")))
        c4.metric("Stop", _money(trade.get("stop_loss")))
        rr = trade.get("risk_reward")
        if rr is not None and not pd.isna(rr):
            st.caption(f"Planned risk/reward: {float(rr):.1f}:1")
    else:
        empty_state("No leading opportunity", "No BUY or WATCH candidate is available in the latest saved scan.", "🛑")

    st.markdown("### Why Catalyst reached this decision")
    st.markdown("\n".join(f"- {reason}" for reason in decision.reasons))

    c1, c2 = st.columns([2, 1])
    with c1:
        st.button("🚀 Run Today’s Analysis", type="primary", use_container_width=True, on_click=_go_to_daily_routine)
    with c2:
        st.button("Open Dashboard", use_container_width=True, on_click=_navigate, args=("Dashboard",))

    st.caption("Catalyst AI provides market intelligence and decision support only. It does not execute trades or provide financial advice.")
