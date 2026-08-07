from __future__ import annotations

import pandas as pd
import streamlit as st

from data.paper_store import load_paper_state
from data.release_candidate_store import active_recommendations, load_run_history, recommendation_history
from engine.paper_trading import trades_frame
from engine.release_candidate import build_release_candidate_pdf, export_trade_history_csv, portfolio_snapshot
from ui.components import empty_state, section_header, status_card
from version import APP_VERSION


def _money(value) -> str:
    try:
        return f"£{float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"


def render_portfolio() -> None:
    section_header("Portfolio & Performance", "Persistent paper portfolio, trade history and release-candidate evidence.")
    state = load_paper_state()
    if not isinstance(state, dict):
        status_card("No paper portfolio is active yet. Start the 30-day trial under Trading Tools → Paper Trading.", "info")
        active = active_recommendations()
        if not active.empty:
            st.markdown("### Active recommendations")
            st.dataframe(active[[c for c in ["ticker","action","score","swing_status","entry_price","target_price","stop_loss","risk_reward","expires_date"] if c in active.columns]], use_container_width=True, hide_index=True)
        return

    snapshot = portfolio_snapshot(state)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Portfolio", _money(snapshot.get("equity")))
    c2.metric("Net P&L", _money(snapshot.get("net_pnl")), f"{float(snapshot.get('return_pct',0)):.2f}%")
    c3.metric("Win Rate", f"{float(snapshot.get('win_rate_pct',0)):.1f}%")
    c4.metric("Expectancy", _money(snapshot.get("expectancy")))
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Cash", _money(snapshot.get("cash")))
    d2.metric("Market Value", _money(snapshot.get("market_value")))
    d3.metric("Open / Closed", f"{int(snapshot.get('open_trades',0))} / {int(snapshot.get('closed_trades',0))}")
    d4.metric("Max Drawdown", f"{float(snapshot.get('max_drawdown_pct',0)):.2f}%")

    equity = pd.DataFrame(state.get("equity_history", []))
    if not equity.empty and {"date","equity"}.issubset(equity.columns):
        st.markdown("### Equity curve")
        st.line_chart(equity.drop_duplicates("date", keep="last").set_index("date")[["equity"]])

    open_trades = trades_frame(state, "OPEN")
    st.markdown("### Open positions")
    if open_trades.empty:
        st.caption("No open paper positions.")
    else:
        cols = [c for c in ["ticker","setup","entry_date","entry_price","quantity","last_price","unrealised_pnl","unrealised_return_pct","target_price","stop_price","days_held"] if c in open_trades.columns]
        st.dataframe(open_trades[cols], use_container_width=True, hide_index=True)

    active = active_recommendations()
    st.markdown("### Active recommendations")
    if active.empty:
        st.caption("No unexpired recommendations are recorded yet. Run the Daily Routine on v14.5 to begin the lifecycle log.")
    else:
        cols = [c for c in ["daily_rank","ticker","action","score","swing_status","position_size_pct","entry_price","target_price","stop_loss","risk_reward","recommended_date","expires_date"] if c in active.columns]
        st.dataframe(active[cols], use_container_width=True, hide_index=True)
        st.caption("Recommendations expire automatically after 3 trading days unless refreshed by a newer routine run.")

    st.markdown("### Performance evidence")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Completed Trades", int(snapshot.get("closed_trades",0)))
    wins = int(snapshot.get("wins",0)); losses = int(snapshot.get("losses",0))
    e2.metric("Wins / Losses", f"{wins} / {losses}")
    e3.metric("Profit Factor", snapshot.get("profit_factor", "—"))
    e4.metric("Days Run", int(snapshot.get("days_run",0)))

    history = load_run_history()
    if not history.empty:
        with st.expander("Persistent daily routine history"):
            st.dataframe(history.sort_values("finished_at", ascending=False), use_container_width=True, hide_index=True)

    closed = trades_frame(state, "CLOSED")
    all_trades = pd.concat([open_trades.assign(status="OPEN"), closed.assign(status="CLOSED")], ignore_index=True, sort=False) if (not open_trades.empty or not closed.empty) else pd.DataFrame()
    rec_history = recommendation_history()
    try:
        pdf = build_release_candidate_pdf(version=APP_VERSION, portfolio=snapshot, run_history=history,
                                          recommendations=active, trades=all_trades)
        x1, x2 = st.columns(2)
        x1.download_button("Download full trade history CSV", export_trade_history_csv(state), "catalyst_v14_5_trade_history.csv", "text/csv", use_container_width=True)
        x2.download_button("Download release-candidate PDF", pdf, "catalyst_v14_5_release_candidate_report.pdf", "application/pdf", use_container_width=True)
    except RuntimeError as exc:
        st.warning(str(exc))

    with st.expander("Recommendation lifecycle history"):
        if rec_history.empty:
            empty_state("No lifecycle history", "Run Daily Routine once on v14.5 to start it.", "📋")
        else:
            st.dataframe(rec_history, use_container_width=True, hide_index=True)
