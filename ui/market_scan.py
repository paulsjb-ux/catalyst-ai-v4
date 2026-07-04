import pandas as pd
import streamlit as st

from data.history_store import load_previous_scan, save_scan, compare_scans
from data.market_data import download_history
from data.universe import get_default_universe, normalise_tickers
from engine.scanner import run_scan
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


def render_market_scan() -> None:
    section_header("Market Scan", "Live BUY, WATCH and IGNORE candidate analysis with automatic history saving.")

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
            with st.spinner(f"Downloading, analysing and saving {len(tickers)} symbols..."):
                market = download_history(tickers, period=period)
                results = run_scan(market.prices)
                saved = save_scan(results)

                st.session_state["scan_results"] = results
                st.session_state["scan_errors"] = market.errors
                st.session_state["scan_time"] = saved.saved_at if saved else ""
                st.session_state["scan_id"] = saved.scan_id if saved else ""

                if saved:
                    previous = load_previous_scan(saved.scan_id)
                    st.session_state["scan_comparison"] = compare_scans(results, previous)

    frame = st.session_state.get("scan_results", pd.DataFrame())
    errors = st.session_state.get("scan_errors", {})
    comparison = st.session_state.get("scan_comparison", pd.DataFrame())

    if frame is None or frame.empty:
        empty_state(
            "No scan results yet",
            "Press Run Market Scan to download prices, score the universe and save the result.",
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
    c4.metric("Errors", len(errors))

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
        height=520,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "signal": st.column_config.TextColumn("Signal", width="small"),
            "score": st.column_config.NumberColumn("Score", width="small"),
            "close": st.column_config.NumberColumn("Close", format="%.2f", width="small"),
            "change_1d_pct": st.column_config.NumberColumn("1D %", format="%.2f", width="small"),
            "change_20d_pct": st.column_config.NumberColumn("20D %", format="%.2f", width="small"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f", width="small"),
            "volume_ratio": st.column_config.NumberColumn("Vol", format="%.2f", width="small"),
            "trend": st.column_config.TextColumn("Trend", width="medium"),
            "reason": st.column_config.TextColumn("Reason", width="large"),
        },
    )

    st.download_button(
        "Download scan CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="catalyst_scan.csv",
        mime="text/csv",
        use_container_width=True,
    )
