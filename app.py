import pandas as pd
import streamlit as st

from config import CONFIG
from logging_config import configure_logging
from ui.components import render_header, top_navigation
from ui.alerts import render_alerts
from ui.dashboard import render_dashboard
from ui.daily_brief import render_daily_brief
from ui.market_scan import render_market_scan
from ui.reports import render_reports
from ui.repeat_winners import render_repeat_winners
from ui.settings import render_settings
from ui.theme import apply_theme
from ui.trade_universe import render_trade_universe
from ui.validation import render_validation
from ui.watchlist import render_watchlist
from version import APP_VERSION

logger = configure_logging()


def route_page(page: str) -> None:
    routes = {
        "Dashboard": lambda: render_dashboard(APP_VERSION, st.session_state.get("scan_results", pd.DataFrame())),
        "Daily Brief": render_daily_brief,
        "Alerts": render_alerts,
        "Market Scan": render_market_scan,
        "Trade Universe": render_trade_universe,
        "Watchlist": render_watchlist,
        "Validation": render_validation,
        "Repeat Winners": render_repeat_winners,
        "Reports": render_reports,
        "Settings": lambda: render_settings(APP_VERSION),
    }
    renderer = routes.get(page)
    if renderer is None:
        st.error(f"Unknown page: {page}")
        return
    renderer()


def main() -> None:
    st.set_page_config(page_title=CONFIG.app_name, page_icon=CONFIG.page_icon, layout=CONFIG.layout, initial_sidebar_state="collapsed")
    apply_theme()
    render_header(CONFIG.app_name, CONFIG.tagline, CONFIG.engine_name, APP_VERSION)
    route_page(top_navigation())


if __name__ == "__main__":
    main()
