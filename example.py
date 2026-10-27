"""Minimal integration; launch with: streamlit run example.py."""

from pathlib import Path

import streamlit as st

from streamlit_file_explorer import file_explorer

st.set_page_config(layout="wide")
st.title("Choose an input file")
result = file_explorer(
    {"Examples": Path(__file__).parent / "examples" / "data" / "workspace"},
    key="inputs",
)
if result.confirmed:
    st.write(result.selection)
