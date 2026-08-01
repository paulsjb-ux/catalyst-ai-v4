import json

import streamlit as st

from config import CONFIG
from data.cloud_store import health_check
from data.health import health_summary
from data.storage_admin import (
    backup_all,
    load_backup_file,
    migrate_local_to_cloud,
    restore_backup,
    restore_latest_cloud_backup,
)
from data.diagnostics import diagnostic_bundle, recent_log_lines
from ui.action_helpers import run_ui_action
from ui.components import section_header, status_card
from ui.professional_tools import render_professional_tools


def render_settings(version: str) -> None:
    section_header("Settings", "Application configuration, health checks and persistent storage.")
    status = health_summary()
    storage = health_check()

    if status["files_ok"] and status["packages_ok"]:
        status_card("Catalyst AI application health check passed.", "positive")
    else:
        status_card("Health check found missing items. See details below.", "warning")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Files OK", "Yes" if status["files_ok"] else "No")
    c2.metric("Packages OK", "Yes" if status["packages_ok"] else "No")
    c3.metric("Storage", storage["backend"])
    c4.metric("Cloud Ready", "Yes" if storage["table_ready"] else "No")

    st.markdown("### Application")
    st.write("**Application:**", CONFIG.app_name)
    st.write("**Version:**", version)
    st.write("**Engine:**", CONFIG.engine_name)
    st.write("**Default universe cap:**", CONFIG.max_default_tickers)

    st.markdown("### Persistent Storage")
    if storage["table_ready"]:
        status_card("Supabase cloud storage is connected and ready.", "positive")
    elif storage["configured"]:
        status_card(f"Cloud credentials found, but storage is unavailable: {storage['error']}", "warning")
    else:
        status_card("Cloud storage is not configured. Catalyst is using local fallback storage.", "info")

    with st.expander("Storage health details"):
        st.json(storage)

    st.caption("Configure SUPABASE_URL plus SUPABASE_KEY (publishable) or SUPABASE_SECRET_KEY (server-side) in Streamlit secrets. Run the supplied SQL file once in Supabase.")

    c1, c2 = st.columns(2)

    if c1.button("Back up all data", width="stretch"):
        result = run_ui_action("Backup", backup_all, "Backup complete.")
        if result is not None:
            st.json(result)

    if c2.button("Migrate local data to cloud", width="stretch", disabled=not storage["table_ready"]):
        result = run_ui_action("Cloud migration", migrate_local_to_cloud, "Local data migrated to Supabase.")
        if result is not None:
            st.json(result)

    c3, c4 = st.columns(2)

    if c3.button("Restore latest cloud backup", width="stretch", disabled=not storage["table_ready"]):
        result = run_ui_action("Cloud restore", restore_latest_cloud_backup, "Latest cloud backup restored.")
        if result is not None:
            st.json(result)

    uploaded = c4.file_uploader("Restore JSON backup", type=["json"])
    if uploaded is not None and st.button("Restore uploaded backup", width="stretch"):
        result = run_ui_action(
            "Uploaded backup restore",
            lambda: restore_backup(load_backup_file(uploaded)),
            "Uploaded backup restored.",
        )
        if result is not None:
            st.json(result)

    with st.expander("Application health details"):
        st.json(status)

    st.markdown("### Diagnostics")
    with st.expander("Recent application log"):
        lines = recent_log_lines(150)
        st.code("\n".join(lines) if lines else "No log entries available.", language="text")
    st.download_button(
        "Download diagnostic log",
        data=diagnostic_bundle(),
        file_name="catalyst-diagnostics.log",
        mime="text/plain",
        width="stretch",
    )

    st.markdown("### Professional Finish")
    render_professional_tools(version)

    st.markdown("### Guardrails")
    st.write("- Persistent data uses Supabase when configured.")
    st.write("- A local fallback copy is retained automatically.")
    st.write("- Cloud migration is explicit and reversible through backups.")
    st.write("- Signals remain decision-support only, not financial advice.")
