import streamlit as st
from ui.components import empty_state,metric_card,section_header,status_card
def render_dashboard(version: str) -> None:
    section_header("Command Dashboard","Catalyst AI v4 application shell and operating status.")
    c1,c2,c3,c4=st.columns(4)
    c1.markdown(metric_card("Universe","Not loaded","engine connects in Part 3"),unsafe_allow_html=True)
    c2.markdown(metric_card("BUY","—","no market data yet"),unsafe_allow_html=True)
    c3.markdown(metric_card("WATCH","—","no market data yet"),unsafe_allow_html=True)
    c4.markdown(metric_card("Version",version,"Sprint 1 Part 2"),unsafe_allow_html=True)
    st.markdown("### System Status")
    status_card("UI package loaded successfully.","positive")
    status_card("Trading engine and market data arrive in Sprint 1 Part 3.","info")
    st.markdown("### Today's Intelligence")
    empty_state("No daily scan yet","The dashboard will populate when the engine is connected.","📊")
