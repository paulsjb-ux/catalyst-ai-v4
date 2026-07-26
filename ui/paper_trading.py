from __future__ import annotations

from datetime import date, datetime
import pandas as pd
import streamlit as st

from data.history_store import load_latest_scan
from data.paper_store import clear_paper_state, load_paper_state, save_paper_state
from engine.paper_trading import (
    DEFAULT_CONFIG,
    candidate_evaluation,
    new_state,
    next_weekday,
    performance_metrics,
    performance_by_setup,
    process_day,
    ticker_currency,
    trade_journal,
    trades_frame,
)
from ui.components import empty_state, section_header, status_card


def _regime_label() -> str:
    regime = st.session_state.get("market_regime", {})
    if isinstance(regime, dict):
        return str(regime.get("regime", "UNKNOWN"))
    return str(regime or "UNKNOWN")


def _latest_scan() -> pd.DataFrame:
    """Return the latest scan enriched with target/stop trade plans."""
    session_scan = st.session_state.get("scan_results", pd.DataFrame())
    scan = session_scan if isinstance(session_scan, pd.DataFrame) and not session_scan.empty else load_latest_scan()
    if scan is None or scan.empty:
        return pd.DataFrame()

    plans = st.session_state.get("trade_plans", pd.DataFrame())
    if isinstance(plans, pd.DataFrame) and not plans.empty and "ticker" in plans.columns:
        plan_columns = [
            column for column in [
                "ticker", "entry_price", "target_price", "stop_loss",
                "risk_pct", "reward_pct", "risk_reward", "position_quality",
                "plan_reason",
            ]
            if column in plans.columns
        ]
        scan = scan.drop(
            columns=[column for column in plan_columns if column != "ticker" and column in scan.columns],
            errors="ignore",
        ).merge(plans[plan_columns], on="ticker", how="left")

    return scan


def _money(value: float) -> str:
    return f"£{value:,.2f}"


def _native_money(value: float | None, currency: str = "USD") -> str:
    if value is None or pd.isna(value):
        return "—"
    symbols = {"GBP": "£", "USD": "$", "EUR": "€", "JPY": "¥", "AUD": "A$", "CAD": "C$", "HKD": "HK$", "CHF": "CHF "}
    return f"{symbols.get(currency, currency + ' ')}{float(value):,.2f}"


def _format_timestamp(value: str | None) -> str:
    if not value:
        return "Not run yet"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y %H:%M")
    except ValueError:
        return value


def _latest_run(state: dict) -> dict:
    runs = state.get("daily_runs", [])
    return runs[-1] if runs else {}


def _render_latest_run_summary(run: dict) -> None:
    st.markdown("### Today's Run Explanation")
    if not run:
        st.caption("No paper-trading day has been recorded yet.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stocks Scanned", int(run.get("scan_count", 0)))
    c2.metric("BUY Signals", int(run.get("buy_signal_count", 0)))
    c3.metric("Qualified", int(run.get("eligible_count", 0)))
    c4.metric("Trades Opened", len(run.get("opened", [])))

    opened = run.get("opened_details", [])
    if opened:
        st.success(
            "Opened: " + ", ".join(
                f"{item['ticker']} ({item['quantity']} shares)" for item in opened
            )
        )
        st.dataframe(pd.DataFrame(opened), use_container_width=True, hide_index=True)
    else:
        st.info("No new paper trades were opened on this run.")

    closed = run.get("closed_details", [])
    if closed:
        st.warning(
            "Closed: " + ", ".join(
                f"{item['ticker']} — {item['reason']}" for item in closed
            )
        )

    rejections = run.get("rejection_counts", {})
    capacity = run.get("skipped_capacity", [])
    sizing = run.get("skipped_position_size", [])

    if rejections or capacity or sizing:
        with st.expander("Why candidates were skipped", expanded=not opened):
            if rejections:
                rejection_frame = pd.DataFrame(
                    [{"Reason": reason, "Count": count} for reason, count in rejections.items()]
                )
                st.dataframe(rejection_frame, use_container_width=True, hide_index=True)
            if capacity:
                st.caption("Skipped because the portfolio was full: " + ", ".join(capacity))
            if sizing:
                st.caption("Skipped because position size calculated to zero: " + ", ".join(sizing))


