from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engine.daily_routine import run_daily_routine
from data.daily_routine_store import save_latest_routine
from ui.components import empty_state, section_header, status_card

STATE_PATH = Path("storage/daily_routine_last_run.json")


def _save_last_run(summary: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def _load_last_run() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def render_daily_routine() -> None:
    section_header(
        "Autonomous Daily Routine",
        "One button downloads data, detects the regime, scans the universe, builds plans, refreshes intelligence and creates exports.",
    )

    last_run = st.session_state.get("daily_routine_summary") or _load_last_run()
    if last_run:
        st.caption(
            f"Last run: {last_run.get('finished_at', 'Unknown')} · "
            f"{'Successful' if last_run.get('success') else 'Needs attention'}"
        )

    c1, c2 = st.columns(2)
    with c1:
        period = st.selectbox("Price history", ["6mo", "1y", "2y"], index=1)
    with c2:
        max_tickers = st.number_input("Maximum symbols", min_value=25, max_value=1200, value=750, step=25)

    send_alerts = st.toggle("Refresh and deliver configured alerts", value=True)
    confirm_repeat = st.checkbox("Allow another run today", value=False, help="Prevents accidental duplicate routines.")

    today = datetime.now(timezone.utc).date().isoformat()
    already_ran_today = bool(last_run and str(last_run.get("finished_at", "")).startswith(today))
    disabled = already_ran_today and not confirm_repeat

    if disabled:
        status_card("A routine has already run today. Tick ‘Allow another run today’ to run it again.", "warning")

    if st.button("🚀 Run Daily Routine", type="primary", use_container_width=True, disabled=disabled):
        progress_bar = st.progress(0, text="Starting Catalyst AI daily routine…")
        live_status = st.empty()
        stage_log = st.empty()
        events: list[dict] = []

        def update(stage: str, percent: int, message: str) -> None:
            progress_bar.progress(percent, text=message)
            events.append({"stage": stage, "message": message})
            live_status.info(message)
            stage_log.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)

        result = run_daily_routine(
            period=period,
            max_tickers=int(max_tickers),
            progress=update,
            send_alerts=send_alerts,
        )
        summary = result.summary()
        st.session_state["daily_routine_result"] = result
        st.session_state["daily_routine_summary"] = summary
        st.session_state["scan_results"] = result.scan_results
        st.session_state["trade_plans"] = result.trade_plans
        st.session_state["market_regime"] = result.regime
        st.session_state["scan_errors"] = result.market_errors
        st.session_state["scan_comparison"] = result.comparison
        st.session_state["scan_id"] = result.scan_id
        st.session_state["daily_brief"] = result.brief
        _save_last_run(summary)
        if result.success:
            save_latest_routine(
                scan=result.scan_results,
                plans=result.trade_plans,
                regime=result.regime,
                summary=summary,
            )
        progress_bar.progress(100, text="Daily Routine complete" if result.success else "Daily Routine stopped")
        st.rerun()

    result = st.session_state.get("daily_routine_result")
    summary = st.session_state.get("daily_routine_summary") or last_run
    if not summary:
        empty_state("No daily routine yet", "Press Run Daily Routine to update the complete trading desk.", "🚀")
        return

    if summary.get("success"):
        status_card(f"Daily Routine completed in {summary.get('duration_seconds', 0)} seconds.", "positive")
    else:
        status_card("The routine stopped before all stages completed. Review the stage log below.", "warning")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", summary.get("symbols_scanned", 0))
    c2.metric("BUY", summary.get("buy_count", 0))
    c3.metric("WATCH", summary.get("watch_count", 0))
    c4.metric("Trade Plans", summary.get("trade_plan_count", 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Data Errors", summary.get("data_error_count", 0))
    c2.metric("Data Success", f"{summary.get('market_success_rate_pct', 0)}%")
    c3.metric("Quarantined", summary.get("quarantined_count", 0))
    c4.metric("Exports", summary.get("exports_created", 0))

    stages = pd.DataFrame(summary.get("stages", []))
    if not stages.empty:
        st.markdown("### Run Summary")
        st.dataframe(stages, use_container_width=True, hide_index=True)

    if result is not None and result.exports:
        with st.expander("Created exports"):
            for path in result.exports:
                st.code(path)
