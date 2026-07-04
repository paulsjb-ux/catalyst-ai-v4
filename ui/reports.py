import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from engine.repeat_winners import build_repeat_winners
from ui.components import empty_state, section_header, status_card


def render_reports() -> None:
    section_header("Reports", "Saved scan summaries, exports and repeat-winner reporting.")

    scans = list_saved_scans()

    if scans.empty:
        empty_state("Reports are waiting for data", "Run Market Scan to create local scan history.", "📄")
        return

    status_card("Local reporting is active. Reports are generated from saved scan history.", "positive")

    st.markdown("### Saved Scan Index")
    st.dataframe(scans, use_container_width=True, hide_index=True)

    scan_csv = scans.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download scan index CSV",
        scan_csv,
        file_name="catalyst_scan_index.csv",
        mime="text/csv",
        use_container_width=True,
    )

    frames = []
    for _, row in scans.head(20).iterrows():
        frame = load_scan(str(row["scan_id"]))
        if not frame.empty:
            frames.append(frame)

    winners = build_repeat_winners(frames)

    st.markdown("### Repeat Winner Report")
    if winners.empty:
        empty_state("No repeat winners yet", "Run more scans to build repeat evidence.", "🏆")
    else:
        st.dataframe(winners, use_container_width=True, hide_index=True)
        st.download_button(
            "Download repeat winner report CSV",
            winners.to_csv(index=False).encode("utf-8"),
            file_name="catalyst_repeat_winner_report.csv",
            mime="text/csv",
            use_container_width=True,
        )