def render_paper_trading() -> None:
    section_header(
        "30-Day Paper Trading Simulator",
        "Forward-test Catalyst with virtual money. One simulated run per trading day; no hindsight prices.",
    )

    state = load_paper_state()

    if state is None:
        status_card(
            "No paper-trading trial is active. Start with the recommended fixed rules below.",
            "info",
        )
        with st.form("start_paper_trial"):
            c1, c2, c3 = st.columns(3)
            starting_cash = c1.number_input(
                "Starting balance (£)",
                min_value=1000.0,
                value=10000.0,
                step=1000.0,
            )
            max_trades = c2.number_input(
                "Maximum open trades",
                min_value=1,
                max_value=10,
                value=5,
            )
            max_position = c3.number_input(
                "Maximum per trade (£)",
                min_value=100.0,
                value=2000.0,
                step=100.0,
            )
            c4, c5, c6 = st.columns(3)
            min_score = c4.number_input(
                "Minimum BUY score",
                min_value=0.0,
                max_value=100.0,
                value=75.0,
            )
            minimum_rr = c5.number_input(
                "Minimum risk/reward",
                min_value=1.0,
                value=2.0,
                step=0.25,
            )
            max_hold = c6.number_input(
                "Maximum holding days",
                min_value=1,
                max_value=30,
                value=10,
            )
            submitted = st.form_submit_button(
                "Start 30-Trading-Day Trial",
                use_container_width=True,
            )

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

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Average Winner", _money(float(metrics["average_win"])))
    k2.metric("Average Loser", _money(float(metrics["average_loss"])))
    k3.metric("Expectancy / Trade", _money(float(metrics["expectancy"])))
    k4.metric("Maximum Drawdown", f"{metrics['max_drawdown_pct']}%")

    scan = _latest_scan()
    latest_run = _latest_run(state)
    has_trade_plans = (
        not scan.empty
        and {"target_price", "stop_loss"}.issubset(scan.columns)
        and scan[["target_price", "stop_loss"]].notna().any(axis=None)
    )
    today = date.today().isoformat()
    today_already_run = latest_run.get("date") == today
    next_run_date = next_weekday(date.today()).strftime("%a %d %b %Y")

    st.markdown("### Daily Control")
    c1, c2, c3 = st.columns(3)
    c1.metric("Last Run", _format_timestamp(latest_run.get("recorded_at")))
    c2.metric("Next Available", next_run_date if today_already_run else "Today")
    c3.metric("Days Remaining", int(metrics["days_remaining"]))

    # A paper-trading day should still be recordable when no candidates qualify
    # or when plans are incomplete. The engine will record the run and explain
    # every rejection rather than leaving the button silently disabled.
    run_disabled = (
        not state.get("active")
        or today_already_run
        or scan.empty
    )

    button_label = (
        "Today's Paper Trades Already Run"
        if today_already_run
        else "▶ Run Today's Paper Trades"
    )

    if not state.get("active"):
        st.warning("The 30-day paper-trading trial is not active.")
    elif scan.empty:
        st.warning("No current scan is available. Run Daily Routine or Market Scan first.")
    elif not has_trade_plans:
        st.warning(
            "Target/stop plans are incomplete. You can still record today's paper-trading run; "
            "Catalyst will explain why no positions could be opened."
        )

    if st.button(
        button_label,
        type="primary",
        use_container_width=True,
        disabled=run_disabled,
        help="Records today's paper-trading decision, including a no-trade result and rejection reasons.",
    ):
        updated = process_day(state, scan, _regime_label(), today)
        save_paper_state(updated)
        st.success("Today's paper-trading run has been recorded.")
        st.rerun()

    if today_already_run:
        st.info(
            f"Today's run is complete. The next paper-trading run is available on {next_run_date}."
        )
    elif state.get("active"):
        evaluation = candidate_evaluation(scan, state, _regime_label())
        buy_count = int((scan["signal"] == "BUY").sum()) if "signal" in scan.columns else 0
        eligible_count = int(evaluation["eligible"].sum()) if not evaluation.empty else 0
        st.caption(
            f"Ready: {len(scan)} scanned · {buy_count} BUY signals · "
            f"{eligible_count} currently qualify under the trial rules."
        )

    if not state.get("active"):
        st.success("The 30-trading-day trial is complete. Review the final performance below.")

    _render_latest_run_summary(latest_run)

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
        wanted = [
            "ticker", "setup", "currency", "entry_date", "entry_price", "quantity", "last_price",
            "unrealised_pnl", "unrealised_return_pct", "target_price", "stop_price", "score", "days_held",
        ]
        view = open_frame[[c for c in wanted if c in open_frame.columns]].copy()
        if "currency" not in view.columns:
            view["currency"] = view["ticker"].map(ticker_currency)
        for column in ["entry_price", "last_price", "target_price", "stop_price"]:
            if column in view.columns:
                view[column] = [_native_money(v, c) for v, c in zip(view[column], view["currency"])]
        st.dataframe(view, use_container_width=True, hide_index=True)

    st.markdown("### Closed Trades")
    closed_frame = trades_frame(state, "CLOSED")
    if closed_frame.empty:
        st.caption("No completed simulated trades yet.")
    else:
        wanted = [
            "ticker", "setup", "currency", "entry_date", "entry_price", "exit_date", "exit_price",
            "exit_reason", "quantity", "net_pnl", "return_pct",
        ]
        view = closed_frame[[c for c in wanted if c in closed_frame.columns]].copy()
        if "currency" not in view.columns:
            view["currency"] = view["ticker"].map(ticker_currency)
        for column in ["entry_price", "exit_price"]:
            if column in view.columns:
                view[column] = [_native_money(v, c) for v, c in zip(view[column], view["currency"])]
        st.dataframe(view, use_container_width=True, hide_index=True)
        st.download_button(
            "Download trade history CSV",
            closed_frame.to_csv(index=False).encode("utf-8"),
            "catalyst_paper_trades.csv",
            "text/csv",
            use_container_width=True,
        )

    st.markdown("### Performance Analytics")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Completed Trades", int(metrics["closed_trades"]))
    p2.metric("Wins / Losses", f"{metrics['wins']} / {metrics['losses']}")
    p3.metric("Profit Factor", metrics["profit_factor"])
    p4.metric("Expectancy", _money(float(metrics["expectancy"])))

    history = pd.DataFrame(state.get("equity_history", []))
    if not history.empty and "date" in history.columns and "equity" in history.columns:
        history = history.drop_duplicates("date", keep="last").set_index("date")
        st.markdown("#### Portfolio Equity Curve")
        st.line_chart(history[["equity"]])

    st.markdown("#### Performance by Setup")
    setup_frame = performance_by_setup(state)
    if setup_frame.empty:
        st.caption("Setup statistics will appear after the first trade closes.")
    else:
        st.dataframe(setup_frame, use_container_width=True, hide_index=True)

    st.markdown("#### Trade Journal")
    journal = trade_journal(state)
    if journal.empty:
        st.caption("The trade journal is empty.")
    else:
        journal_columns = [
            "entry_date", "exit_date", "ticker", "setup", "status", "score",
            "market_regime", "entry_price", "exit_price", "quantity",
            "net_pnl", "return_pct", "exit_reason",
        ]
        journal_view = journal[[c for c in journal_columns if c in journal.columns]].copy()
        st.dataframe(journal_view, use_container_width=True, hide_index=True)
        st.download_button(
            "Download full trade journal CSV",
            journal.to_csv(index=False).encode("utf-8"),
            "catalyst_paper_trading_journal.csv",
            "text/csv",
            use_container_width=True,
        )

    with st.expander("Trial administration"):
        st.warning("Resetting permanently clears the current paper-trading trial.")
        confirm = st.checkbox("I understand the current simulation will be deleted")
        if st.button("Reset Paper-Trading Trial", disabled=not confirm):
            clear_paper_state()
            st.rerun()

    if not state.get("daily_runs"):
        empty_state(
            "Ready for Day 1",
            "Run the Daily Routine or Market Scan, then press Run Today's Paper Trades.",
            "🧪",
        )
