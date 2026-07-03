import streamlit as st
from ui.components import empty_state,section_header
def render_trade_universe() -> None:
    section_header("Trade Universe","Browse and filter the scan universe.")
    c1,c2=st.columns(2)
    c1.metric("Configured Maximum","650")
    c2.metric("Loaded Today","0")
    empty_state("Universe is not loaded","The universe manager arrives in Sprint 1 Part 3.","🌐")
