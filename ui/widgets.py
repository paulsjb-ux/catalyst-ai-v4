import pandas as pd
import streamlit as st
def dataframe_or_message(frame: pd.DataFrame, message: str = "No data available.") -> None:
    if frame is None or frame.empty:
        st.info(message)
        return
    st.dataframe(frame, use_container_width=True, hide_index=True)
def csv_download(frame: pd.DataFrame, label: str, filename: str) -> None:
    if frame is None:
        frame = pd.DataFrame()
    st.download_button(label, frame.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv", use_container_width=True)
