import pandas as pd
import streamlit as st
from ui.components import empty_state, metric_card, section_header, status_card

TOP_COLUMNS = ["ticker","signal","score","close","change_20d_pct","rsi_14","trend","reason"]

def render_dashboard(version: str, scan_results: pd.DataFrame | None = None) -> None:
    section_header("Command Dashboard", "Live market intelligence and operating status.")
    frame = scan_results if scan_results is not None else pd.DataFrame()
    buys = int((frame["signal"] == "BUY").sum()) if not frame.empty else 0
    watches = int((frame["signal"] == "WATCH").sum()) if not frame.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Universe", str(len(frame)) if not frame.empty else "Not loaded", "successfully scanned"), unsafe_allow_html=True)
    c2.markdown(metric_card("BUY", str(buys), "high-conviction candidates"), unsafe_allow_html=True)
    c3.markdown(metric_card("WATCH", str(watches), "developing candidates"), unsafe_allow_html=True)
    c4.markdown(metric_card("Version", version, "Sprint 1 Part 3"), unsafe_allow_html=True)

    st.markdown("### System Status")
    status_card("UI and trading engine packages loaded.", "positive")

    if frame.empty:
        status_card("Run a market scan to populate live candidates.", "info")
        st.markdown("### Today's Intelligence")
        empty_state("No scan loaded", "Open Market Scan and press Run Market Scan.", "📊")
        return

    status_card(f"Latest scan contains {len(frame)} successfully analysed symbols.", "positive")
    st.markdown("### Top Candidates")
    top = frame[frame["signal"].isin(["BUY", "WATCH"])].head(10)
    if top.empty:
        empty_state("No qualifying candidates", "The current universe produced no BUY or WATCH signals.", "🛡️")
        return

    st.dataframe(
        top[TOP_COLUMNS],
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "signal": st.column_config.TextColumn("Signal", width="small"),
            "score": st.column_config.NumberColumn("Score", width="small"),
            "close": st.column_config.NumberColumn("Close", format="%.2f", width="small"),
            "change_20d_pct": st.column_config.NumberColumn("20D %", format="%.2f", width="small"),
            "rsi_14": st.column_config.NumberColumn("RSI", format="%.1f", width="small"),
            "trend": st.column_config.TextColumn("Trend", width="medium"),
            "reason": st.column_config.TextColumn("Reason", width="large"),
        },
    )
