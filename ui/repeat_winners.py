import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from engine.repeat_winners import build_repeat_winners
from ui.components import empty_state, section_header, status_card


def render_repeat_winners() -> None:
    section_header(
        "Repeat Winners",
        "Stocks repeatedly appearing as BUY or WATCH across saved scans.",
    )

    scans = list_saved_scans()

    if scans.empty:
        empty_state("No scan history yet", "Run Market Scan several times to build repeat-winner evidence.", "🏆")
        return

    lookback = st.slider("Saved scans to analyse", 2, min(30, max(2, len(scans))), min(10, max(2, len(scans))))

    frames = []
    for _, row in scans.head(lookback).iterrows():
        frame = load_scan(str(row["scan_id"]))
        if not frame.empty:
            frames.append(frame)

    winners = build_repeat_winners(frames)

    if winners.empty:
        empty_state("No repeat winners yet", "No symbols have repeated as BUY/WATCH across the selected scans.", "🛡️")
        return

    priority_count = int((winners["status"] == "PRIORITY").sum())
    proven_count = int((winners["status"] == "PROVEN").sum())
    emerging_count = int((winners["status"] == "EMERGING").sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analysed Scans", lookback)
    c2.metric("Priority", priority_count)
    c3.metric("Proven", proven_count)
    c4.metric("Emerging", emerging_count)

    status_card("Repeat winners are based on locally saved scan history.", "info")

    st.dataframe(
        winners,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "appearances": st.column_config.NumberColumn("Appearances", width="small"),
            "buy_count": st.column_config.NumberColumn("BUY Count", width="small"),
            "watch_count": st.column_config.NumberColumn("WATCH Count", width="small"),
            "avg_score": st.column_config.NumberColumn("Avg Score", format="%.1f", width="small"),
            "latest_signal": st.column_config.TextColumn("Latest Signal", width="small"),
            "latest_close": st.column_config.NumberColumn("Latest Close", format="%.2f", width="small"),
            "status": st.column_config.TextColumn("Status", width="medium"),
        },
    )

    st.download_button(
        "Download repeat winners CSV",
        winners.to_csv(index=False).encode("utf-8"),
        file_name="catalyst_repeat_winners.csv",
        mime="text/csv",
        use_container_width=True,
    )
