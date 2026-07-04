import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from engine.repeat_winners import build_repeat_winners
from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels
from ui.components import empty_state, section_header, status_card


def render_reports() -> None:
    section_header("Reports", "Saved scan summaries, exports, repeat winners and validation reporting.")

    scans = list_saved_scans()

    if scans.empty:
        empty_state("Reports are waiting for data", "Run Market Scan to create local scan history.", "📄")
        return

    status_card("Local reporting is active. Reports are generated from saved scan history.", "positive")

    st.markdown("### Saved Scan Index")
    st.dataframe(scans, use_container_width=True, hide_index=True)

    st.download_button(
        "Download scan index CSV",
        scans.to_csv(index=False).encode("utf-8"),
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

    st.markdown("### Quick Validation Report")
    latest_scan_id = str(scans.iloc[0]["scan_id"])
    latest = load_scan(latest_scan_id)

    if latest.empty:
        empty_state("Latest scan unavailable", "The latest saved scan could not be loaded.", "📈")
        return

    candidate_rows = latest[latest["signal"].isin(["BUY", "WATCH"])].copy()

    if candidate_rows.empty:
        empty_state("No candidates in latest scan", "The latest scan has no BUY or WATCH rows.", "📈")
        return

    if st.button("Validate latest scan", type="primary", use_container_width=True):
        tickers = candidate_rows["ticker"].dropna().astype(str).str.upper().unique().tolist()
        with st.spinner(f"Validating latest scan for {len(tickers)} tickers..."):
            market = download_history(tickers, period="6mo")
            validation = calculate_forward_returns(candidate_rows, market.prices)
            summary = add_quality_labels(summarise_validation(validation))
            st.session_state["report_validation"] = validation
            st.session_state["report_validation_summary"] = summary

    validation = st.session_state.get("report_validation", pd.DataFrame())
    summary = st.session_state.get("report_validation_summary", pd.DataFrame())

    if not summary.empty:
        st.markdown("#### Latest Scan Validation Summary")
        st.dataframe(summary, use_container_width=True, hide_index=True)

    if not validation.empty:
        pending = int((validation.get("validation_status", pd.Series(dtype=str)) == "PENDING").sum())
        if pending:
            status_card(
                f"{pending} rows are pending because future validation windows have not completed yet.",
                "info",
            )

        st.download_button(
            "Download latest validation CSV",
            validation.to_csv(index=False).encode("utf-8"),
            file_name=f"catalyst_latest_validation_{latest_scan_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )
