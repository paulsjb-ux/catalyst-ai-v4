import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans
from ui.components import empty_state, metric_card, section_header, status_card


TOP_COLUMNS = ["ticker", "signal", "score", "close", "change_20d_pct", "rsi_14", "trend", "reason"]
PLAN_COLUMNS = ["ticker", "signal", "entry_price", "target_price", "stop_loss", "risk_reward", "position_quality"]


def render_dashboard(version: str, scan_results: pd.DataFrame | None = None) -> None:
    section_header("Command Dashboard", "Live intelligence, saved scan status and target/stop planning.")

    frame = scan_results if scan_results is not None else pd.DataFrame()
    plans = st.session_state.get("trade_plans", pd.DataFrame())
    scans = list_saved_scans()
    buys = int((frame["signal"] == "BUY").sum()) if not frame.empty else 0
    watches = int((frame["signal"] == "WATCH").sum()) if not frame.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Universe", str(len(frame)) if not frame.empty else "Not loaded", "latest session scan"), unsafe_allow_html=True)
    c2.markdown(metric_card("BUY", str(buys), "high-conviction candidates"), unsafe_allow_html=True)
    c3.markdown(metric_card("WATCH", str(watches), "developing candidates"), unsafe_allow_html=True)
    c4.markdown(metric_card("Trade Plans", str(len(plans)) if plans is not None else "0", "targets and stops"), unsafe_allow_html=True)

    st.markdown("### System Status")
    status_card("Sprint 2 Part 2 target/stop engine is installed.", "positive")
    st.caption(f"Version: {version}")

    if frame.empty:
        status_card("Run a market scan to populate live candidates.", "info")
        st.markdown("### Today's Intelligence")
        empty_state("No scan loaded", "Open Market Scan and press Run Market Scan.", "📊")
    else:
        status_card(f"Latest scan contains {len(frame)} successfully analysed symbols.", "positive")
        st.markdown("### Top Candidates")
        top = frame[frame["signal"].isin(["BUY", "WATCH"])].head(10)

        if top.empty:
            empty_state("No qualifying candidates", "The current universe produced no BUY or WATCH signals.", "🛡️")
        else:
            st.dataframe(top[TOP_COLUMNS], use_container_width=True, hide_index=True, height=360)

    if plans is not None and not plans.empty:
        st.markdown("### Best Trade Plans")
        best = plans.sort_values(["position_quality", "risk_reward"], ascending=[True, False]).head(10)
        st.dataframe(
            best[[col for col in PLAN_COLUMNS if col in best.columns]],
            use_container_width=True,
            hide_index=True,
            height=360,
        )

    st.markdown("### Saved Scan Status")
    if scans.empty:
        empty_state("No saved scans yet", "Market Scan will automatically save each completed run.", "💾")
    else:
        st.dataframe(
            scans[["scan_id", "saved_at", "row_count", "buy_count", "watch_count"]].head(8),
            use_container_width=True,
            hide_index=True,
        )
