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
        desk = build_swing_desk(scan, plans, regime, proof_report=load_proof_report())
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
    scan, plans, regime, summary, desk = _latest_payload()
    last_run = summary or _load_last_run()

    finished = str(last_run.get("finished_at", "")) if last_run else ""
    runtime = float(last_run.get("duration_seconds", 0) or 0) if last_run else 0
    run_label = finished.replace("T", " ")[:16] if finished else "Not run yet"
    regime_name = str((regime or {}).get("regime", "AWAITING SCAN")).replace("_", " ")
    proof_verdict = str(last_run.get("proof_verdict", "AWAITING RUN")) if last_run else "AWAITING RUN"
    health = "HEALTHY" if (not last_run or last_run.get("success", True)) else "ATTENTION"

    st.markdown(
        f"""
        <div class="desk-status-strip">
          <div><span>MARKET</span><strong>{regime_name}</strong></div>
          <div><span>LAST RUN</span><strong>{run_label}</strong></div>
          <div><span>VALIDATION</span><strong>{proof_verdict}</strong></div>
          <div><span>ENGINE</span><strong>{health}</strong></div>
        </div>
        <div class="routine-command v101-command">
          <div class="routine-brand-row">
            <div class="routine-title">Daily Trading Desk <span>· Catalyst AI v11.1</span></div>
            <div class="routine-subtitle">One run updates, validates and ranks today’s swing opportunities.</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Advanced routine settings", expanded=False):
        c1, c2, c3 = st.columns(3)
        period = c1.selectbox("Price history", ["6mo", "1y", "2y"], index=1)
        max_tickers = c2.number_input("Maximum symbols", min_value=25, max_value=1200, value=750, step=25)
        send_alerts = c3.toggle("Refresh alerts", value=True)
    if "period" not in locals():
        period, max_tickers, send_alerts = "1y", 750, True

    today = datetime.now(timezone.utc).date().isoformat()
    already_ran_today = bool(last_run and str(last_run.get("finished_at", "")).startswith(today))
    button_label = "↻ RUN DAILY ROUTINE AGAIN" if already_ran_today else "▶ RUN DAILY ROUTINE"

    if st.button(button_label, type="primary", use_container_width=True, key="v101_run_daily_routine"):
        _run_routine(period, int(max_tickers), send_alerts)

    if not summary or not isinstance(scan, pd.DataFrame) or scan.empty:
        st.markdown(
            '<div class="desk-awaiting"><strong>Ready.</strong> Press the button once and Catalyst will build today’s complete trading desk.</div>',
            unsafe_allow_html=True,
        )
        return

    if not summary.get("success", True):
        status_card("The last routine needs attention. Open the diagnostics panel for details.", "warning")
        return

    policy = policy_from_proof(load_proof_report())
    swing_summary = swing_desk_summary(desk, policy)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_card("Market", regime_name, "Current regime"), unsafe_allow_html=True)
    c2.markdown(metric_card("Qualified", str(swing_summary["qualified_swing_trades"]), f"Max {policy.maximum_new_positions} new positions"), unsafe_allow_html=True)
    c3.markdown(metric_card("Position cap", f"{policy.position_cap_pct:g}%", "Reduced size"), unsafe_allow_html=True)
    c4.markdown(metric_card("Validation", proof_verdict, "Latest proof status"), unsafe_allow_html=True)

    status_series = desk.get("swing_status", pd.Series(index=desk.index, dtype=str)) if not desk.empty else pd.Series(dtype=str)
    qualified = desk[status_series.isin(["PRIORITY", "QUALIFIED"])] if not desk.empty else pd.DataFrame()
    if qualified.empty:
        st.markdown(
            '<div class="daily-verdict verdict-cash"><span>TODAY’S VERDICT</span><strong>NO TRADE — REMAIN IN CASH</strong><p>No swing setup passed all quality, evidence and regime filters.</p></div>',
            unsafe_allow_html=True,
        )
    else:
        plural = "S" if len(qualified) != 1 else ""
        st.markdown(
            f'<div class="daily-verdict verdict-trade"><span>TODAY’S VERDICT</span><strong>{len(qualified)} QUALIFIED SWING SETUP{plural}</strong><p>Review no more than {policy.maximum_new_positions} new positions at reduced size.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown("### Today’s ranked opportunities")
    if desk.empty:
        empty_state("No candidates", "The scan produced no BUY or WATCH candidates.", "—")
    else:
        display = desk.copy()
        rename = {
            "daily_rank": "Rank", "ticker": "Ticker", "action": "Action", "score": "Score",
            "swing_status": "Status", "position_size_pct": "Size %", "entry_price": "Entry",
            "target_price": "Target", "stop_loss": "Stop", "risk_reward": "R/R", "trend": "Trend",
        }
        columns = [c for c in rename if c in display.columns]
        st.dataframe(display[columns].rename(columns=rename), use_container_width=True, hide_index=True)

    top = qualified.head(policy.maximum_new_positions) if not qualified.empty else pd.DataFrame()
    if not top.empty:
        st.markdown("### Action plan")
        action_columns = st.columns(len(top))
        for column, (_, row) in zip(action_columns, top.iterrows()):
            with column:
                rank = int(row.get("daily_rank", 0) or 0)
                score = float(row.get("score", 0) or 0)
                size = float(row.get("position_size_pct", 0) or 0)
                card = (
                    f'<div class="action-card"><div class="action-rank">RANK {rank}</div>'
                    f'<div class="action-ticker">{row.get("ticker")}</div>'
                    f'<div class="action-label">{row.get("action")}</div>'
                    f'<div class="action-detail">Score <b>{score:.0f}</b> · Size <b>{size:.0f}%</b></div>'
                    f'<div class="action-levels">Entry {row.get("entry_price", "—")}<br>'
                    f'Target {row.get("target_price", "—")}<br>Stop {row.get("stop_loss", "—")}</div></div>'
                )
                st.markdown(card, unsafe_allow_html=True)

    st.caption(
        f"Completed {finished or '—'} in {runtime:g}s. Swing focus currently uses score band "
        f"{policy.score_min:g}–{policy.score_max:g} and prioritises {', '.join(policy.preferred_tickers)}. "
        "Priority is evidence-based, not a guarantee."
    )

    with st.expander("Diagnostics and run details", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Symbols scanned", summary.get("symbols_scanned", 0))
        c2.metric("BUY signals", summary.get("buy_count", 0))
        c3.metric("WATCH signals", summary.get("watch_count", 0))
        c4.metric("Data success", f"{summary.get('market_success_rate_pct', 0)}%")
        stages = pd.DataFrame(summary.get("stages", []))
        if not stages.empty:
            st.dataframe(stages, use_container_width=True, hide_index=True)
