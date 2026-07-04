import streamlit as st

from config import CONFIG
from data.health import health_summary
from ui.components import section_header, status_card

def render_settings(version: str) -> None:
    section_header("Settings", "Application configuration, health checks and product guardrails.")
    status = health_summary()

    if status["files_ok"] and status["packages_ok"]:
        status_card("Catalyst AI v4 health check passed.", "positive")
    else:
        status_card("Health check found missing items. See details below.", "warning")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files OK", "Yes" if status["files_ok"] else "No")
    c2.metric("Packages OK", "Yes" if status["packages_ok"] else "No")
    c3.metric("Missing Files", len(status["missing_files"]))
    c4.metric("Missing Packages", len(status["missing_packages"]))

    st.markdown("### Application")
    st.write("**Application:**", CONFIG.app_name)
    st.write("**Version:**", version)
    st.write("**Engine:**", CONFIG.engine_name)
    st.write("**Default universe cap:**", CONFIG.max_default_tickers)

    with st.expander("Health check details"):
        st.json(status)

    st.markdown("### Guardrails")
    st.write("- No Portfolio page in the v4 foundation.")
    st.write("- No current holdings loaded by default.")
    st.write("- No Trading 212 legacy dependency.")
    st.write("- Market intelligence remains separate from holdings.")
    st.write("- Signals are decision-support only, not financial advice.")
