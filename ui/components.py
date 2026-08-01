import html
import re
import streamlit as st
from version import APP_VERSION


def render_header(app_name: str, tagline: str, engine_name: str, version: str, page_title: str = "") -> None:
    """Compact workspace title bar used inside the main content area."""
    title = page_title or app_name
    st.markdown(
        f'''<div class="workspace-header">
        <div class="workspace-brand"><span class="workspace-mark">🚀</span>
        <h1>{html.escape(title)}</h1></div>
        <div class="workspace-product">{html.escape(app_name)} · v{html.escape(version)}</div>
        </div>''', unsafe_allow_html=True
    )


PRIMARY_NAVIGATION = [
    "Daily Routine",
    "Today’s Decision",
    "Dashboard",
    "Watchlist",
    "Reports",
]

TRADING_TOOLS = [
    "Daily Brief",
    "Market Scan",
    "Alerts",
    "Paper Trading",
]

ANALYTICS_TOOLS = [
    "Backtesting",
    "Validation",
    "Repeat Winners",
]

SYSTEM_TOOLS = [
    "Trade Universe",
    "Settings",
]

TOOL_NAVIGATION = [
    "Daily Brief",
    "Market Scan",
    "Alerts",
    "Paper Trading",
    "Backtesting",
    "Validation",
    "Repeat Winners",
    "Trade Universe",
    "Settings",
]
ALL_NAVIGATION = PRIMARY_NAVIGATION + TOOL_NAVIGATION


def navigation_overflow_fix() -> None:
    """Keep the workspace inside the viewport and clear of Streamlit's header."""
    st.markdown(
        """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main {
    width:100%!important; max-width:100%!important; overflow-x:clip!important;
}
.main .block-container {
    width:100%!important; max-width:1500px!important; overflow-x:hidden!important;
    padding-top:3.75rem!important;
}
div[data-testid="stHorizontalBlock"] { width:100%!important; max-width:100%!important; overflow:hidden!important; }
div[data-testid="column"] { min-width:0!important; max-width:100%!important; }
[data-testid="stSidebar"] { border-right:1px solid #dbeafe; }
[data-testid="stSidebarContent"] { padding-top:1rem; }
</style>
""", unsafe_allow_html=True)


def _navigation_key(page: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_")
    return f"workspace_nav_{safe}"


def _sidebar_button(page: str, selected: str, prefix: str) -> None:
    clicked = st.button(
        page,
        key=f"{prefix}_{_navigation_key(page)}",
        type="primary" if page == selected else "secondary",
        use_container_width=True,
    )
    if clicked and page != selected:
        st.session_state["primary_navigation"] = page
        st.rerun()


def _sidebar_group(label: str, pages: list[str], selected: str, prefix: str, expanded: bool = True) -> None:
    with st.expander(label, expanded=expanded):
        for page in pages:
            _sidebar_button(page, selected, prefix)


def top_navigation() -> str:
    """v12 workstation navigation: fixed left rail; legacy More tools content is grouped by workflow."""
    navigation_overflow_fix()
    selected = st.session_state.get("primary_navigation", "Daily Routine")
    if selected not in ALL_NAVIGATION:
        selected = "Daily Routine"
        st.session_state["primary_navigation"] = selected

    with st.sidebar:
        st.markdown(
            f'<div class="sidebar-brand"><span>🚀</span><div><strong>Catalyst AI</strong><small>v{APP_VERSION}</small></div></div>',
            unsafe_allow_html=True,
        )
        
        # "More tools" from v11 are now organised into the groups below.

        for page in PRIMARY_NAVIGATION:
            _sidebar_button(page, selected, "primary")

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        _sidebar_group("Trading tools", TRADING_TOOLS, selected, "trading", selected in TRADING_TOOLS)
        _sidebar_group("Analytics", ANALYTICS_TOOLS, selected, "analytics", selected in ANALYTICS_TOOLS)
        _sidebar_group("System", SYSTEM_TOOLS, selected, "system", selected in SYSTEM_TOOLS)

        st.markdown('<div class="sidebar-footer">One-button swing intelligence</div>', unsafe_allow_html=True)

    return st.session_state.get("primary_navigation", "Daily Routine")


def metric_card(label: str, value: str, note: str = "") -> str:
    return f'<div class="metric-card"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div><div class="metric-note">{html.escape(str(note))}</div></div>'


def status_card(message: str, kind: str = "info") -> None:
    css = {"positive": "status-positive", "warning": "status-warning", "info": "status-info"}.get(kind, "status-info")
    st.markdown(f'<div class="{css}">{html.escape(message)}</div>', unsafe_allow_html=True)


def empty_state(title: str, message: str, icon: str = "📭") -> None:
    st.markdown(f'<div class="empty-state"><div style="font-size:2.2rem">{icon}</div><h3>{html.escape(title)}</h3><p>{html.escape(message)}</p></div>', unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)
