import pandas as pd
import streamlit as st

from data.history_store import compare_scans, load_previous_scan, save_scan
from data.market_data import download_history
from data.universe import get_default_universe, normalise_tickers
from engine.market_regime import REGIME_TICKERS, build_market_regime
from engine.scanner import run_scan
from engine.trade_plans import build_trade_plans, filter_trade_plan_candidates
from engine.universe_builder import build_scan_universe
from ui.components import empty_state, section_header, status_card


DISPLAY_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "base_score",
    "market_adjustment",
    "close",
    "change_1d_pct",
    "change_20d_pct",
    "change_60d_pct",
    "rsi_14",
    "volume_ratio",
    "volatility_20d_pct",
    "trend",
    "reason",
]

SCORE_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "base_score",
    "market_regime",
    "market_adjustment",
    "trend_score",
    "momentum_score",
    "volume_score",
    "relative_strength_score",
    "volatility_penalty",
    "extension_penalty",
    "reason",
]

PLAN_COLUMNS = [
    "ticker",
    "signal",
    "score",
    "entry_price",
    "target_price",
    "stop_loss",
    "risk_pct",
    "reward_pct",
    "risk_reward",
    "position_quality",
    "plan_reason",
]

UNIVERSE_VERSION = "global-323"
DEFAULT_MAX_TICKERS = 323


def _build_default_universe() -> list[str]:
    """Build the expanded liquid-market universe with a safe fallback."""
    tickers = build_scan_universe(
        include_sp500=True,
        include_nasdaq100=True,
        include_global_liquid=True,
        include_watchlist=True,
        include_starter_large_universe=True,
        max_tickers=DEFAULT_MAX_TICKERS,
    )
    return tickers or get_default_universe()


def _initialise_ticker_input() -> None:
    """Replace the old 80-symbol default once, without overwriting later edits."""
    if st.session_state.get("market_scan_universe_version") == UNIVERSE_VERSION:
        return

    default_universe = _build_default_universe()
    st.session_state["ticker_input"] = ",".join(default_universe)
    st.session_state["market_scan_universe_version"] = UNIVERSE_VERSION


