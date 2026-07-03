import streamlit as st
def responsive_columns(count: int):
    if count < 1:
        raise ValueError("count must be at least 1")
    return st.columns(count)
def page_intro(title: str, description: str) -> None:
    st.title(title)
    st.caption(description)
