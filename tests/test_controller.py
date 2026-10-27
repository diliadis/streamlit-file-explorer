import uuid
from unittest.mock import patch

from streamlit_file_explorer.controller import ExplorerController
from streamlit_file_explorer.models import ExplorerError


def action(controller, kind, **values):
    event = {
        "type": kind,
        "id": str(uuid.uuid4()),
        "context": {"root": controller.root, "path": controller.path},
        **values,
    }
    controller.apply(event)
    return event


def payload(controller):
    return controller.payload(label="Files", environment="Test", height=400)


def test_folders_first_and_pagination(controller):
    first = payload(controller)
    assert [e["name"] for e in first["entries"]] == ["results", "a.csv"]
    assert first["pages"] == 2
    action(controller, "page", page=1)
    assert [e["name"] for e in payload(controller)["entries"]] == ["b.txt"]


def test_search_and_sort(controller):
    action(controller, "search", query="CSV")
    assert [e["name"] for e in payload(controller)["entries"]] == ["a.csv"]
    action(controller, "search", query="")
    action(controller, "sort", sort="name", descending=True)
    assert [e["name"] for e in payload(controller)["entries"]] == ["results", "b.txt"]


def test_navigation_resets_selection_search_and_page(controller):
    action(controller, "select", paths=["a.csv"])
    action(controller, "search", query="csv")
    action(controller, "navigate", root="Workspace", path="results")
    assert controller.path == "results" and not controller.selected and controller.query == ""
    assert payload(controller)["entries"][0]["name"] == "hit.csv"


def test_confirm_is_explicit_one_run_and_idempotent(controller, workspace):
    action(controller, "select", paths=["a.csv"])
    assert not controller.result().confirmed
    event = action(controller, "confirm", paths=["a.csv"])
    assert controller.result().confirmed
    assert controller.result().selected_path == workspace / "a.csv"
    controller.apply(event)
    assert not controller.result().confirmed
    controller.apply(None)
    assert not controller.result().confirmed


def test_confirmation_revalidates_deleted_selection(controller, workspace):
    action(controller, "select", paths=["a.csv"])
    (workspace / "a.csv").unlink()
    action(controller, "confirm", paths=["a.csv"])
    assert not controller.confirmed and controller.error
    payload(controller)
    assert not controller.selected


def test_selection_mode_and_extensions_are_enforced(controller):
    action(controller, "confirm", paths=["results"])
    assert controller.error and not controller.confirmed
    controller.selection_mode = "directory"
    action(controller, "confirm", paths=[""])
    assert controller.confirmed
    controller.selection_mode = "file"
    controller.extensions = (".csv",)
    action(controller, "confirm", paths=["b.txt"])
    assert controller.error and not controller.confirmed


def test_malicious_or_cross_folder_selection_rejected(controller):
    for paths in [["../secret"], ["results/hit.csv"], ["a.csv", "b.txt"], "a.csv", [None]]:
        action(controller, "confirm", paths=paths)
        assert controller.error and not controller.confirmed


def test_multi_selection_and_duplicates(controller):
    controller.multiple = True
    action(controller, "confirm", paths=["a.csv", "b.txt", "a.csv"])
    assert controller.confirmed and controller.selected == ["a.csv", "b.txt"]


def test_stale_action_cannot_change_current_folder(controller):
    old = {
        "id": "old",
        "context": {"root": "Workspace", "path": ""},
        "type": "confirm",
        "paths": ["a.csv"],
    }
    action(controller, "navigate", root="Workspace", path="results")
    controller.apply(old)
    assert not controller.confirmed and controller.path == "results"


def test_cache_is_instance_local_and_refreshable(controller, fs):
    with patch.object(fs, "list_directory", wraps=fs.list_directory) as scan:
        payload(controller)
        action(controller, "select", paths=["a.csv"])
        payload(controller)
        assert scan.call_count == 1
        action(controller, "refresh")
        payload(controller)
        assert scan.call_count == 2
    other = ExplorerController(
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
    assert other.selected == [] and other._listing is None


def test_permission_error_keeps_navigation_recoverable(controller):
    with patch.object(
        controller.fs, "list_directory", side_effect=ExplorerError("Permission denied")
    ):
        data = payload(controller)
    assert data["error"] == "Permission denied" and data["locations"]
    action(controller, "refresh")
    assert payload(controller)["entries"] and not controller.error


def test_hidden_toggle_and_bad_page(controller):
    action(controller, "hidden")
    assert payload(controller)["total"] == 4
    action(controller, "page", page=-1)
    assert controller.error
    action(controller, "page", page=100)
    assert payload(controller)["page"] == 1


def test_failed_navigation_keeps_current_location(controller):
    action(controller, "navigate", root="Workspace", path="missing")
    assert controller.error and controller.path == ""


def test_malformed_browser_values_do_not_crash(controller):
    for kind, values in [
        ("sort", {"sort": [], "descending": False}),
        ("sort", {"sort": {}, "descending": False}),
        ("sort", {"sort": "name", "descending": 1}),
        ("search", {"query": None}),
        ("navigate", {"root": [], "path": ""}),
        ("page", {"page": True}),
        ("select", {"paths": [False]}),
    ]:
        action(controller, kind, **values)
        assert controller.error
