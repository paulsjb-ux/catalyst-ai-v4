from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from data.daily_routine_store import load_latest_routine, save_latest_routine
from engine.daily_routine import run_daily_routine
from engine.swing_focus import build_swing_desk, load_proof_report, policy_from_proof, swing_desk_summary
from ui.components import empty_state, metric_card, status_card

STATE_PATH = Path("storage/daily_routine_last_run.json")


def _save_last_run(summary: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def _load_last_run() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _latest_payload():
    persisted = load_latest_routine()
    scan = st.session_state.get("scan_results", persisted.get("scan", pd.DataFrame()))
    plans = st.session_state.get("trade_plans", persisted.get("plans", pd.DataFrame()))
    regime = st.session_state.get("market_regime", persisted.get("regime", {}))
    summary = st.session_state.get("daily_routine_summary", persisted.get("summary", {})) or _load_last_run()
    desk = st.session_state.get("swing_desk")
    if not isinstance(desk, pd.DataFrame) and isinstance(scan, pd.DataFrame) and not scan.empty:
        report = load_proof_report()
        desk = build_swing_desk(scan, plans, regime, proof_report=report)
    return scan, plans, regime, summary, desk if isinstance(desk, pd.DataFrame) else pd.DataFrame()


def _run_routine(period: str, max_tickers: int, send_alerts: bool) -> None:
    progress_bar = st.progress(0, text="Starting the Catalyst trading desk…")
    live_status = st.empty()

    def update(stage: str, percent: int, message: str) -> None:
        progress_bar.progress(percent, text=message)
        live_status.caption(message)

    result = run_daily_routine(
        period=period,
        max_tickers=int(max_tickers),
        progress=update,
        send_alerts=send_alerts,
    )
    summary = result.summary()
    st.session_state.update({
        "daily_routine_result": result,
        "daily_routine_summary": summary,
        "scan_results": result.scan_results,
        "trade_plans": result.trade_plans,
        "market_regime": result.regime,
        "scan_errors": result.market_errors,
        "scan_comparison": result.comparison,
        "scan_id": result.scan_id,
        "daily_brief": result.brief,
        "swing_desk": result.swing_desk,
        "swing_summary": result.swing_summary,
        "proof_health": result.proof_health,
    })
    _save_last_run(summary)
    if result.success:
        save_latest_routine(scan=result.scan_results, plans=result.trade_plans, regime=result.regime, summary=summary)
    progress_bar.progress(100, text="Trading desk ready" if result.success else "Routine stopped")
    st.rerun()


def render_daily_routine() -> None:
    st.markdown(
        """
        <div class="routine-command">
          <div class="routine-eyebrow">CATALYST AI v10.0</div>
          <div class="routine-title">Today’s Trading Desk</div>
          <div class="routine-subtitle">One button updates the market, validates the evidence and selects only the strongest swing opportunities.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scan, plans, regime, summary, desk = _latest_payload()
    last_run = summary or _load_last_run()

    with st.expander("Routine settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        period = c1.selectbox("Price history", ["6mo", "1y", "2y"], index=1)
        max_tickers = c2.number_input("Maximum symbols", min_value=25, max_value=1200, value=750, step=25)
        send_alerts = c3.toggle("Refresh alerts", value=True)
    if "period" not in locals():
        period, max_tickers, send_alerts = "1y", 750, True

    today = datetime.now(timezone.utc).date().isoformat()
    already_ran_today = bool(last_run and str(last_run.get("finished_at", "")).startswith(today))
    button_label = "↻ Run Again" if already_ran_today else "▶ Run Daily Routine"

    if st.button(button_label, type="primary", use_container_width=True, key="v100_run_daily_routine"):
        _run_routine(period, int(max_tickers), send_alerts)

    if not summary or not isinstance(scan, pd.DataFrame) or scan.empty:
        empty_state("Trading desk not run yet", "Press the button once. Catalyst will do the rest.", "▶")
        return

    if not summary.get("success", True):
        status_card("The last routine needs attention. Open the run details below.", "warning")
        return

    finished = str(summary.get("finished_at", ""))
    st.caption(f"Last completed: {finished} · Runtime {summary.get('duration_seconds', 0)} seconds")

    policy = policy_from_proof(load_proof_report())
    swing_summary = swing_desk_summary(desk, policy)
    regime_name = str((regime or {}).get("regime", "UNKNOWN")).replace("_", " ")
    proof_verdict = summary.get("proof_verdict", "CONDITIONAL PASS")

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Market regime", regime_name, "Current environment"), unsafe_allow_html=True)
    c2.markdown(metric_card("Qualified swings", str(swing_summary["qualified_swing_trades"]), f"Maximum {policy.maximum_new_positions} new"), unsafe_allow_html=True)
    c3.markdown(metric_card("Position cap", f"{policy.position_cap_pct:g}%", "Reduced size by default"), unsafe_allow_html=True)
    c4.markdown(metric_card("Proof status", str(proof_verdict), "Validation evidence"), unsafe_allow_html=True)

    qualified = desk[desk.get("swing_status", pd.Series(index=desk.index, dtype=str)).isin(["PRIORITY", "QUALIFIED"])] if not desk.empty else pd.DataFrame()
    if qualified.empty:
        status_card("NO TRADE TODAY — no swing setup passed the full quality and regime filters.", "info")
    else:
        status_card(f"{len(qualified)} swing setup{'s' if len(qualified) != 1 else ''} passed. Review no more than {policy.maximum_new_positions} positions.", "positive")

    st.markdown("### Best Swing Opportunities")
    if desk.empty:
        empty_state("No candidates", "The scan produced no BUY or WATCH candidates.", "—")
    else:
        display = desk.copy()
        rename = {
            "daily_rank": "Rank", "ticker": "Ticker", "action": "Action", "score": "Score",
            "position_size_pct": "Size %", "entry_price": "Entry", "target_price": "Target",
            "stop_loss": "Stop", "risk_reward": "R/R", "trend": "Trend",
        }
        columns = [c for c in rename if c in display.columns]
        st.dataframe(display[columns].rename(columns=rename), use_container_width=True, hide_index=True)

    top = qualified.head(policy.maximum_new_positions) if not qualified.empty else pd.DataFrame()
    if not top.empty:
        st.markdown("### Today’s Action")
        for _, row in top.iterrows():
            st.markdown(
                f"**{row.get('ticker')} — {row.get('action')}**  \n"
                f"Score {float(row.get('score', 0)):.0f} · Reduced size {float(row.get('position_size_pct', 0)):.0f}% · "
                f"Entry {row.get('entry_price', '—')} · Target {row.get('target_price', '—')} · Stop {row.get('stop_loss', '—')}"
            )

    st.caption(
        f"Swing focus uses the currently validated score band {policy.score_min:g}–{policy.score_max:g} and gives priority to "
        f"{', '.join(policy.preferred_tickers)}. A priority label is evidence-based, not a guarantee."
    )

    with st.expander("Run details and diagnostics"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Symbols scanned", summary.get("symbols_scanned", 0))
        c2.metric("BUY signals", summary.get("buy_count", 0))
        c3.metric("WATCH signals", summary.get("watch_count", 0))
        c4.metric("Data success", f"{summary.get('market_success_rate_pct', 0)}%")
        stages = pd.DataFrame(summary.get("stages", []))
        if not stages.empty:
            st.dataframe(stages, use_container_width=True, hide_index=True)
