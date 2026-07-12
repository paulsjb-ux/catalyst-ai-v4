import html
import streamlit as st

def render_header(app_name: str, tagline: str, engine_name: str, version: str) -> None:
    st.markdown(f"""
    <div class="hero">
        <h1>🚀 {html.escape(app_name)}</h1>
        <p><strong>{html.escape(tagline)}</strong><br>Powered by the {html.escape(engine_name)}</p>
        <span class="badge">Version {html.escape(version)} · Market Intelligence Only</span>
    </div>
    """, unsafe_allow_html=True)

def top_navigation() -> str:
    return st.radio(
        "Navigation",
        ["Dashboard","Market Scan","Trade Universe","Watchlist","Validation","Repeat Winners","Reports","Settings"],
        horizontal=True,
        label_visibility="collapsed",
        key="primary_navigation",
    )

def metric_card(label: str, value: str, note: str = "") -> str:
    return f'<div class="metric-card"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div><div class="metric-note">{html.escape(str(note))}</div></div>'

def status_card(message: str, kind: str = "info") -> None:
    css = {"positive":"status-positive","warning":"status-warning","info":"status-info"}.get(kind, "status-info")
    st.markdown(f'<div class="{css}">{html.escape(message)}</div>', unsafe_allow_html=True)

def empty_state(title: str, message: str, icon: str = "📭") -> None:
    st.markdown(f'<div class="empty-state"><div style="font-size:2.2rem">{icon}</div><h3>{html.escape(title)}</h3><p>{html.escape(message)}</p></div>', unsafe_allow_html=True)

def section_header(title: str, subtitle: str = "") -> None:
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)
