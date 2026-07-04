import streamlit as st
from ui.components import empty_state, section_header
def render_validation() -> None:
    section_header("Validation Centre", "Forward-return tracking and strategy evidence.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Validated Signals", "0")
    c2.metric("Win Rate", "—")
    c3.metric("Average Return", "—")
    empty_state("No validation history", "Validation activates when daily scan history is stored.", "🧪")
