import streamlit as st
from ui.components import empty_state,section_header
def render_market_scan() -> None:
    section_header("Market Scan","BUY, WATCH and market-opportunity views.")
    c1,c2,c3=st.columns(3)
    with c1: st.selectbox("Signal",["All","BUY","WATCH","IGNORE"],disabled=True)
    with c2: st.slider("Minimum score",0,100,70,disabled=True)
    with c3: st.text_input("Search ticker",disabled=True)
    empty_state("Scanner not connected yet","Sprint 1 Part 3 will connect market data and candidate ranking.","🔎")
