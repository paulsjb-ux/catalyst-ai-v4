import pandas as pd
import streamlit as st

from data.history_store import load_previous_scan, save_scan, compare_scans
from data.market_data import download_history
from data.universe import get_default_universe, normalise_tickers
from engine.scanner import run_scan
from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates
from ui.components import empty_state, section_header, status_card


DISPLAY_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "close",
    "change_1d_pct",
    "change_20d_pct",
    "rsi_14",
    "volume_ratio",
    "trend",
    "reason",
]


PLAN_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "entry_price",
    "target_price",
    "stop_loss",
    "risk_pct",
    "reward_pct",
    "risk_reward",
    "position_quality",
    "plan_reason",
]


def render_market_scan() -> None:
    section_header(
        "Market Scan",
        "Live BUY, WATCH and IGNORE analysis with trade-plan targets and stops.",
    )

    default_text = ",".join(get_default_universe(30))
    tickers_raw = st.text_area(
        "Tickers",
        value=st.session_state.get("ticker_input", default_text),
        height=90,
        help="Comma-separated US tickers. Start with 20–30 while testing.",
    )
    st.session_state["ticker_input"] = tickers_raw

    c1, c2, c3 = st.columns(3)
    with c1:
        period = st.selectbox("History", ["6mo", "1y", "2y"], index=1)
    with c2:
        minimum_score = st.slider("Minimum displayed score", 0, 100, 50)
    with c3:
        signal_filter = st.selectbox("Signal", ["BUY & WATCH", "All", "BUY", "WATCH", "IGNORE"])

    if st.button("Run Market Scan", type="primary", use_container_width=True):
        tickers = normalise_tickers(tickers_raw)
        if not tickers:
            st.error("Enter at least one ticker.")
        else:
            with st.spinner(f"Downloading, analysing and planning {len(tickers)} symbols..."):
                market = download_history(tickers, period=period)
                results = run_scan(market.prices)
                plan_candidates = filter_trade_plan_candidates(results)
                plans = build_trade_plans(plan_candidates, market.prices)

                saved = save_scan(results)

                st.session_state["scan_results"] = results
                st.session_state["trade_plans"] = plans
                st.session_state["scan_errors"] = market.errors
                st.session_state["scan_time"] = saved.saved_at if saved else ""
                st.session_state["scan_id"] = saved.scan_id if saved else ""

                if saved:
                    previous = load_previous_scan(saved.scan_id)
                    st.session_state["scan_comparison"] = compare_scans(results, previous)

    frame = st.session_state.get("scan_results", pd.DataFrame())
    plans = st.session_state.get("trade_plans", pd.DataFrame())
    errors = st.session_state.get("scan_errors", {})
    comparison = st.session_state.get("scan_comparison", pd.DataFrame())

    if frame is None or frame.empty:
        empty_state(
            "No scan results yet",
            "Press Run Market Scan to download prices, score the universe and build target/stop plans.",
            "🔎",
        )
        return

    filtered = frame[frame["score"] >= minimum_score].copy()

    if signal_filter == "BUY & WATCH":
        filtered = filtered[filtered["signal"].isin(["BUY", "WATCH"])]
    elif signal_filter != "All":
        filtered = filtered[filtered["signal"] == signal_filter]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", len(frame))
    c2.metric("BUY", int((frame["signal"] == "BUY").sum()))
    c3.metric("WATCH", int((frame["signal"] == "WATCH").sum()))
    c4.metric("Plans", len(plans) if plans is not None else 0)

    scan_id = st.session_state.get("scan_id", "")
    if scan_id:
        status_card(f"Scan saved locally as {scan_id}.", "positive")

    if errors:
        status_card(f"{len(errors)} symbols could not be loaded. The rest of the scan completed.", "warning")
        with st.expander("View data errors"):
            st.json(errors)

    if not comparison.empty:
        with st.expander("Compare with previous scan"):
            comparison_cols = [
                col for col in [
                    "ticker",
                    "signal_now",
                    "signal_prev",
                    "signal_change",
                    "score_now",
                    "score_prev",
                    "score_change",
                    "close_now",
                    "close_prev",
                ] if col in comparison.columns
            ]
            st.dataframe(comparison[comparison_cols], use_container_width=True, hide_index=True)

    if filtered.empty:
        empty_state("No matches", "Adjust the score or signal filters.", "🛡️")
        return

    st.markdown("### Candidate Results")
    st.dataframe(
        filtered[DISPLAY_COLUMNS],
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    if plans is not None and not plans.empty:
        st.markdown("### Target & Stop Plans")
        visible_plans = plans.copy()
        if signal_filter == "BUY & WATCH":
            visible_plans = visible_plans[visible_plans["signal"].isin(["BUY", "WATCH"])]
        elif signal_filter != "All":
            visible_plans = visible_plans[visible_plans["signal"] == signal_filter]

        st.dataframe(
            visible_plans[[col for col in PLAN_COLUMNS if col in visible_plans.columns]],
            use_container_width=True,
            hide_index=True,
            height=420,
            column_config={
                "ticker": st.column_config.TextColumn("Ticker", width="small"),
                "signal": st.column_config.TextColumn("Signal", width="small"),
                "score": st.column_config.NumberColumn("Score", width="small"),
                "entry_price": st.column_config.NumberColumn("Entry", format="%.2f", width="small"),
                "target_price": st.column_config.NumberColumn("Target", format="%.2f", width="small"),
                "stop_loss": st.column_config.NumberColumn("Stop", format="%.2f", width="small"),
                "risk_pct": st.column_config.NumberColumn("Risk %", format="%.2f", width="small"),
                "reward_pct": st.column_config.NumberColumn("Reward %", format="%.2f", width="small"),
                "risk_reward": st.column_config.NumberColumn("R/R", format="%.2f", width="small"),
                "position_quality": st.column_config.TextColumn("Quality", width="small"),
                "plan_reason": st.column_config.TextColumn("Reason", width="large"),
            },
        )

        st.download_button(
            "Download trade plans CSV",
            visible_plans.to_csv(index=False).encode("utf-8"),
            file_name="catalyst_trade_plans.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.download_button(
        "Download scan CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="catalyst_scan.csv",
        mime="text/csv",
        use_container_width=True,
    )
