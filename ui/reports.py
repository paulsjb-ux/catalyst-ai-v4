import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from engine.market_regime import REGIME_TICKERS, build_market_regime
from engine.repeat_winners import build_repeat_winners
from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates
from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels
from ui.components import empty_state, section_header, status_card


def render_reports() -> None:
    section_header("Reports", "Saved scan summaries, exports, repeat winners, validation, regime and trade plans.")

    scans = list_saved_scans()
    if scans.empty:
        empty_state("Reports are waiting for data", "Run Market Scan to create local scan history.", "📄")
        return

    status_card("Local reporting is active. Reports are generated from saved scan history.", "positive")

    st.markdown("### Saved Scan Index")
    st.dataframe(scans, use_container_width=True, hide_index=True)
    st.download_button("Download scan index CSV", scans.to_csv(index=False).encode("utf-8"), file_name="catalyst_scan_index.csv", mime="text/csv", use_container_width=True)

    frames = []
    for _, row in scans.head(20).iterrows():
        frame = load_scan(str(row["scan_id"]))
        if not frame.empty:
            frames.append(frame)

    st.markdown("### Repeat Winner Report")
    winners = build_repeat_winners(frames)
    if winners.empty:
        empty_state("No repeat winners yet", "Run more scans to build repeat evidence.", "🏆")
    else:
        st.dataframe(winners, use_container_width=True, hide_index=True)
        st.download_button("Download repeat winner report CSV", winners.to_csv(index=False).encode("utf-8"), file_name="catalyst_repeat_winner_report.csv", mime="text/csv", use_container_width=True)

    st.markdown("### Current Market Regime Report")
    if st.button("Refresh market regime", use_container_width=True):
        with st.spinner("Downloading SPY/QQQ market data..."):
            market = download_history(REGIME_TICKERS, period="1y")
            st.session_state["report_market_regime"] = build_market_regime(market.prices)

    regime = st.session_state.get("report_market_regime")
    if regime:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regime", regime.get("regime", "UNKNOWN"))
        c2.metric("Market Score", regime.get("market_score", 0))
        c3.metric("Adjustment", regime.get("regime_adjustment", 0))
        c4.metric("Risk Label", regime.get("risk_label", "UNKNOWN"))
        st.dataframe(pd.DataFrame(regime.get("indices", [])), use_container_width=True, hide_index=True)

    latest_scan_id = str(scans.iloc[0]["scan_id"])
    latest = load_scan(latest_scan_id)
    if latest.empty:
        empty_state("Latest scan unavailable", "The latest saved scan could not be loaded.", "📈")
        return

    st.markdown("### Latest Scan Trade Plan Report")
    candidate_rows = filter_trade_plan_candidates(latest)
    if candidate_rows.empty:
        empty_state("No candidates in latest scan", "The latest scan has no BUY or WATCH rows.", "📈")
    elif st.button("Build latest trade plan report", type="primary", use_container_width=True):
        tickers = candidate_rows["ticker"].dropna().astype(str).str.upper().unique().tolist()
        with st.spinner(f"Building trade plans for {len(tickers)} tickers..."):
            market = download_history(tickers, period="6mo")
            st.session_state["report_trade_plans"] = build_trade_plans(candidate_rows, market.prices)

    plans = st.session_state.get("report_trade_plans", pd.DataFrame())
    if not plans.empty:
        st.dataframe(plans, use_container_width=True, hide_index=True)
        st.download_button("Download latest trade plans CSV", plans.to_csv(index=False).encode("utf-8"), file_name=f"catalyst_trade_plans_{latest_scan_id}.csv", mime="text/csv", use_container_width=True)

    st.markdown("### Quick Validation Report")
    candidate_rows = latest[latest["signal"].isin(["BUY", "WATCH"])].copy()
    if candidate_rows.empty:
        empty_state("No candidates in latest scan", "The latest scan has no BUY or WATCH rows.", "📈")
        return

    if st.button("Validate latest scan", use_container_width=True):
        tickers = candidate_rows["ticker"].dropna().astype(str).str.upper().unique().tolist()
        with st.spinner(f"Validating latest scan for {len(tickers)} tickers..."):
            market = download_history(tickers, period="6mo")
            validation = calculate_forward_returns(candidate_rows, market.prices)
            st.session_state["report_validation"] = validation
            st.session_state["report_validation_summary"] = add_quality_labels(summarise_validation(validation))

    summary = st.session_state.get("report_validation_summary", pd.DataFrame())
    validation = st.session_state.get("report_validation", pd.DataFrame())
    if not summary.empty:
        st.markdown("#### Latest Scan Validation Summary")
        st.dataframe(summary, use_container_width=True, hide_index=True)
    if not validation.empty:
        st.download_button("Download latest validation CSV", validation.to_csv(index=False).encode("utf-8"), file_name=f"catalyst_latest_validation_{latest_scan_id}.csv", mime="text/csv", use_container_width=True)
