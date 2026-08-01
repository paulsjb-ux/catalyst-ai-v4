from __future__ import annotations

import pandas as pd
import streamlit as st

from data.market_data import download_history
from engine.backtest import run_backtest
from engine.backtest_analysis import ticker_performance
from engine.confidence_calibration import calibration_summary
from ui.components import empty_state, section_header, status_card


DEFAULT_TICKERS = "AAPL,MSFT,NVDA,AMZN,META,GOOGL,AVGO,LLY,JPM,COST"


def render_backtesting() -> None:
    section_header(
        "Historical Backtesting",
        "Test the existing Catalyst scoring rules using next-day entries and "
        "strict no-look-ahead assumptions.",
    )

    status_card(
        "Backtests are research tools, not forecasts. Results exclude taxes, "
        "slippage beyond the selected transaction cost, and portfolio-capital constraints.",
        "info",
    )

    tickers_raw = st.text_area(
        "Tickers",
        value=DEFAULT_TICKERS,
        height=100,
        help="Use a focused set first. Large historical downloads can take time.",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        period = st.selectbox("History", ["2y", "5y", "10y"], index=1)
    with c2:
        holding_days = st.number_input(
            "Maximum holding days",
            min_value=2,
            max_value=120,
            value=20,
            step=1,
        )
    with c3:
        minimum_score = st.number_input(
            "Minimum strategy score",
            min_value=55,
            max_value=100,
            value=78,
            step=1,
        )

    c1, c2, c3 = st.columns(3)
    with c1:
        use_target_stop = st.toggle("Use ATR target and stop", value=True)
        adaptive_risk = st.toggle(
            "Adaptive exits and sizing",
            value=True,
            help="Uses only signal-date score, momentum and volatility.",
        )
        walk_forward_calibration = st.toggle(
            "Walk-forward confidence calibration",
            value=True,
            help=(
                "FULL size requires evidence from trades that closed before "
                "each new trade. No future trades are used."
            ),
        )
    with c2:
        transaction_cost = st.number_input(
            "Round-trip cost (%)",
            min_value=0.0,
            max_value=5.0,
            value=0.10,
            step=0.05,
            format="%.2f",
        )
    with c3:
        include_watch = st.toggle("Include WATCH signals", value=False)
        base_position_pct = st.number_input(
            "Base position size (%)",
            min_value=2.5,
            max_value=50.0,
            value=20.0,
            step=2.5,
        )
        minimum_evidence_trades = st.number_input(
            "Evidence trades before FULL size",
            min_value=5,
            max_value=100,
            value=20,
            step=5,
        )

    run_clicked = st.button(
        "Run Historical Backtest",
        type="primary",
        use_container_width=True,
    )

    if run_clicked:
        tickers = list(
            dict.fromkeys(
                token.strip().upper()
                for token in tickers_raw.replace("\n", ",").split(",")
                if token.strip()
            )
        )
        st.session_state.pop("backtest_run_error", None)
        st.session_state.pop("backtest_run_summary", None)

        if not tickers:
            st.session_state["backtest_run_error"] = (
                "Enter at least one ticker before running the backtest."
            )
        else:
            progress = st.progress(0, text="Preparing historical backtest...")
            try:
                progress.progress(10, text="Downloading historical prices...")
                market = download_history(
                    tickers,
                    period=period,
                    cache_minutes=60,
                )

                loaded = len(market.prices)
                failed = len(market.errors)
                stale = getattr(market, "stale_cache_hits", 0)
                st.session_state["backtest_run_summary"] = {
                    "requested": len(tickers),
                    "loaded": loaded,
                    "failed": failed,
                    "cache_hits": market.cache_hits,
                    "stale_cache_hits": stale,
                }

                if loaded == 0:
                    details = "; ".join(
                        f"{ticker}: {message}"
                        for ticker, message in list(market.errors.items())[:5]
                    )
                    raise RuntimeError(
                        "No historical price data loaded. "
                        + (details or "The market-data provider returned no usable data.")
                    )

                progress.progress(45, text=f"Testing {loaded} loaded symbols...")
                signals = ("BUY", "WATCH") if include_watch else ("BUY",)
                result = run_backtest(
                    market.prices,
                    holding_days=int(holding_days),
                    minimum_score=int(minimum_score),
                    signals=signals,
                    use_target_stop=use_target_stop,
                    transaction_cost_pct=float(transaction_cost),
                    adaptive_risk=adaptive_risk,
                    base_position_pct=float(base_position_pct),
                    walk_forward_calibration=walk_forward_calibration,
                    minimum_evidence_trades=int(minimum_evidence_trades),
                )
                result.errors.update(market.errors)
                progress.progress(90, text="Calculating portfolio metrics...")

                # Store a completed result only after the full run succeeds.
                st.session_state["backtest_result"] = result
                progress.progress(100, text="Backtest complete")
                st.success(
                    f"Backtest complete: {loaded}/{len(tickers)} symbols loaded, "
                    f"{result.metrics.get('trades', 0)} trades generated."
                )
            except Exception as exc:
                st.session_state["backtest_run_error"] = str(exc)
                progress.empty()

    run_error = st.session_state.get("backtest_run_error")
    if run_error:
        st.error(f"Backtest could not run: {run_error}")

    run_summary = st.session_state.get("backtest_run_summary")
    if run_summary:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Requested", run_summary.get("requested", 0))
        c2.metric("Price Data Loaded", run_summary.get("loaded", 0))
        c3.metric("Data Failures", run_summary.get("failed", 0))
        c4.metric(
            "Cache Fallbacks",
            run_summary.get("stale_cache_hits", 0),
        )

    result = st.session_state.get("backtest_result")
    if result is None:
        empty_state(
            "No backtest yet",
            "Choose a focused ticker set and run the historical test.",
            "🧪",
        )
        return

    metrics = result.metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trades", metrics.get("trades", 0))
    c2.metric("Win Rate", f"{metrics.get('win_rate_pct', 0)}%")
    c3.metric("Average Trade", f"{metrics.get('average_return_pct', 0)}%")
    c4.metric("Profit Factor", metrics.get("profit_factor", 0))

    st.markdown("### Walk-Forward Calibrated Portfolio")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Calibrated Return",
        f"{metrics.get('calibrated_compounded_return_pct', 0)}%",
    )
    c2.metric(
        "Calibrated Drawdown",
        f"{metrics.get('calibrated_max_drawdown_pct', 0)}%",
    )
    c3.metric(
        "Average Calibrated Position",
        f"{metrics.get('average_calibrated_position_size_pct', 0)}%",
    )
    c4.metric("Average Hold", f"{metrics.get('average_holding_days', 0)} days")

    with st.expander("Raw and adaptive comparison"):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(
            "Raw Return",
            f"{metrics.get('compounded_return_pct', 0)}%",
        )
        c2.metric(
            "Raw Drawdown",
            f"{metrics.get('max_drawdown_pct', 0)}%",
        )
        c3.metric(
            "Adaptive Return",
            f"{metrics.get('portfolio_compounded_return_pct', 0)}%",
        )
        c4.metric(
            "Adaptive Drawdown",
            f"{metrics.get('portfolio_max_drawdown_pct', 0)}%",
        )

    if not result.equity_curve.empty:
        st.markdown("### Compounded Trade Equity")
        curve = result.equity_curve.set_index("trade_number")
        chart_columns = [
            c
            for c in ["calibrated_equity", "portfolio_equity", "equity"]
            if c in curve.columns
        ]
        st.line_chart(curve[chart_columns], height=320)

    if result.trades.empty:
        diagnostic = result.diagnostics or {}
        bars = diagnostic.get("bars_evaluated", 0)
        buys = diagnostic.get("buy_signals", 0)
        watches = diagnostic.get("watch_signals", 0)
        qualifying_scores = diagnostic.get(
            "scores_at_or_above_minimum",
            0,
        )
        maximum_score = diagnostic.get("maximum_score", 0)

        status_card(
            "No historical entries qualified. "
            f"{bars:,} bars were evaluated, producing {buys:,} BUY and "
            f"{watches:,} WATCH signals. "
            f"{qualifying_scores:,} bars reached the selected score; "
            f"the highest score was {maximum_score}.",
            "warning",
        )

        by_ticker = pd.DataFrame(diagnostic.get("by_ticker", []))
        if not by_ticker.empty:
            st.markdown("### Signal Diagnostics")
            diagnostic_columns = [
                "ticker",
                "price_rows",
                "bars_evaluated",
                "buy_signals",
                "watch_signals",
                "scores_at_or_above_minimum",
                "maximum_score",
                "accepted_entries",
                "error",
            ]
            st.dataframe(
                by_ticker[
                    [
                        column
                        for column in diagnostic_columns
                        if column in by_ticker.columns
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                height=320,
            )
    else:
        evidence = calibration_summary(result.trades)
        if not evidence.empty:
            st.markdown("### Confidence Evidence")
            st.caption(
                "Each trade is sized using only earlier closed trades from "
                "the same score band and original risk label."
            )
            st.dataframe(
                evidence,
                use_container_width=True,
                hide_index=True,
                height=240,
            )

        performance = ticker_performance(result.trades)
        if not performance.empty:
            st.markdown("### Ticker Performance")
            st.caption("Diagnostic only; not used to remove historical trades.")
            st.dataframe(performance, use_container_width=True, hide_index=True, height=300)

        st.markdown("### Historical Trades")
        st.dataframe(
            result.trades.sort_values(
                ["entry_date", "ticker"],
                ascending=[False, True],
            ),
            use_container_width=True,
            hide_index=True,
            height=430,
        )
        st.download_button(
            "Download backtest trades CSV",
            result.trades.to_csv(index=False).encode("utf-8"),
            file_name="catalyst_backtest_trades.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("Backtest assumptions"):
        st.json(result.assumptions)

    if result.errors:
        with st.expander(f"Data errors ({len(result.errors)})"):
            st.json(result.errors)
