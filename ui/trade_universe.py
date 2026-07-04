import streamlit as st
from data.universe import DEFAULT_UNIVERSE
from ui.components import section_header
def render_trade_universe() -> None:
    section_header("Trade Universe", "The starter universe used by Catalyst AI v4.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Starter Symbols", len(DEFAULT_UNIVERSE))
    c2.metric("Asset Types", "Stocks + ETFs")
    c3.metric("Primary Market", "United States")
    search = st.text_input("Search universe").strip().upper()
    symbols = [ticker for ticker in DEFAULT_UNIVERSE if search in ticker] if search else DEFAULT_UNIVERSE
    st.dataframe({"Ticker": symbols}, use_container_width=True, hide_index=True)
    st.caption("You can override this list from the Market Scan page.")
