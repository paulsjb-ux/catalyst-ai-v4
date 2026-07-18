from __future__ import annotations

from datetime import date
import pandas as pd
import streamlit as st

from data.history_store import load_latest_scan
from data.paper_store import clear_paper_state, load_paper_state, save_paper_state
from engine.paper_trading import DEFAULT_CONFIG, new_state, performance_metrics, process_day, trades_frame
from ui.components import empty_state, section_header, status_card


def _regime_label() -> str:
    regime = st.session_state.get("market_regime", {})
    if isinstance(regime, dict):
        return str(regime.get("regime", "UNKNOWN"))
    return str(regime or "UNKNOWN")


def _latest_scan() -> pd.DataFrame:
    session_scan = st.session_state.get("scan_results", pd.DataFrame())
    if isinstance(session_scan, pd.DataFrame) and not session_scan.empty:
        return session_scan
    return load_latest_scan()


def _money(value: float) -> str:
    return f"£{value:,.2f}"


def render_paper_trading() -> None:
    section_header(
        "30-Day Paper Trading Simulator",
        "Forward-test Catalyst with virtual money. One simulated run per trading day; no hindsight prices.",
    )

    state = load_paper_state()

    if state is None:
        status_card("No paper-trading trial is active. Start with the recommended fixed rules below.", "info")
        with st.form("start_paper_trial"):
            c1, c2, c3 = st.columns(3)
            starting_cash = c1.number_input("Starting balance (£)", min_value=1000.0, value=10000.0, step=1000.0)
            max_trades = c2.number_input("Maximum open trades", min_value=1, max_value=10, value=5)
            max_position = c3.number_input("Maximum per trade (£)", min_value=100.0, value=2000.0, step=100.0)
            c4, c5, c6 = st.columns(3)
            min_score = c4.number_input("Minimum BUY score", min_value=0.0, max_value=100.0, value=75.0)
            minimum_rr = c5.number_input("Minimum risk/reward", min_value=1.0, value=2.0, step=0.25)
            max_hold = c6.number_input("Maximum holding days", min_value=1, max_value=30, value=10)
            submitted = st.form_submit_button("Start 30-Trading-Day Trial", use_container_width=True)

        if submitted:
            config = {
                **DEFAULT_CONFIG,
                "starting_cash": float(starting_cash),
                "max_open_trades": int(max_trades),
                "max_position_value": float(max_position),
                "minimum_score": float(min_score),
                "minimum_risk_reward": float(minimum_rr),
                "maximum_holding_days": int(max_hold),
            }
            save_paper_state(new_state(config))
            st.success("30-day paper-trading trial started.")
            st.rerun()
        return

    metrics = performance_metrics(state)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Day", f"{metrics['days_run']} / {state['config']['trial_days']}")
    c2.metric("Portfolio", _money(float(metrics["equity"])))
    c3.metric("Net P&L", _money(float(metrics["net_pnl"])), f"{metrics['return_pct']}%")
    c4.metric("Open Trades", int(metrics["open_trades"]))
    c5.metric("Win Rate", f"{metrics['win_rate_pct']}%")

    if state.get("active"):
        scan = _latest_scan()
        today_already_run = any(item.get("date") == date.today().isoformat() for item in state.get("daily_runs", []))
        if scan.empty:
            st.warning("Run the Daily Routine or Market Scan first. The simulator needs today's latest scan.")
        elif today_already_run:
            st.info("Today's paper-trading run is already recorded. Return on the next trading day.")
        else:
            if st.button("Run Today's Paper Trades", type="primary", use_container_width=True):
                updated = process_day(state, scan, _regime_label(), date.today().isoformat())
                save_paper_state(updated)
                latest = updated["daily_runs"][-1]
                opened = ", ".join(latest["opened"]) or "none"
                closed = ", ".join(latest["closed"]) or "none"
                st.success(f"Day recorded. Opened: {opened}. Closed: {closed}.")
                st.rerun()
    else:
        st.success("The 30-trading-day trial is complete. Review the final performance below.")

    st.markdown("### Trial Rules")
    cfg = state["config"]
    st.caption(
        f"BUY score ≥ {cfg['minimum_score']} · risk/reward ≥ {cfg['minimum_risk_reward']}:1 · "
        f"max {cfg['max_open_trades']} open trades · max {_money(float(cfg['max_position_value']))} each · "
        f"{cfg['risk_per_trade_pct']}% risk · {cfg['maximum_holding_days']}-day maximum hold · "
        f"{cfg['entry_slippage_pct']}% entry and {cfg['exit_slippage_pct']}% exit slippage."
    )

    st.markdown("### Open Trades")
    open_frame = trades_frame(state, "OPEN")
    if open_frame.empty:
        st.caption("No open simulated positions.")
    else:
        wanted = ["ticker", "entry_date", "entry_price", "quantity", "last_price", "target_price", "stop_price", "score", "days_held"]
        st.dataframe(open_frame[[c for c in wanted if c in open_frame.columns]], use_container_width=True, hide_index=True)

    st.markdown("### Closed Trades")
    closed_frame = trades_frame(state, "CLOSED")
    if closed_frame.empty:
        st.caption("No completed simulated trades yet.")
    else:
        wanted = ["ticker", "entry_date", "entry_price", "exit_date", "exit_price", "exit_reason", "quantity", "net_pnl", "return_pct"]
        view = closed_frame[[c for c in wanted if c in closed_frame.columns]]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button("Download trade history CSV", closed_frame.to_csv(index=False).encode("utf-8"), "catalyst_paper_trades.csv", "text/csv")

    st.markdown("### Performance")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Completed Trades", int(metrics["closed_trades"]))
    p2.metric("Profit Factor", metrics["profit_factor"])
    p3.metric("Average Win", _money(float(metrics["average_win"])))
    p4.metric("Maximum Drawdown", f"{metrics['max_drawdown_pct']}%")

    history = pd.DataFrame(state.get("equity_history", []))
    if not history.empty and "date" in history.columns and "equity" in history.columns:
        history = history.drop_duplicates("date", keep="last").set_index("date")
        st.line_chart(history[["equity"]])

    with st.expander("Trial administration"):
        st.warning("Resetting permanently clears the current paper-trading trial.")
        confirm = st.checkbox("I understand the current simulation will be deleted")
        if st.button("Reset Paper-Trading Trial", disabled=not confirm):
            clear_paper_state()
            st.rerun()

    if not state.get("daily_runs"):
        empty_state("Ready for Day 1", "Run the Daily Routine or Market Scan, then press Run Today's Paper Trades.", "🧪")