def render_market_scan() -> None:
    section_header(
        "Market Scan",
        "Smarter BUY, WATCH and IGNORE scoring with market regime awareness.",
    )

    _initialise_ticker_input()

    default_universe = _build_default_universe()
    default_text = ",".join(default_universe)

    c1, c2 = st.columns([3, 1])
    with c1:
        st.caption(
            f"Expanded liquid-market universe: up to {DEFAULT_MAX_TICKERS} symbols."
        )
    with c2:
        if st.button("Reset to global universe", use_container_width=True):
            st.session_state["ticker_input"] = default_text
            st.rerun()

    tickers_raw = st.text_area(
        "Tickers",
        value=st.session_state.get("ticker_input", default_text),
        height=140,
        help=(
            "The expanded universe includes liquid US and international shares "
            "plus major ETFs. SPY and QQQ are added automatically for regime context."
        ),
    )
    st.session_state["ticker_input"] = tickers_raw

    selected_tickers = normalise_tickers(tickers_raw)
    st.caption(f"{len(selected_tickers)} unique symbols currently selected.")

    c1, c2, c3 = st.columns(3)
    with c1:
        period = st.selectbox("History", ["6mo", "1y", "2y"], index=1)
    with c2:
        minimum_score = st.slider("Minimum displayed score", 0, 100, 50)
    with c3:
        signal_filter = st.selectbox(
            "Signal",
            ["BUY & WATCH", "All", "BUY", "WATCH", "IGNORE"],
        )

    include_regime = st.toggle(
        "Apply SPY/QQQ market regime adjustment",
        value=True,
    )

    if st.button("Run Market Scan", type="primary", use_container_width=True):
        tickers = normalise_tickers(tickers_raw)

        if not tickers:
            st.error("Enter at least one ticker.")
        else:
            download_tickers = tickers.copy()
            for regime_ticker in REGIME_TICKERS:
                if regime_ticker not in download_tickers:
                    download_tickers.append(regime_ticker)

            with st.spinner(
                f"Downloading, analysing and planning {len(tickers)} symbols..."
            ):
                market = download_history(download_tickers, period=period)
                regime = (
                    build_market_regime(market.prices)
                    if include_regime
                    else None
                )
                results = run_scan(
                    market.prices,
                    market_regime=regime,
                )
                plans = build_trade_plans(
                    filter_trade_plan_candidates(results),
                    market.prices,
                )
                saved = save_scan(results)

                st.session_state["scan_results"] = results
                st.session_state["trade_plans"] = plans
                st.session_state["market_regime"] = regime
                st.session_state["scan_errors"] = market.errors
                st.session_state["scan_id"] = saved.scan_id if saved else ""

                if saved:
                    previous = load_previous_scan(saved.scan_id)
                    st.session_state["scan_comparison"] = compare_scans(
                        results,
                        previous,
                    )

    frame = st.session_state.get("scan_results", pd.DataFrame())
    plans = st.session_state.get("trade_plans", pd.DataFrame())
    regime = st.session_state.get("market_regime")
    errors = st.session_state.get("scan_errors", {})
    comparison = st.session_state.get("scan_comparison", pd.DataFrame())

    if frame is None or frame.empty:
        empty_state(
            "No scan results yet",
            "Press Run Market Scan to download prices, score the universe and build target/stop plans.",
            "🔎",
        )
        return

    if regime:
        st.markdown("### Market Regime")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Regime", regime.get("regime", "UNKNOWN"))
        c2.metric("Market Score", regime.get("market_score", 0))
        c3.metric("Adjustment", regime.get("regime_adjustment", 0))
        c4.metric("Risk Label", regime.get("risk_label", "UNKNOWN"))
        status_card(
            regime.get("reason", "No market regime reason available."),
            "info",
        )
        with st.expander("SPY / QQQ detail"):
            st.dataframe(
                pd.DataFrame(regime.get("indices", [])),
                use_container_width=True,
                hide_index=True,
            )

    filtered = frame[frame["score"] >= minimum_score].copy()

    if signal_filter == "BUY & WATCH":
        filtered = filtered[filtered["signal"].isin(["BUY", "WATCH"])]
    elif signal_filter != "All":
        filtered = filtered[filtered["signal"] == signal_filter]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Scanned", len(frame))
    c2.metric("BUY", int((frame["signal"] == "BUY").sum()))
    c3.metric("WATCH", int((frame["signal"] == "WATCH").sum()))
    c4.metric("Trade Plans", len(plans) if plans is not None else 0)

    scan_id = st.session_state.get("scan_id", "")
    if scan_id:
        status_card(f"Scan saved as {scan_id}.", "positive")

    visible_errors = {
        ticker: error
        for ticker, error in errors.items()
        if ticker not in REGIME_TICKERS
    }
    if visible_errors:
        status_card(
            f"{len(visible_errors)} symbols could not be loaded. "
            "The rest of the scan completed.",
            "warning",
        )
        with st.expander("View data errors"):
            st.json(visible_errors)

    if comparison is not None and not comparison.empty:
        with st.expander("Compare with previous scan"):
            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
            )

    if filtered.empty:
        empty_state(
            "No matches",
            "Adjust the score or signal filters.",
            "🛡️",
        )
        return

    st.markdown("### Candidate Results")
    st.dataframe(
        filtered[[column for column in DISPLAY_COLUMNS if column in filtered.columns]],
        use_container_width=True,
        hide_index=True,
        height=420,
    )

    st.markdown("### Scoring Breakdown")
    st.dataframe(
        filtered[[column for column in SCORE_COLUMNS if column in filtered.columns]],
        use_container_width=True,
        hide_index=True,
        height=360,
    )

    if plans is not None and not plans.empty:
        st.markdown("### Target & Stop Plans")
        visible_plans = plans.copy()

        if signal_filter == "BUY & WATCH":
            visible_plans = visible_plans[
                visible_plans["signal"].isin(["BUY", "WATCH"])
            ]
        elif signal_filter != "All":
            visible_plans = visible_plans[
                visible_plans["signal"] == signal_filter
            ]

        st.dataframe(
            visible_plans[
                [column for column in PLAN_COLUMNS if column in visible_plans.columns]
            ],
            use_container_width=True,
            hide_index=True,
            height=420,
        )
        st.download_button(
            "Download trade plans CSV",
            visible_plans.to_csv(index=False).encode("utf-8"),
            file_name="catalyst_trade_plans.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.download_button(
        "Download scan CSV",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="catalyst_scan.csv",
        mime="text/csv",
        use_container_width=True,
    )
