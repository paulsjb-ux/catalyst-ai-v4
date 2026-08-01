from __future__ import annotations

from importlib import import_module
from typing import Callable
import uuid

import pandas as pd
import streamlit as st

from config import CONFIG
from logging_config import configure_logging
from ui.components import render_header, top_navigation
from ui.theme import apply_theme
from version import APP_VERSION

logger = configure_logging()

ROUTES: dict[str, tuple[str, str]] = {
    "Today’s Decision": ("ui.todays_decision", "render_todays_decision"),
    "Daily Routine": ("ui.daily_routine", "render_daily_routine"),
    "Dashboard": ("ui.dashboard", "render_dashboard"),
    "Daily Brief": ("ui.daily_brief", "render_daily_brief"),
    "Alerts": ("ui.alerts", "render_alerts"),
    "Market Scan": ("ui.market_scan", "render_market_scan"),
    "Paper Trading": ("ui.paper_trading", "render_paper_trading"),
    "Backtesting": ("ui.backtesting", "render_backtesting"),
    "Trade Universe": ("ui.trade_universe", "render_trade_universe"),
    "Watchlist": ("ui.watchlist", "render_watchlist"),
    "Validation": ("ui.validation", "render_validation"),
    "Repeat Winners": ("ui.repeat_winners", "render_repeat_winners"),
    "Reports": ("ui.reports", "render_reports"),
    "Settings": ("ui.settings", "render_settings"),
}


def _load_renderer(page: str) -> Callable:
    module_name, function_name = ROUTES[page]
    renderer = getattr(import_module(module_name), function_name, None)
    if not callable(renderer):
        raise AttributeError(f"Renderer {function_name!r} not found in {module_name!r}")
    return renderer


def route_page(page: str) -> None:
    if page not in ROUTES:
        logger.warning("Unknown route requested: %s", page)
        st.error("That page is not available. Please choose another page.")
        return
    try:
        renderer = _load_renderer(page)
        if page == "Dashboard":
            renderer(APP_VERSION, st.session_state.get("scan_results", pd.DataFrame()))
        elif page == "Settings":
            renderer(APP_VERSION)
        else:
            renderer()
    except Exception:
        reference = uuid.uuid4().hex[:8]
        logger.exception("Page render failed [%s] page=%s", reference, page)
        st.error(f"{page} could not be loaded. Reference: {reference}. The rest of Catalyst remains available.")


def main() -> None:
    st.set_page_config(page_title=CONFIG.app_name, page_icon=CONFIG.page_icon, layout=CONFIG.layout, initial_sidebar_state="collapsed")
    apply_theme()
    page = top_navigation()
    if page != "Daily Routine":
        render_header(CONFIG.app_name, CONFIG.tagline, CONFIG.engine_name, APP_VERSION)
    route_page(page)


if __name__ == "__main__":
    main()
