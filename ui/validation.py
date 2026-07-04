import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from ui.components import empty_state, section_header, status_card


def render_validation() -> None:
    section_header(
        "Validation Centre",
        "Saved-scan evidence and forward-test tracking foundation.",
    )

    scans = list_saved_scans()

    if scans.empty:
        empty_state("No validation history yet", "Run Market Scan to create the first saved scan record.", "🧪")
        return

    total_rows = int(scans["row_count"].sum())
    total_buys = int(scans["buy_count"].sum())
    total_watches = int(scans["watch_count"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Saved Scans", len(scans))
    c2.metric("Analysed Rows", total_rows)
    c3.metric("BUY Signals", total_buys)
    c4.metric("WATCH Signals", total_watches)

    status_card("Part 4 tracks scan evidence. Return validation against future prices arrives in later builds.", "info")

    st.markdown("### Scan History")
    st.dataframe(
        scans[["scan_id", "saved_at", "row_count", "buy_count", "watch_count"]],
        use_container_width=True,
        hide_index=True,
    )

    selected = st.selectbox("Inspect saved scan", scans["scan_id"].tolist())

    if selected:
        frame = load_scan(selected)
        if frame.empty:
            st.warning("Selected scan file could not be loaded.")
        else:
            st.markdown("### Selected Scan")
            st.dataframe(frame, use_container_width=True, hide_index=True)
            st.download_button(
                "Download selected scan CSV",
                frame.to_csv(index=False).encode("utf-8"),
                file_name=f"catalyst_scan_{selected}.csv",
                mime="text/csv",
                use_container_width=True,
            )
