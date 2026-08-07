import json
import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from engine.validation import calculate_forward_returns, summarise_validation, add_quality_labels
from engine.auto_validation import (
    load_tracker, reset_tracker, tracker_summary, persistence_status,
    merge_tracker_evidence, recover_validation_days,
)
from engine.proof_validation import build_proof_report
from engine.research_lab import (
    evaluate_experiment, experiment_comparison_frame, list_experiments,
    load_locked_benchmark, lock_benchmark, save_experiment,
)
from engine.validation_report import (
    build_validation_pdf,
    list_validation_reports,
    load_json_report,
    save_validation_report,
    summary_frame,
)
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



def _validation_trades() -> tuple[pd.DataFrame, dict, str]:
    """Use the current backtest when available, otherwise accept an exported trade CSV."""
    result = st.session_state.get("backtest_result")
    if result is not None:
        trades = getattr(result, "trades", pd.DataFrame())
        if isinstance(trades, pd.DataFrame) and not trades.empty:
            return trades.copy(), getattr(result, "assumptions", {}) or {}, "Current backtest"

    upload = st.file_uploader(
        "Or upload completed backtest trades CSV",
        type=["csv"],
        key="validation_trade_upload",
        help="Use the CSV exported from Historical Backtesting when the app has been restarted.",
    )
    if upload is not None:
        try:
            trades = pd.read_csv(upload)
        except Exception as exc:
            st.error(f"The trade CSV could not be read: {exc}")
            return pd.DataFrame(), {}, "Upload error"
        if trades.empty:
            st.warning("The uploaded trade CSV contains no rows.")
            return pd.DataFrame(), {}, "Empty upload"
        return trades, {"source": "uploaded_csv", "filename": upload.name}, f"Uploaded CSV: {upload.name}"

    return pd.DataFrame(), {}, "No evidence loaded"


def _baseline_report() -> dict | None:
    # v9.2.1 is retained as the locked benchmark copied into each clean release.
    return load_json_report("storage/validation/latest_proof_report.json")


