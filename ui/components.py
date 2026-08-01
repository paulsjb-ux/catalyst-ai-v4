import html
import re
import streamlit as st


def render_header(app_name: str, tagline: str, engine_name: str, version: str, page_title: str = "") -> None:
    """Ultra-compact page title bar."""
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
    st.markdown(
        """
<style>
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], section.main,
.main .block-container { width:100%!important; max-width:100%!important; overflow-x:clip!important; }
div[data-testid="stHorizontalBlock"] { width:100%!important; max-width:100%!important; overflow:hidden!important; }
div[data-testid="column"] { min-width:0!important; max-width:100%!important; overflow:hidden!important; }
div[data-testid="column"] .stButton, div[data-testid="column"] .stButton > button { width:100%!important; max-width:100%!important; min-width:0!important; }
div[data-testid="column"] .stButton > button { white-space:normal!important; overflow-wrap:anywhere!important; line-height:1.1!important; }
div[data-testid="stRadio"][aria-label="Navigation"] { display:none!important; }
</style>
""", unsafe_allow_html=True)


def _navigation_key(page: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_")
    return f"workspace_nav_{safe}"


def _render_nav_row(pages: list[str], selected: str, prefix: str) -> None:
    columns = st.columns(len(pages), gap="small")
    for column, page in zip(columns, pages):
        with column:
            clicked = st.button(
                page,
                key=f"{prefix}_{_navigation_key(page)}",
                type="primary" if page == selected else "secondary",
                use_container_width=True,
            )
            if clicked and page != selected:
                st.session_state["primary_navigation"] = page
                st.rerun()


def top_navigation() -> str:
    """Workflow-first navigation: daily pages first, specialist tools on demand."""
    navigation_overflow_fix()
    selected = st.session_state.get("primary_navigation", "Daily Routine")
    if selected not in ALL_NAVIGATION:
        selected = "Daily Routine"
        st.session_state["primary_navigation"] = selected

    _render_nav_row(PRIMARY_NAVIGATION, selected, "primary")

    tools_open = selected in TOOL_NAVIGATION
    with st.expander("More tools" + (f" · {selected}" if tools_open else ""), expanded=tools_open):
        for start in range(0, len(TOOL_NAVIGATION), 5):
            _render_nav_row(TOOL_NAVIGATION[start:start + 5], selected, f"tools_{start}")

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
