import streamlit as st
from config import CONFIG
from ui.components import section_header, status_card
def render_settings(version: str) -> None:
    section_header("Settings", "Application configuration and product guardrails.")
    status_card("Catalyst AI v4 UI package is active.", "positive")
    st.write("**Application:**", CONFIG.app_name)
    st.write("**Version:**", version)
    st.write("**Engine:**", CONFIG.engine_name)
    st.write("**Default universe cap:**", CONFIG.max_default_tickers)
    st.markdown("### Guardrails")
    st.write("- No Portfolio page in the v4 foundation.")
    st.write("- No current holdings loaded by default.")
    st.write("- No Trading 212 legacy dependency.")
