import html
import streamlit as st


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
/* Catalyst primary navigation: wrap instead of horizontal scrolling */
div[data-testid="stRadio"][aria-label="Navigation"] {
    width: 100%;
    overflow: visible !important;
}

div[data-testid="stRadio"][aria-label="Navigation"] > div {
    width: 100%;
    overflow: visible !important;
}

div[data-testid="stRadio"][aria-label="Navigation"] div[role="radiogroup"] {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.65rem !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow-x: hidden !important;
    overflow-y: visible !important;
    padding-bottom: 0.15rem !important;
}

div[data-testid="stRadio"][aria-label="Navigation"] label {
    flex: 0 1 auto !important;
    min-width: 0 !important;
    white-space: nowrap !important;
    margin: 0 !important;
}

/* Prevent the app canvas itself from sliding horizontally */
html,
body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main .block-container {
    max-width: 100% !important;
    overflow-x: hidden !important;
}

/* Keep navigation usable on narrower screens */
@media (max-width: 900px) {
    div[data-testid="stRadio"][aria-label="Navigation"] label {
        flex: 1 1 calc(33.333% - 0.65rem) !important;
    }
}

@media (max-width: 640px) {
    div[data-testid="stRadio"][aria-label="Navigation"] label {
        flex: 1 1 calc(50% - 0.65rem) !important;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )


def top_navigation() -> str:
    navigation_overflow_fix()
    return st.radio(
        "Navigation",
        PRIMARY_NAVIGATION,
        horizontal=True,
        label_visibility="collapsed",
        key="primary_navigation",
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
