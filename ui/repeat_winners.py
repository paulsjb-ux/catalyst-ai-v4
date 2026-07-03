import streamlit as st
from ui.components import empty_state,section_header
def render_repeat_winners() -> None:
    section_header("Repeat Winners","Stocks repeatedly qualifying as high-conviction candidates.")
    c1,c2,c3=st.columns(3)
    c1.metric("Emerging","0")
    c2.metric("Proven","0")
    c3.metric("Priority","0")
    empty_state("No repeat evidence yet","Repeat winners need multiple daily scans.","🏆")
