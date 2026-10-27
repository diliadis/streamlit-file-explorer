"""Finder-style file browsing for local and cluster Streamlit applications."""

from importlib.metadata import PackageNotFoundError, version

from .component import file_explorer
from .models import ExplorerResult, SelectionMode

__all__ = ["ExplorerResult", "SelectionMode", "file_explorer"]
try:
    __version__ = version("streamlit-file-explorer")
except PackageNotFoundError:
    __version__ = "0+uninstalled"
