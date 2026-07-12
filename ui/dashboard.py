import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans
from data.watchlist_store import load_watchlist
from engine.portfolio_monitor import portfolio_summary
from ui.components import empty_state, metric_card, section_header, status_card

TOP_COLUMNS = ["ticker", "signal", "score", "base_score", "market_adjustment", "close", "change_20d_pct", "rsi_14", "trend", "reason"]
PLAN_COLUMNS = ["ticker", "signal", "entry_price", "target_price", "stop_loss", "risk_reward", "position_quality"]


def render_dashboard(version: str, scan_results: pd.DataFrame | None = None) -> None:
    section_header("Command Dashboard", "Live intelligence, market regime, portfolio status and smarter scoring.")

    frame = scan_results if scan_results is not None else pd.DataFrame()
    plans = st.session_state.get("trade_plans", pd.DataFrame())
    regime = st.session_state.get("market_regime")
    monitor = st.session_state.get("portfolio_monitor", pd.DataFrame())
    watchlist = load_watchlist()
    scans = list_saved_scans()

    buys = int((frame["signal"] == "BUY").sum()) if not frame.empty else 0
    watches = int((frame["signal"] == "WATCH").sum()) if not frame.empty else 0
    portfolio = portfolio_summary(monitor)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Universe", str(len(frame)) if not frame.empty else "Not loaded", "latest session scan"), unsafe_allow_html=True)
    c2.markdown(metric_card("BUY", str(buys), "high-conviction candidates"), unsafe_allow_html=True)
    c3.markdown(metric_card("WATCH", str(watches), "developing candidates"), unsafe_allow_html=True)
    c4.markdown(metric_card("Tracked", str(len(watchlist)), "watchlist and holdings"), unsafe_allow_html=True)

    st.markdown("### System Status")
    status_card("Sprint 2 Part 5 watchlist and portfolio monitor is installed.", "positive")
    st.caption(f"Version: {version}")

    st.markdown("### Portfolio Snapshot")
    if monitor is None or monitor.empty:
        empty_state("Portfolio not refreshed", "Open Watchlist and press Refresh live monitor.", "💼")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Positions", portfolio["positions"])
        c2.metric("Market Value", f"${portfolio['market_value']:,.2f}")
        c3.metric("Unrealised P&L", f"${portfolio['unrealised_pnl']:,.2f}", f"{portfolio['unrealised_pnl_pct']:.2f}%")
        c4.metric("Alerts", portfolio["alerts"])

    st.markdown("### Market Regime")
    if regime:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regime", regime.get("regime", "UNKNOWN"))
        c2.metric("Market Score", regime.get("market_score", 0))
        c3.metric("Adjustment", regime.get("regime_adjustment", 0))
        c4.metric("Risk Label", regime.get("risk_label", "UNKNOWN"))
        status_card(regime.get("reason", "No market regime reason available."), "info")
    else:
        empty_state("No market regime yet", "Run Market Scan with regime adjustment enabled.", "🌍")

    if frame.empty:
        empty_state("No scan loaded", "Open Market Scan and press Run Market Scan.", "📊")
    else:
        st.markdown("### Top Candidates")
        top = frame[frame["signal"].isin(["BUY", "WATCH"])].head(10)
        if top.empty:
            empty_state("No qualifying candidates", "The current universe produced no BUY or WATCH signals.", "🛡️")
        else:
            st.dataframe(top[[c for c in TOP_COLUMNS if c in top.columns]], use_container_width=True, hide_index=True, height=360)

    if plans is not None and not plans.empty:
        st.markdown("### Best Trade Plans")
        best = plans.sort_values(["position_quality", "risk_reward"], ascending=[True, False]).head(10)
        st.dataframe(best[[c for c in PLAN_COLUMNS if c in best.columns]], use_container_width=True, hide_index=True, height=360)

    st.markdown("### Saved Scan Status")
    if scans.empty:
        empty_state("No saved scans yet", "Market Scan will automatically save each completed run.", "💾")
    else:
        st.dataframe(scans[["scan_id", "saved_at", "row_count", "buy_count", "watch_count"]].head(8), use_container_width=True, hide_index=True)
