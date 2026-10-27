from pathlib import Path

import pytest

from streamlit_file_explorer.controller import ExplorerController
from streamlit_file_explorer.filesystem import LocalFilesystem


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "results").mkdir()
    (root / "results" / "hit.csv").write_text("id,score\na,-9\n")
    (root / "a.csv").write_text("id,value\na,1\nb,2\n")
    (root / "b.txt").write_text("hello world")
    (root / ".hidden").write_text("hidden")
    return root


@pytest.fixture
def fs(workspace: Path) -> LocalFilesystem:
    return LocalFilesystem({"Workspace": workspace})


@pytest.fixture
def controller(fs: LocalFilesystem) -> ExplorerController:
    return ExplorerController(
        fs,
        selection_mode="file",
        multiple=False,
        extensions=(),
        show_hidden=False,
        preview=True,
        page_size=2,
        max_preview_bytes=1024,
        cache_ttl=2,
    )