def _render_auto_validation() -> None:
    tracker = load_tracker()
    summary = tracker_summary(tracker)
    storage = tracker.get("storage") or persistence_status()
    st.markdown("### 30-Day Automatic Paper Validation")
    st.caption("Each successful Daily Routine run is saved once per market date. Qualified recommendations are paper-tracked automatically; no broker orders are placed.")

    if storage.get("durable"):
        st.success(f"Persistent storage: {storage.get('mode', 'SUPABASE')} · Programme {storage.get('programme_id', 'default')}")
    else:
        detail = storage.get("error") or storage.get("message") or "Durable storage is not configured."
        st.error(f"Persistence warning: {storage.get('mode', 'LOCAL')} — {detail}")
        st.caption("On Streamlit Cloud, local-only records may disappear after a restart or redeploy. Configure Supabase before relying on the 30-day count.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Progress", f"{summary['days_completed']}/{summary['target_days']} days")
    c2.metric("Paper Trades", summary["trades_total"], f"{summary['open_trades']} open")
    c3.metric("Closed PF", summary["profit_factor"] if summary["closed_trades"] else "Collecting")
    c4.metric("Status", summary["status"])
    st.progress(summary["progress_pct"] / 100.0, text=f"{summary['progress_pct']}% of the 30-day programme complete")

    days = pd.DataFrame(tracker.get("days", []))
    trades = pd.DataFrame(tracker.get("trades", []))
    t1, t2 = st.tabs(["Daily Log", "Paper Trades"])
    with t1:
        st.dataframe(days.sort_values("date", ascending=False) if not days.empty else days, use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(trades, use_container_width=True, hide_index=True)

    e1, e2 = st.columns([3, 1])
    e1.download_button("Download 30-Day Evidence", json.dumps(tracker, indent=2).encode("utf-8"), file_name="catalyst_30_day_auto_validation.json", mime="application/json", use_container_width=True)
    if e2.button("Reset Programme", use_container_width=True):
        reset_tracker()
        st.rerun()

    with st.expander("Recovery & persistence", expanded=not bool(storage.get("durable"))):
        st.markdown("**Recover previous evidence without inventing results**")
        evidence = st.file_uploader("Import a previous 30-Day Evidence JSON", type=["json"], key="auto_validation_recovery_json")
        if evidence is not None and st.button("Merge imported evidence", use_container_width=True, key="merge_auto_validation_evidence"):
            try:
                incoming = json.loads(evidence.getvalue().decode("utf-8"))
                merged = merge_tracker_evidence(incoming)
                st.success(f"Evidence merged. Tracker now contains {tracker_summary(merged)['days_completed']} unique days.")
                st.rerun()
            except Exception as exc:
                st.error(f"Evidence could not be merged: {exc}")

        st.markdown("**Manually restore known completed days**")
        st.caption("Use this only for days you know the Daily Routine completed. Restored days are marked RECOVERED and no trade outcome is fabricated.")
        raw_dates = st.text_area("Completed dates (YYYY-MM-DD, one per line)", key="recovery_dates", placeholder="2026-08-05\n2026-08-06\n2026-08-07")
        recovery_note = st.text_input("Recovery note", value="Recovered after Streamlit storage reset.", key="recovery_note")
        if st.button("Restore these days", use_container_width=True, key="restore_validation_days"):
            dates = [line.strip() for line in raw_dates.splitlines() if line.strip()]
            if not dates:
                st.warning("Enter at least one date to restore.")
            else:
                recovered = recover_validation_days(dates, note=recovery_note)
                st.success(f"Recovery complete. Tracker now contains {tracker_summary(recovered)['days_completed']} unique days.")
                st.rerun()

        st.markdown("**Supabase setup**")
        st.caption("Run `supabase_schema.sql`, then add SUPABASE_URL, SUPABASE_KEY and optionally CATALYST_VALIDATION_PROGRAMME_ID to Streamlit Secrets. See README_V14_3_2.md.")


def _render_proof_validation() -> None:
    _render_auto_validation()
    st.divider()
    st.markdown("### v14.3 Quant Research Centre")
    st.caption("Generate a reproducible proof report, compare it with the locked v9.2.1 baseline and archive every run.")

    trades, configuration, source = _validation_trades()
    if trades.empty:
        status_card(
            "Run Historical Backtesting first, or upload catalyst_backtest_trades.csv above. No strategy assumptions are changed by validation.",
            "info",
        )
        return

    baseline = _baseline_report()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Evidence Trades", len(trades))
    c2.metric("Source", source)
    c3.metric("Build", APP_VERSION)
    c4.metric("Baseline", f"v{baseline.get('metadata', {}).get('build', '-')}" if baseline else "Not found")

    if st.button("Generate v14.3 Validation Report", type="primary", use_container_width=True):
        with st.spinner("Running profitability, consistency, drawdown, stress and calibration checks..."):
            report = build_proof_report(
                trades,
                build_version=APP_VERSION,
                configuration=configuration,
            )
            saved_path = save_validation_report(report)
            st.session_state["proof_validation_report"] = report
            st.session_state["proof_validation_saved_path"] = str(saved_path)

    report = st.session_state.get("proof_validation_report")
    if not report:
        return

    verdict = report["verdict"]
    tone = "positive" if verdict == "PASS" else ("info" if verdict == "CONDITIONAL PASS" else "warning")
    saved_path = st.session_state.get("proof_validation_saved_path", "")
    status_card(
        f"Verdict: {verdict} — {report['checks_passed']}/{report['checks_total']} checks passed."
        + (f" Archived as {saved_path}." if saved_path else ""),
        tone,
    )

    overall = report["overall"]
    stress = report["stress"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Net Return", f"{overall['total_return_pct']}%")
    c2.metric("Profit Factor", overall["profit_factor"])
    c3.metric("Max Drawdown", f"{overall['max_drawdown_pct']}%")
    c4.metric("Stress PF", stress["profit_factor"])

    checks = pd.DataFrame([
        {"check": key.replace("_", " ").title(), "result": "PASS" if value else "FAIL"}
        for key, value in report["checks"].items()
    ])
    st.dataframe(checks, use_container_width=True, hide_index=True)

    if baseline:
        st.markdown("#### Comparison with locked v9.2.1 baseline")
        st.caption("Positive change is not automatically better for trade count; use profit factor, expectancy, drawdown and stress survival as the main evidence.")
        st.dataframe(summary_frame(report, baseline), use_container_width=True, hide_index=True)

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(["By Year", "Score Bands", "Tickers", "Regimes", "Holding Period", "Adaptive Confidence", "Restrictions", "Stress Drivers", "Attribution", "Calibration"])
    with tab1:
        st.dataframe(pd.DataFrame(report["by_year"]), use_container_width=True, hide_index=True)
    with tab2:
        st.dataframe(pd.DataFrame(report["by_score_band"]), use_container_width=True, hide_index=True)
    with tab3:
        st.dataframe(pd.DataFrame(report["by_ticker"]), use_container_width=True, hide_index=True, height=360)
    with tab4:
        st.dataframe(pd.DataFrame(report["by_regime"]), use_container_width=True, hide_index=True)
    with tab5:
        st.dataframe(pd.DataFrame(report.get("by_holding_period", [])), use_container_width=True, hide_index=True)
    with tab6:
        st.dataframe(pd.DataFrame(report.get("by_adaptive_confidence", [])), use_container_width=True, hide_index=True)
    with tab7:
        st.caption("Why adaptive confidence reduced or blocked position size. A trade may appear under more than one reason.")
        st.dataframe(pd.DataFrame(report.get("decision_filter_diagnostics", [])), use_container_width=True, hide_index=True)
    with tab8:
        st.caption("Separates the impact of costs and delayed entry instead of reporting only the combined stress result.")
        st.dataframe(pd.DataFrame(report.get("stress_decomposition", [])), use_container_width=True, hide_index=True)
    with tab9:
        st.caption("Observed component differences between winning and losing completed trades. This is attribution, not causal proof.")
        st.dataframe(pd.DataFrame(report.get("feature_attribution", [])), use_container_width=True, hide_index=True)
    with tab10:
        st.caption("Compares adaptive confidence bands with realised win rates. Large gaps indicate confidence is not yet calibrated as a probability.")
        st.dataframe(pd.DataFrame(report.get("confidence_calibration", [])), use_container_width=True, hide_index=True)

    st.markdown("#### Execution Stress Test")
    st.caption("Subtracts an additional 0.20% cost and 0.15% delayed-entry penalty from every completed trade.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Stress Return", f"{stress['total_return_pct']}%")
    c2.metric("Stress Profit Factor", stress["profit_factor"])
    c3.metric("Stress Drawdown", f"{stress['max_drawdown_pct']}%")

    try:
        pdf_bytes = build_validation_pdf(report, baseline=baseline)
    except RuntimeError as exc:
        pdf_bytes = None
        st.warning(str(exc))

    export1, export2, export3 = st.columns(3)
    export1.download_button(
        "Download PDF Report",
        pdf_bytes or b"",
        file_name=f"catalyst_validation_report_v{APP_VERSION}.pdf",
        mime="application/pdf",
        disabled=pdf_bytes is None,
        use_container_width=True,
    )
    export2.download_button(
        "Download JSON Evidence",
        json.dumps(report, indent=2, default=str).encode("utf-8"),
        file_name=f"catalyst_validation_report_v{APP_VERSION}.json",
        mime="application/json",
        use_container_width=True,
    )
    export3.download_button(
        "Download Comparison CSV",
        summary_frame(report, baseline).to_csv(index=False).encode("utf-8"),
        file_name=f"catalyst_validation_comparison_v{APP_VERSION}.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown("#### v14.3 Quant Research Lab")
    st.caption("Run controlled A/B experiments on the exact same completed trades. Production trading logic is not changed.")

    locked = load_locked_benchmark()
    lock_col, status_col = st.columns([1, 2])
    if lock_col.button("Lock Current Report as Research Benchmark", use_container_width=True):
        benchmark_path = lock_benchmark(report)
        st.success(f"Benchmark locked at {benchmark_path}.")
        locked = load_locked_benchmark()
    status_col.metric(
        "Locked Research Benchmark",
        f"v{(locked or {}).get('metadata', {}).get('build', '-')}" if locked else "Not locked",
    )

    presets = {
        "80-85 score band": ("score_range", {"minimum": 80, "maximum": 85}),
        "JPM + MSFT + GOOGL only": ("ticker_subset", {"tickers": ["JPM", "MSFT", "GOOGL"]}),
        "Exclude NVDA + AVGO": ("exclude_tickers", {"tickers": ["NVDA", "AVGO"]}),
        "Confidence 58+": ("confidence_floor", {"minimum": 58}),
        "6-20 day swing trades": ("holding_period", {"minimum_days": 6, "maximum_days": 20}),
        "Core swing combination": ("combined", {"steps": [
            {"type": "score_range", "params": {"minimum": 80, "maximum": 85}},
            {"type": "ticker_subset", "params": {"tickers": ["JPM", "MSFT", "GOOGL"]}},
            {"type": "holding_period", "params": {"minimum_days": 6, "maximum_days": 20}},
        ]}),
    }
    preset_name = st.selectbox("Research experiment", list(presets), key="research_lab_preset")
    experiment_type, experiment_params = presets[preset_name]
    st.code(json.dumps({"type": experiment_type, "params": experiment_params}, indent=2), language="json")

    if st.button("Run Controlled A/B Experiment", type="secondary", use_container_width=True):
        result = evaluate_experiment(
            trades,
            name=preset_name,
            experiment_type=experiment_type,
            params=experiment_params,
        )
        result_path = save_experiment(result)
        st.session_state["research_experiment_result"] = result
        st.session_state["research_experiment_path"] = str(result_path)

    experiment_result = st.session_state.get("research_experiment_result")
    if experiment_result:
        experiment_verdict = experiment_result.get("verdict", "REJECT")
        status_card(
            f"Experiment {experiment_result.get('name')}: {experiment_verdict}. "
            f"Archived as {st.session_state.get('research_experiment_path', '-')}.",
            "positive" if experiment_verdict == "PROMOTE" else "warning",
        )
        st.dataframe(experiment_comparison_frame(experiment_result), use_container_width=True, hide_index=True)
        checks_frame = pd.DataFrame([
            {"promotion gate": key.replace("_", " ").title(), "result": "PASS" if value else "FAIL"}
            for key, value in (experiment_result.get("promotion_checks") or {}).items()
        ])
        st.dataframe(checks_frame, use_container_width=True, hide_index=True)
        ex1, ex2 = st.columns(2)
        ex1.download_button(
            "Download Experiment JSON",
            json.dumps(experiment_result, indent=2, default=str).encode("utf-8"),
            file_name=f"catalyst_experiment_{experiment_result.get('experiment_id', 'result')}.json",
            mime="application/json",
            use_container_width=True,
        )
        ex2.download_button(
            "Download A/B Comparison CSV",
            experiment_comparison_frame(experiment_result).to_csv(index=False).encode("utf-8"),
            file_name=f"catalyst_experiment_{experiment_result.get('experiment_id', 'result')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    experiment_history = list_experiments()
    if not experiment_history.empty:
        st.markdown("##### Experiment History")
        st.dataframe(experiment_history.drop(columns=["path"], errors="ignore"), use_container_width=True, hide_index=True, height=220)

    st.markdown("#### Validation History")
    history = list_validation_reports()
    if history.empty:
        st.caption("No archived reports yet.")
    else:
        st.dataframe(history.drop(columns=["path"], errors="ignore"), use_container_width=True, hide_index=True, height=220)
        selected = st.selectbox("Open archived report", history["file"].tolist(), key="validation_history_select")
        row = history.loc[history["file"] == selected]
        if not row.empty:
            archived = load_json_report(row.iloc[0]["path"])
            if archived:
                st.download_button(
                    "Download Selected Archived JSON",
                    json.dumps(archived, indent=2, default=str).encode("utf-8"),
                    file_name=selected,
                    mime="application/json",
                    use_container_width=True,
                )

def render_validation() -> None:
    section_header(
        "Validation Centre",
        "Versioned proof reports, baseline comparison and forward-return validation.",
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
