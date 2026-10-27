"""Local demo; set FILE_EXPLORER_ROOTS to use mounted cluster directories."""

import json
import os
from pathlib import Path

import streamlit as st

from streamlit_file_explorer import file_explorer

st.set_page_config(page_title="File Explorer", page_icon="📂", layout="wide")
base = Path(__file__).parent / "examples" / "data"
try:
    roots = (
        json.loads(os.environ["FILE_EXPLORER_ROOTS"])
        if "FILE_EXPLORER_ROOTS" in os.environ
        else {
            "Workspace": str(base / "workspace"),
            "Scratch": str(base / "scratch"),
        }
    )
    if not isinstance(roots, dict) or not all(isinstance(v, str) for v in roots.values()):
        raise ValueError("Expected a JSON object mapping location names to paths.")
except (ValueError, TypeError) as exc:
    st.error(f"Invalid FILE_EXPLORER_ROOTS: {exc}")
    st.stop()

with st.sidebar:
    st.subheader("Explorer settings")
    mode = st.selectbox(
        "Select",
        ["file", "directory", "any"],
        format_func=lambda v: {
            "file": "Files",
            "directory": "Folders",
            "any": "Files and folders",
        }[v],
    )
    multiple = st.toggle("Multiple selection")
    suffixes = st.multiselect(
        "File types", [".csv", ".tsv", ".txt", ".md", ".json", ".yaml", ".pdb", ".sbatch", ".png"]
    )
    st.caption("An empty filter shows all file types.")
    st.divider()
    st.caption(
        "The demo opens bundled example files by default. "
        "Configure locations with FILE_EXPLORER_ROOTS."
    )

st.title("Your files, in one place")
st.write("Browse a workspace, inspect a result, and choose what comes next.")


@st.fragment
def browser() -> None:
    result = file_explorer(
        roots,
        key="workspace_browser",
        label="Workspace files",
        selection_mode=mode,
        multiple=multiple,
        extensions=suffixes,
        height=320,
        environment_label=f"Cluster · job {os.environ['SLURM_JOB_ID']}"
        if "SLURM_JOB_ID" in os.environ
        else "Local filesystem",
    )
    if result.confirmed:
        st.session_state["last_selection"] = [str(path) for path in result.selection]
    if st.session_state.get("last_selection"):
        st.success("Selection ready")
        st.code("\n".join(st.session_state["last_selection"]), language=None)


browser()
with st.expander("Use this component in your app"):
    st.code(
        """from pathlib import Path
from streamlit_file_explorer import file_explorer

result = file_explorer(
    {"Projects": Path("/path/to/projects")},
    key="input_files",
    extensions=[".csv", ".pdb"],
)
if result.confirmed:
    process(result.selected_path)""",
        language="python",
    )
    st.caption(
        "Browse and select are read-only. "
        "The returned paths belong to the machine running Streamlit."
    )
