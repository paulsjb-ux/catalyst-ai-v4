from __future__ import annotations

from importlib import import_module
from typing import Callable

import pandas as pd
import streamlit as st

from config import CONFIG
from logging_config import configure_logging
from ui.components import render_header, top_navigation
from ui.theme import apply_theme
from version import APP_VERSION

logger = configure_logging()


# Page modules are imported only when selected. This reduces cold-start work and
# prevents optional page dependencies from slowing or breaking unrelated pages.
_PAGE_ROUTES: dict[str, tuple[str, str]] = {
    "Today’s Decision": ("ui.todays_decision", "render_todays_decision"),
    "Daily Routine": ("ui.daily_routine", "render_daily_routine"),
    "Daily Brief": ("ui.daily_brief", "render_daily_brief"),
    "Alerts": ("ui.alerts", "render_alerts"),
    "Market Scan": ("ui.market_scan", "render_market_scan"),
    "Paper Trading": ("ui.paper_trading", "render_paper_trading"),
    "Trade Universe": ("ui.trade_universe", "render_trade_universe"),
    "Watchlist": ("ui.watchlist", "render_watchlist"),
    "Validation": ("ui.validation", "render_validation"),
    "Repeat Winners": ("ui.repeat_winners", "render_repeat_winners"),
    "Reports": ("ui.reports", "render_reports"),
}


def _load_renderer(module_name: str, function_name: str) -> Callable[[], None]:
    module = import_module(module_name)
    return getattr(module, function_name)


def route_page(page: str) -> None:
    try:
        if page == "Dashboard":
            renderer = _load_renderer("ui.dashboard", "render_dashboard")
            renderer(APP_VERSION, st.session_state.get("scan_results", pd.DataFrame()))
            return
        if page == "Settings":
            renderer = _load_renderer("ui.settings", "render_settings")
            renderer(APP_VERSION)
            return
        route = _PAGE_ROUTES.get(page)
        if route is None:
            st.error(f"Unknown page: {page}")
            return
        _load_renderer(*route)()
    except Exception as exc:
        logger.exception("Page render failed: %s", page)
        st.error(f"{page} could not be loaded: {exc}")


def main() -> None:
    st.set_page_config(
        page_title=CONFIG.app_name,
        page_icon=CONFIG.page_icon,
        layout=CONFIG.layout,
        initial_sidebar_state="collapsed",
    )
    apply_theme()
    render_header(CONFIG.app_name, CONFIG.tagline, CONFIG.engine_name, APP_VERSION)
    route_page(top_navigation())


if __name__ == "__main__":
    main()
