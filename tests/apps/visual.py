"""Manual browser smoke test: narrow layout, multiple instances, and confirmations.

Run from the project root: streamlit run tests/apps/visual.py
Use --theme.base dark to verify inherited dark mode.
"""

from pathlib import Path

import streamlit as st

from streamlit_file_explorer import file_explorer

st.set_page_config(page_title="Explorer integration check", layout="wide")
workspace = Path(__file__).resolve().parents[2] / "examples" / "data" / "workspace"
st.title("Explorer integration check")
for column, key, label in zip(
    st.columns([1, 2]), ["narrow", "wide"], ["Compact", "Standard"], strict=True
):
    with column:
        result = file_explorer(
            {"Workspace": workspace},
            key=key,
            label=label,
            multiple=True,
            selection_mode="any",
            height=260,
            page_size=3,
        )
        st.write("Directory:", result.directory.name)
        st.write("Selected:", [path.name for path in result.selection])
        if result.confirmed:
            st.success("Confirmed: " + ", ".join(path.name for path in result.selection))
