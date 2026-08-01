import html
import streamlit as st
import re


def render_header(app_name: str, tagline: str, engine_name: str, version: str) -> None:
    st.markdown(f'''<div class="hero"><h1>🚀 {html.escape(app_name)}</h1><p><strong>{html.escape(tagline)}</strong><br>Powered by the {html.escape(engine_name)}</p><span class="badge">Version {html.escape(version)} · Market Intelligence Only</span></div>''', unsafe_allow_html=True)


PRIMARY_NAVIGATION = [
    "Today’s Decision",
    "Daily Routine",
    "Dashboard",
    "Daily Brief",
    "Alerts",
    "Market Scan",
    "Paper Trading",
    "Backtesting",
    "Trade Universe",
    "Watchlist",
    "Validation",
    "Repeat Winners",
    "Reports",
    "Settings",
]


def navigation_overflow_fix() -> None:
    st.markdown(
        """
<style>
/* Fixed-grid navigation: no horizontal strip or sideways dragging. */
html,
body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main .block-container {
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: clip !important;
}

div[data-testid="stHorizontalBlock"] {
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden !important;
}

div[data-testid="column"] {
    min-width: 0 !important;
    max-width: 100% !important;
    overflow: hidden !important;
}

div[data-testid="column"] .stButton,
div[data-testid="column"] .stButton > button {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
}

div[data-testid="column"] .stButton > button {
    white-space: normal !important;
    overflow-wrap: anywhere !important;
    line-height: 1.15 !important;
    min-height: 3.25rem !important;
    padding: 0.55rem 0.45rem !important;
    border-radius: 1rem !important;
}

div[data-testid="stRadio"][aria-label="Navigation"] {
    display: none !important;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _navigation_key(page: str) -> str:
    safe = re.sub(r"[^a-z0-9]+", "_", page.lower()).strip("_")
    return f"primary_nav_{safe}"


def top_navigation() -> str:
    """Render navigation in fixed rows that cannot scroll sideways."""
    navigation_overflow_fix()

    selected = st.session_state.get(
        "primary_navigation",
        PRIMARY_NAVIGATION[0],
    )
    if selected not in PRIMARY_NAVIGATION:
        selected = PRIMARY_NAVIGATION[0]
        st.session_state["primary_navigation"] = selected

    buttons_per_row = 5

    for row_start in range(
        0,
        len(PRIMARY_NAVIGATION),
        buttons_per_row,
    ):
        row_pages = PRIMARY_NAVIGATION[
            row_start : row_start + buttons_per_row
        ]
        columns = st.columns(len(row_pages), gap="small")

        for column, page in zip(columns, row_pages):
            with column:
                clicked = st.button(
                    page,
                    key=_navigation_key(page),
                    type=(
                        "primary"
                        if page == selected
                        else "secondary"
                    ),
                    use_container_width=True,
                )
                if clicked and page != selected:
                    st.session_state["primary_navigation"] = page
                    st.rerun()

    return st.session_state.get(
        "primary_navigation",
        PRIMARY_NAVIGATION[0],
    )


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
