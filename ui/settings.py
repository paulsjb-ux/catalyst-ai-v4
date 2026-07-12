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
from ui.components import section_header, status_card


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

    st.caption("Configure SUPABASE_URL and SUPABASE_KEY in Streamlit secrets. Run the supplied SQL file once in Supabase.")

    c1, c2 = st.columns(2)

    if c1.button("Back up all data", width="stretch"):
        try:
            result = backup_all()
            st.success(
                f"Backup complete: {result['watchlist_count']} watchlist rows and "
                f"{result['scan_count']} scans."
            )
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    if c2.button("Migrate local data to cloud", width="stretch", disabled=not storage["table_ready"]):
        try:
            result = migrate_local_to_cloud()
            st.success("Local data migrated to Supabase.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    c3, c4 = st.columns(2)

    if c3.button("Restore latest cloud backup", width="stretch", disabled=not storage["table_ready"]):
        try:
            result = restore_latest_cloud_backup()
            st.success("Latest cloud backup restored.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    uploaded = c4.file_uploader("Restore JSON backup", type=["json"])
    if uploaded is not None and st.button("Restore uploaded backup", width="stretch"):
        try:
            payload = load_backup_file(uploaded)
            result = restore_backup(payload)
            st.success("Uploaded backup restored.")
            st.json(result)
        except Exception as exc:
            st.error(str(exc))

    with st.expander("Application health details"):
        st.json(status)

    st.markdown("### Guardrails")
    st.write("- Persistent data uses Supabase when configured.")
    st.write("- A local fallback copy is retained automatically.")
    st.write("- Cloud migration is explicit and reversible through backups.")
    st.write("- Signals remain decision-support only, not financial advice.")
