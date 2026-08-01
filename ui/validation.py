import json
import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels
from engine.proof_validation import build_proof_report
from version import APP_VERSION
from ui.components import empty_state, section_header, status_card


VALIDATION_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "saved_entry_price",
    "entry_price",
    "entry_date",
    "latest_price",
    "return_1d_pct",
    "status_1d",
    "return_5d_pct",
    "status_5d",
    "return_10d_pct",
    "status_10d",
    "return_20d_pct",
    "status_20d",
    "avg_forward_return_pct",
    "validation_status",
]



def _render_proof_validation() -> None:
    st.markdown("### Proof & Performance")
    st.caption("Runs the locked v9.2.1 evidence checks against the most recent backtest. No strategy parameters are changed.")
    result = st.session_state.get("backtest_result")
    if result is None or getattr(result, "trades", pd.DataFrame()).empty:
        status_card("Run a Backtesting test first. Catalyst will then use those completed trades as the locked evidence set.", "info")
        return

    trades = result.trades
    c1, c2, c3 = st.columns(3)
    c1.metric("Evidence Trades", len(trades))
    c2.metric("Backtest Errors", len(getattr(result, "errors", {}) or {}))
    c3.metric("Build", APP_VERSION)

    if st.button("Run Proof Validation", type="primary", use_container_width=True):
        with st.spinner("Testing profitability, consistency, drawdown and stress survival..."):
            report = build_proof_report(
                trades,
                build_version=APP_VERSION,
                configuration=getattr(result, "assumptions", {}) or {},
            )
            st.session_state["proof_validation_report"] = report

    report = st.session_state.get("proof_validation_report")
    if not report:
        return

    verdict = report["verdict"]
    tone = "positive" if verdict == "PASS" else ("info" if verdict == "CONDITIONAL PASS" else "warning")
    status_card(f"Verdict: {verdict} — {report['checks_passed']}/{report['checks_total']} proof checks passed.", tone)

    overall = report["overall"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Return", f"{overall['total_return_pct']}%")
    c2.metric("Profit Factor", overall["profit_factor"])
    c3.metric("Max Drawdown", f"{overall['max_drawdown_pct']}%")
    c4.metric("Avg Trade", f"{overall['average_return_pct']}%")

    checks = pd.DataFrame([
        {"check": key.replace("_", " ").title(), "result": "PASS" if value else "FAIL"}
        for key, value in report["checks"].items()
    ])
    st.dataframe(checks, use_container_width=True, hide_index=True)

    tab1, tab2, tab3, tab4 = st.tabs(["By Year", "Score Bands", "Tickers", "Regimes"])
    with tab1:
        st.dataframe(pd.DataFrame(report["by_year"]), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(pd.DataFrame(report["by_score_band"]), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(pd.DataFrame(report["by_ticker"]), use_container_width=True, hide_index=True, height=360)
    with tab4:
        st.dataframe(pd.DataFrame(report["by_regime"]), use_container_width=True, hide_index=True)

    stress = report["stress"]
    st.markdown("#### Execution Stress Test")
    st.caption("Adds 0.20% extra cost and a 0.15% delayed-entry penalty to every trade.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stress Return", f"{stress['total_return_pct']}%")
    c2.metric("Stress Profit Factor", stress["profit_factor"])
    c3.metric("Stress Drawdown", f"{stress['max_drawdown_pct']}%")

    st.download_button(
        "Download Proof Report (JSON)",
        json.dumps(report, indent=2, default=str).encode("utf-8"),
        file_name=f"catalyst_proof_report_v{APP_VERSION}.json",
        mime="application/json",
        use_container_width=True,
    )


def render_validation() -> None:
    section_header(
        "Validation Centre",
        "Proof testing, performance diagnostics and forward-return validation.",
    )

    _render_proof_validation()
    st.divider()
    st.markdown("### Saved Scan Forward Validation")

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
        "Validation now anchors returns to the saved scan timestamp and marks incomplete windows as PENDING.",
        "positive",
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
        with st.spinner(f"Downloading price data for {len(tickers)} tickers..."):
            # 6mo provides enough history for older saved scans while keeping downloads light.
            market = download_history(tickers, period="6mo")
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
            "Press Run Forward Validation to calculate returns from the selected scan date.",
            "📈",
        )
        return

    st.markdown("### Validation Summary")
    if summary.empty:
        empty_state("No validation summary", "There was not enough data to summarise.", "📊")
    else:
        st.dataframe(summary, use_container_width=True, hide_index=True)

    pending_count = int((validation.get("validation_status", pd.Series(dtype=str)) == "PENDING").sum())
    if pending_count:
        status_card(
            f"{pending_count} rows have no completed forward window yet. That is normal for very recent scans.",
            "info",
        )

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
            "saved_entry_price": st.column_config.NumberColumn("Saved Entry", format="%.2f", width="small"),
            "entry_price": st.column_config.NumberColumn("Market Entry", format="%.2f", width="small"),
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
