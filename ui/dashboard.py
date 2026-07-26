from __future__ import annotations

import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_latest_scan
from data.daily_routine_store import load_latest_routine
from data.watchlist_store import load_watchlist
from engine.executive_dashboard import best_trade, market_health, ranked_opportunities, vix_snapshot
from engine.portfolio_monitor import portfolio_summary
from ui.components import empty_state, metric_card, section_header, status_card


def _money(value) -> str:
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def _index_detail(regime: dict, ticker: str) -> dict:
    for item in regime.get("indices", []) if isinstance(regime, dict) else []:
        if item.get("ticker") == ticker:
            return item
    return {}


def render_dashboard(version: str, scan_results: pd.DataFrame | None = None) -> None:
    section_header("Executive Dashboard", "Your daily trading desk: market health, risk posture and the strongest opportunities in one view.")

    persisted = load_latest_routine()

    frame = scan_results if isinstance(scan_results, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        stored_scan = persisted.get("scan", pd.DataFrame())
        frame = stored_scan if isinstance(stored_scan, pd.DataFrame) else pd.DataFrame()
    if frame.empty:
        frame = load_latest_scan()

    plans = st.session_state.get("trade_plans", pd.DataFrame())
    plans = plans if isinstance(plans, pd.DataFrame) else pd.DataFrame()
    if plans.empty:
        stored_plans = persisted.get("plans", pd.DataFrame())
        plans = stored_plans if isinstance(stored_plans, pd.DataFrame) else pd.DataFrame()

    regime = st.session_state.get("market_regime", {})
    regime = regime if isinstance(regime, dict) else {}
    if not regime:
        stored_regime = persisted.get("regime", {})
        regime = stored_regime if isinstance(stored_regime, dict) else {}

    # Restore the payload into this browser session so all pages share the same run.
    if not frame.empty:
        st.session_state["scan_results"] = frame
    if not plans.empty:
        st.session_state["trade_plans"] = plans
    if regime:
        st.session_state["market_regime"] = regime
    monitor = st.session_state.get("portfolio_monitor", pd.DataFrame())
    watchlist = load_watchlist()
    scans = list_saved_scans()

    health = market_health(regime, frame)
    vix = vix_snapshot(regime)
    opportunities = ranked_opportunities(frame, plans)
    trade = best_trade(opportunities)
    spy = _index_detail(regime, "SPY")
    qqq = _index_detail(regime, "QQQ")

    st.markdown("### Market Health")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Health Score", f"{health['score']}/100", health["label"]), unsafe_allow_html=True)
    c2.markdown(metric_card("Risk Posture", health["risk_state"], regime.get("risk_label", "Unknown")), unsafe_allow_html=True)
    c3.markdown(metric_card("Breadth", f"{health['breadth']:.1f}%", f"{health['above_50_pct']:.1f}% above 50-day MA"), unsafe_allow_html=True)
    vix_value = f"{vix['level']:.2f}" if vix.get("level") is not None else "—"
    c4.markdown(metric_card("VIX", vix_value, vix["label"]), unsafe_allow_html=True)
    status_card(regime.get("reason", "Run the Daily Routine to calculate live market health."), health["tone"])

    st.markdown("### SPY & QQQ Trend")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(metric_card("SPY", spy.get("trend", "Not loaded"), f"Score {spy.get('score', 0)} · 20D {spy.get('change_20d_pct', 0):.1f}%" if spy else "Run Daily Routine"), unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("QQQ", qqq.get("trend", "Not loaded"), f"Score {qqq.get('score', 0)} · 20D {qqq.get('change_20d_pct', 0):.1f}%" if qqq else "Run Daily Routine"), unsafe_allow_html=True)

    st.markdown("### Best Trade of the Day")
    if not trade:
        message = (
            "No saved BUY or WATCH opportunities are available. Run the Daily Routine to refresh the trading desk."
            if frame.empty
            else "Catalyst found no BUY or WATCH opportunity strong enough to rank. No trade is a valid decision."
        )
        empty_state("No official trade today", message, "🛡️")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(metric_card("Ticker", str(trade.get("ticker", "—")), str(trade.get("signal", "WATCH"))), unsafe_allow_html=True)
        c2.markdown(metric_card("Confidence", str(trade.get("confidence", "D")), f"Score {trade.get('score', 0)}"), unsafe_allow_html=True)
        c3.markdown(metric_card("Entry", _money(trade.get("entry_price")), f"Target {_money(trade.get('target_price'))}"), unsafe_allow_html=True)
        rr = trade.get("risk_reward")
        c4.markdown(metric_card("Risk / Reward", f"{float(rr):.2f}" if pd.notna(rr) else "—", f"Stop {_money(trade.get('stop_loss'))}"), unsafe_allow_html=True)

    st.markdown("### Top Opportunities")
    if opportunities.empty:
        empty_state("No ranked opportunities", "Run the Daily Routine. In defensive markets the table may correctly remain empty.", "📊")
    else:
        st.dataframe(opportunities, use_container_width=True, hide_index=True, height=330)

    st.markdown("### Portfolio & System")
    portfolio = portfolio_summary(monitor)
    buys = int((frame.get("signal", pd.Series(dtype=str)) == "BUY").sum()) if not frame.empty else 0
    watches = int((frame.get("signal", pd.Series(dtype=str)) == "WATCH").sum()) if not frame.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("BUY", buys)
    c2.metric("WATCH", watches)
    c3.metric("Open Positions", portfolio.get("positions", 0))
    c4.metric("Tracked", len(watchlist))

    with st.expander("Executive detail"):
        st.caption(f"Version: {version}")
        st.write(f"Bullish or recovering trends: {health['bullish_trend_pct']:.1f}%")
        if monitor is not None and not monitor.empty:
            st.write(f"Portfolio market value: {_money(portfolio.get('market_value'))}")
            st.write(f"Unrealised P&L: {_money(portfolio.get('unrealised_pnl'))}")
        if scans is not None and not scans.empty:
            st.dataframe(scans[[c for c in ["scan_id", "saved_at", "row_count", "buy_count", "watch_count"] if c in scans.columns]].head(5), use_container_width=True, hide_index=True)
