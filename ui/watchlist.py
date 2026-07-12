import pandas as pd
import streamlit as st

from data.history_store import list_saved_scans, load_scan
from data.market_data import download_history
from data.watchlist_store import (
    add_or_update_item,
    clear_watchlist,
    import_watchlist_csv,
    load_watchlist,
    remove_item,
)
from engine.portfolio_monitor import build_portfolio_monitor, portfolio_summary
from ui.components import empty_state, section_header, status_card


MONITOR_COLUMNS = [
    "ticker",
    "quantity",
    "entry_price",
    "current_price",
    "change_1d_pct",
    "market_value",
    "unrealised_pnl",
    "unrealised_pnl_pct",
    "target_price",
    "distance_to_target_pct",
    "stop_loss",
    "distance_to_stop_pct",
    "latest_signal",
    "latest_score",
    "market_regime",
    "holding_status",
    "alerts",
    "notes",
]


def _latest_saved_scan() -> pd.DataFrame:
    scans = list_saved_scans()
    if scans is None or scans.empty:
        return pd.DataFrame()

    scan_id = str(scans.iloc[0]["scan_id"])
    return load_scan(scan_id)


def render_watchlist() -> None:
    section_header(
        "Watchlist & Portfolio",
        "Track ideas and holdings against live price, targets, stops, signals and market regime.",
    )

    with st.expander("Add or update ticker", expanded=False):
        c1, c2, c3 = st.columns(3)
        ticker = c1.text_input("Ticker", key="watchlist_ticker").upper().strip()
        quantity = c2.number_input("Quantity", min_value=0.0, value=0.0, step=1.0)
        entry_price = c3.number_input("Entry price", min_value=0.0, value=0.0, step=0.01)

        c4, c5 = st.columns(2)
        target_price = c4.number_input("Target price", min_value=0.0, value=0.0, step=0.01)
        stop_loss = c5.number_input("Stop loss", min_value=0.0, value=0.0, step=0.01)
        notes = st.text_input("Notes")

        if st.button("Save ticker", type="primary", use_container_width=True):
            if not ticker:
                st.error("Enter a ticker.")
            else:
                add_or_update_item(
                    ticker=ticker,
                    quantity=quantity,
                    entry_price=entry_price or None,
                    target_price=target_price or None,
                    stop_loss=stop_loss or None,
                    notes=notes,
                )
                st.success(f"{ticker} saved.")
                st.rerun()

    with st.expander("Import CSV", expanded=False):
        st.caption("Supported columns include ticker/symbol, quantity/shares, entry_price/average_price, target_price, stop_loss and notes.")
        uploaded = st.file_uploader("Upload watchlist or portfolio CSV", type=["csv"], key="watchlist_upload")
        if uploaded is not None and st.button("Import CSV", use_container_width=True):
            import_watchlist_csv(uploaded)
            st.success("CSV imported.")
            st.rerun()

    watchlist = load_watchlist()

    if watchlist.empty:
        empty_state(
            "No watchlist yet",
            "Add a ticker manually or upload a CSV. Quantity can be zero for watch-only ideas.",
            "👀",
        )
        return

    tickers = watchlist["ticker"].dropna().astype(str).str.upper().unique().tolist()

    if st.button("Refresh live monitor", type="primary", use_container_width=True):
        with st.spinner(f"Refreshing {len(tickers)} tickers..."):
            market = download_history(tickers, period="6mo")
            monitor = build_portfolio_monitor(
                watchlist=watchlist,
                price_map=market.prices,
                latest_scan=st.session_state.get("scan_results", _latest_saved_scan()),
                market_regime=st.session_state.get("market_regime"),
            )
            st.session_state["portfolio_monitor"] = monitor
            st.session_state["portfolio_errors"] = market.errors

    monitor = st.session_state.get("portfolio_monitor", pd.DataFrame())
    errors = st.session_state.get("portfolio_errors", {})

    if monitor.empty:
        status_card("Press Refresh live monitor to download prices and calculate portfolio status.", "info")
        st.markdown("### Saved Watchlist")
        st.dataframe(watchlist, use_container_width=True, hide_index=True)
    else:
        summary = portfolio_summary(monitor)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Positions", summary["positions"])
        c2.metric("Invested", f"${summary['invested']:,.2f}")
        c3.metric("Market Value", f"${summary['market_value']:,.2f}")
        c4.metric("Unrealised P&L", f"${summary['unrealised_pnl']:,.2f}", f"{summary['unrealised_pnl_pct']:.2f}%")
        c5.metric("Alerts", summary["alerts"])

        if errors:
            status_card(f"{len(errors)} tickers could not be refreshed.", "warning")
            with st.expander("View refresh errors"):
                st.json(errors)

        alerts = monitor[monitor["alerts"] != "NONE"]
        if not alerts.empty:
            st.markdown("### Action Alerts")
            st.dataframe(
                alerts[["ticker", "current_price", "latest_signal", "holding_status", "alerts"]],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("### Live Monitor")
        st.dataframe(
            monitor[[column for column in MONITOR_COLUMNS if column in monitor.columns]],
            use_container_width=True,
            hide_index=True,
            height=520,
            column_config={
                "entry_price": st.column_config.NumberColumn("Entry", format="%.2f"),
                "current_price": st.column_config.NumberColumn("Current", format="%.2f"),
                "market_value": st.column_config.NumberColumn("Market Value", format="%.2f"),
                "unrealised_pnl": st.column_config.NumberColumn("P&L", format="%.2f"),
                "unrealised_pnl_pct": st.column_config.NumberColumn("P&L %", format="%.2f"),
                "target_price": st.column_config.NumberColumn("Target", format="%.2f"),
                "stop_loss": st.column_config.NumberColumn("Stop", format="%.2f"),
            },
        )

        st.download_button(
            "Download live monitor CSV",
            monitor.to_csv(index=False).encode("utf-8"),
            file_name="catalyst_watchlist_monitor.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("### Manage Watchlist")
    remove_ticker = st.selectbox("Select ticker to remove", watchlist["ticker"].tolist())
    c1, c2 = st.columns(2)

    if c1.button("Remove selected ticker", use_container_width=True):
        remove_item(remove_ticker)
        st.session_state.pop("portfolio_monitor", None)
        st.rerun()

    if c2.button("Clear entire watchlist", use_container_width=True):
        clear_watchlist()
        st.session_state.pop("portfolio_monitor", None)
        st.rerun()

    st.download_button(
        "Download saved watchlist CSV",
        watchlist.to_csv(index=False).encode("utf-8"),
        file_name="catalyst_watchlist.csv",
        mime="text/csv",
        use_container_width=True,
    )
