import errno
import os
from unittest.mock import patch

import pytest

from streamlit_file_explorer.filesystem import LocalFilesystem, relative_path
from streamlit_file_explorer.models import ExplorerError


@pytest.mark.parametrize(
    "path", ["../secret", "a/../../secret", "/etc/passwd", "C:/Windows", "a\\b", "\x00", None, 4]
)
def test_rejects_escaping_or_invalid_paths(fs, path):
    with pytest.raises(ExplorerError):
        fs.inspect("Workspace", path)


def test_normalizes_relative_paths():
    assert relative_path("./results//hit.csv") == "results/hit.csv"
    assert relative_path(".") == ""


def test_listing_is_shallow_and_hidden_is_explicit(fs):
    entries = fs.list_directory("Workspace", "", show_hidden=False).entries
    assert {e.name for e in entries} == {"results", "a.csv", "b.txt"}
    assert "hit.csv" not in {e.name for e in entries}
    assert ".hidden" in {
        e.name for e in fs.list_directory("Workspace", "", show_hidden=True).entries
    }


def test_empty_directories_are_listed(fs, workspace):
    (workspace / "empty").mkdir()
    assert any(
        e.name == "empty" and e.kind == "directory"
        for e in fs.list_directory("Workspace", "", show_hidden=False).entries
    )


def test_limit_is_reported(workspace):
    fs = LocalFilesystem({"Workspace": workspace}, max_entries=2)
    listing = fs.list_directory("Workspace", "", show_hidden=True)
    assert len(listing.entries) == 2 and listing.truncated


def test_unknown_root_is_rejected(fs):
    with pytest.raises(ExplorerError, match="Unknown"):
        fs.inspect("Other", "")


@pytest.mark.parametrize("inside", [True, False])
def test_links_are_visible_but_never_followed(fs, workspace, tmp_path, inside):
    target = workspace / "a.csv" if inside else tmp_path / "secret.txt"
    if not inside:
        target.write_text("secret")
    (workspace / "link").symlink_to(target)
    entry = next(
        e for e in fs.list_directory("Workspace", "", show_hidden=False).entries if e.name == "link"
    )
    assert entry.kind == "symlink" and entry.error
    with pytest.raises(ExplorerError):
        fs.preview("Workspace", "link", max_bytes=1024)


def test_directory_symlink_cannot_escape(fs, workspace, tmp_path):
    (tmp_path / "secret").write_text("private")
    (workspace / "escape").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ExplorerError):
        fs.preview("Workspace", "escape/secret", max_bytes=1024)


def test_replacement_between_listing_and_read_is_rejected(fs, workspace, tmp_path):
    fs.list_directory("Workspace", "", show_hidden=False)
    (tmp_path / "secret").write_text("private")
    (workspace / "b.txt").unlink()
    (workspace / "b.txt").symlink_to(tmp_path / "secret")
    with pytest.raises(ExplorerError):
        fs.preview("Workspace", "b.txt", max_bytes=1024)


def test_special_files_are_not_opened(fs, workspace):
    os.mkfifo(workspace / "pipe")
    entry = next(
        e for e in fs.list_directory("Workspace", "", show_hidden=False).entries if e.name == "pipe"
    )
    assert entry.kind == "other"
    with pytest.raises(ExplorerError):
        fs.preview("Workspace", "pipe", max_bytes=1024)


def test_permission_failure_is_actionable(fs):
    with (
        patch("os.open", side_effect=PermissionError(errno.EACCES, "denied")),
        pytest.raises(ExplorerError, match="Permission denied"),
    ):
        fs.list_directory("Workspace", "", show_hidden=False)


def test_text_preview_is_bounded_and_utf8_boundary_is_valid(fs, workspace):
    (workspace / "large.txt").write_text("a" * 1023 + "é" * 5000)
    preview = fs.preview("Workspace", "large.txt", max_bytes=1024)
    assert preview["kind"] == "text" and preview["truncated"]
    assert preview["text"] == "a" * 1023


def test_binary_does_not_render_as_text(fs, workspace):
    (workspace / "binary").write_bytes(b"hello\x00world")
    assert fs.preview("Workspace", "binary", max_bytes=1024)["kind"] == "metadata"


def test_csv_with_quoted_newlines(fs, workspace):
    (workspace / "quoted.csv").write_text('name,comment\na,"one\ntwo"\n')
    result = fs.preview("Workspace", "quoted.csv", max_bytes=1024)
    assert result["rows"] == [["name", "comment"], ["a", "one\ntwo"]]


def test_csv_row_limit(fs, workspace):
    (workspace / "many.csv").write_text("name,score\n" + "a,2\n" * 100)
    result = fs.preview("Workspace", "many.csv", max_bytes=1024)
    assert result["kind"] == "table" and len(result["rows"]) == 51 and result["truncated"]


def test_small_png_and_oversized_image(fs, workspace):
    (workspace / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 20)
    assert fs.preview("Workspace", "image.png", max_bytes=1024)["src"].startswith(
        "data:image/png;base64,"
    )
    (workspace / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 2048)
    assert fs.preview("Workspace", "image.png", max_bytes=1024)["kind"] == "metadata"


def test_markup_is_returned_as_plain_text(fs, workspace):
    (workspace / "page.html").write_text('<script>alert("no")</script>')
    assert fs.preview("Workspace", "page.html", max_bytes=1024)["kind"] == "text"


def test_deleted_file_returns_actionable_error(fs, workspace):
    (workspace / "b.txt").unlink()
    with pytest.raises(ExplorerError, match="no longer available"):
        fs.inspect("Workspace", "b.txt")


def test_descriptors_are_closed_on_success_and_failure(fs):
    before = len(os.listdir("/dev/fd"))
    for _ in range(10):
        fs.preview("Workspace", "a.csv", max_bytes=1024)
        with pytest.raises(ExplorerError):
            fs.inspect("Workspace", "missing/file")
    assert len(os.listdir("/dev/fd")) == before
