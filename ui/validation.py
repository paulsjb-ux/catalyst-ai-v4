import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels
from ui.components import empty_state, section_header, status_card


VALIDATION_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "entry_price",
    "latest_price",
    "return_1d_pct",
    "return_5d_pct",
    "return_10d_pct",
    "return_20d_pct",
    "avg_forward_return_pct",
]


def render_validation() -> None:
    section_header(
        "Validation Centre",
        "Forward-return validation for saved Catalyst signals.",
    )

    scans = list_saved_scans()

    if scans.empty:
        empty_state("No validation history yet", "Run Market Scan to create the first saved scan record.", "🧪")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Saved Scans", len(scans))
    c2.metric("Rows Saved", int(scans["row_count"].sum()))
    c3.metric("BUY Signals", int(scans["buy_count"].sum()))
    c4.metric("WATCH Signals", int(scans["watch_count"].sum()))

    status_card(
        "Sprint 2 validation estimates 1D, 5D, 10D and 20D forward returns from saved scan entries.",
        "info",
    )

    st.markdown("### Choose scan to validate")
    selected = st.selectbox("Saved scan", scans["scan_id"].tolist())

    if not selected:
        return

    frame = load_scan(selected)

    if frame.empty:
        st.warning("Selected scan file could not be loaded.")
        return

    signal_filter = st.selectbox("Signals to validate", ["BUY & WATCH", "BUY", "WATCH", "All"], index=0)

    filtered = frame.copy()
    if signal_filter == "BUY & WATCH":
        filtered = filtered[filtered["signal"].isin(["BUY", "WATCH"])]
    elif signal_filter != "All":
        filtered = filtered[filtered["signal"] == signal_filter]

    if filtered.empty:
        empty_state("No signals to validate", "The selected filters returned no rows.", "🧪")
        return

    tickers = filtered["ticker"].dropna().astype(str).str.upper().unique().tolist()

    if st.button("Run Forward Validation", type="primary", use_container_width=True):
        with st.spinner(f"Downloading forward price data for {len(tickers)} tickers..."):
            market = download_history(tickers, period="3mo")
            validation = calculate_forward_returns(filtered, market.prices)
            summary = add_quality_labels(summarise_validation(validation))

            st.session_state["validation_results"] = validation
            st.session_state["validation_summary"] = summary
            st.session_state["validation_errors"] = market.errors
            st.session_state["validated_scan_id"] = selected

    validation = st.session_state.get("validation_results", pd.DataFrame())
    summary = st.session_state.get("validation_summary", pd.DataFrame())
    errors = st.session_state.get("validation_errors", {})

    if errors:
        with st.expander("Validation data errors"):
            st.json(errors)

    if validation.empty:
        empty_state(
            "No forward validation run yet",
            "Press Run Forward Validation to calculate forward returns for the selected scan.",
            "📈",
        )
        return

    st.markdown("### Validation Summary")
    if summary.empty:
        empty_state("No validation summary", "There was not enough data to summarise.", "📊")
    else:
        st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown("### Signal-Level Forward Returns")
    visible_cols = [col for col in VALIDATION_COLUMNS if col in validation.columns]
    st.dataframe(
        validation[visible_cols],
        use_container_width=True,
        hide_index=True,
        height=520,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", width="small"),
            "signal": st.column_config.TextColumn("Signal", width="small"),
            "score": st.column_config.NumberColumn("Score", width="small"),
            "entry_price": st.column_config.NumberColumn("Entry", format="%.2f", width="small"),
            "latest_price": st.column_config.NumberColumn("Latest", format="%.2f", width="small"),
            "return_1d_pct": st.column_config.NumberColumn("1D %", format="%.2f", width="small"),
            "return_5d_pct": st.column_config.NumberColumn("5D %", format="%.2f", width="small"),
            "return_10d_pct": st.column_config.NumberColumn("10D %", format="%.2f", width="small"),
            "return_20d_pct": st.column_config.NumberColumn("20D %", format="%.2f", width="small"),
            "avg_forward_return_pct": st.column_config.NumberColumn("Avg %", format="%.2f", width="small"),
        },
    )

    st.download_button(
        "Download validation CSV",
        validation.to_csv(index=False).encode("utf-8"),
        file_name=f"catalyst_validation_{selected}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if not summary.empty:
        st.download_button(
            "Download validation summary CSV",
            summary.to_csv(index=False).encode("utf-8"),
            file_name=f"catalyst_validation_summary_{selected}.csv",
            mime="text/csv",
            use_container_width=True,
        )
