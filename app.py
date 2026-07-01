from __future__ import annotations

import streamlit as st

from config import CONFIG
from logging_config import configure_logging
from version import APP_VERSION

logger = configure_logging()

HOLDINGS_ENABLED = False
CURRENT_HOLDINGS = []

def apply_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg,#f8fbff 0%,#eef7ff 70%,#ffffff 100%);
            color: #0f172a;
        }
        .block-container {
            max-width: 1180px;
            padding-top: 1rem;
        }
        .hero {
            background: linear-gradient(135deg,#ffffff,#eff6ff);
            border: 1px solid #bfdbfe;
            border-radius: 28px;
            padding: 24px;
            box-shadow: 0 18px 42px rgba(15,23,42,.08);
            margin-bottom: 18px;
        }
        .hero h1 {
            font-size: clamp(2.4rem, 5vw, 4.5rem);
            letter-spacing: -.07em;
            margin: 0;
        }
        .hero p {
            color: #475569;
            font-size: 1.05rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_header() -> None:
    st.markdown(
        f"""
        <div class="hero">
            <h1>🚀 {CONFIG.app_name}</h1>
            <p><strong>{CONFIG.tagline}</strong><br>
            Powered by the {CONFIG.engine_name}</p>
            <p>Version {APP_VERSION}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_navigation() -> str:
    return st.radio(
        "Navigation",
        ["Dashboard", "Market Scan", "Trade Universe", "Validation", "Repeat Winners", "Settings"],
        horizontal=True,
        label_visibility="collapsed",
    )

def render_dashboard() -> None:
    st.subheader("Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Universe", "Not loaded")
    c2.metric("BUY", "—")
    c3.metric("WATCH", "—")
    c4.metric("Version", APP_VERSION)
    st.info("Sprint 1 Part 1 foundation is running. Trading engine modules are added in later parts.")

def render_placeholder(page: str) -> None:
    st.subheader(page)
    st.warning("This page is part of the v4 foundation and will be connected in Sprint 1 Parts 2–5.")

def render_settings() -> None:
    st.subheader("Settings")
    st.success("Catalyst AI v4 foundation is deployed.")
    st.write("Holdings enabled:", CONFIG.holdings_enabled)
    st.write("Max default tickers:", CONFIG.max_default_tickers)
    st.write("No Portfolio and no current holdings are loaded by default.")

def main() -> None:
    st.set_page_config(
        page_title=CONFIG.app_name,
        page_icon=CONFIG.page_icon,
        layout=CONFIG.layout,
        initial_sidebar_state="collapsed",
    )
    apply_theme()
    render_header()
    page = render_navigation()

    if page == "Dashboard":
        render_dashboard()
    elif page == "Settings":
        render_settings()
    else:
        render_placeholder(page)

if __name__ == "__main__":
    main()
