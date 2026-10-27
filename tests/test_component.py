"""Exercise the actual adapter callback and session state, without a browser."""

from unittest.mock import Mock

import pytest

from streamlit_file_explorer import component, file_explorer


@pytest.fixture
def adapter(monkeypatch):
    session = {}
    renderer = Mock()
    monkeypatch.setattr(component.st, "session_state", session)
    monkeypatch.setattr(component, "_get_component", lambda: renderer)
    return session, renderer


def deliver(adapter, key, event):
    session, renderer = adapter
    session[key] = {"action": event}
    renderer.call_args.kwargs["on_action_change"]()


def test_callback_selection_confirmation_and_rerun(workspace, adapter):
    roots = {"Workspace": workspace}
    result = file_explorer(roots, key="picker")
    assert result.selection == ()
    event = {
        "type": "confirm",
        "id": "one",
        "paths": ["a.csv"],
        "context": {"root": "Workspace", "path": ""},
    }
    deliver(adapter, "picker", event)
    result = file_explorer(roots, key="picker")
    assert result.confirmed and result.selected_path == workspace / "a.csv"
    assert adapter[1].call_args.kwargs["data"]["ack"] == "one"
    result = file_explorer(roots, key="picker")
    assert not result.confirmed and result.selected_path == workspace / "a.csv"


def test_instances_and_configuration_changes_are_isolated(workspace, adapter):
    roots = {"Workspace": workspace}
    file_explorer(roots, key="first")
    deliver(
        adapter,
        "first",
        {
            "type": "navigate",
            "id": "nav",
            "root": "Workspace",
            "path": "results",
            "context": {"root": "Workspace", "path": ""},
        },
    )
    assert file_explorer(roots, key="first").directory == workspace / "results"
    assert file_explorer(roots, key="second").directory == workspace
    assert file_explorer(roots, key="first", selection_mode="directory").directory == workspace


@pytest.mark.parametrize(
    "settings",
    [
        {"key": ""},
        {"selection_mode": []},
        {"multiple": "yes"},
        {"preview": 1},
        {"show_hidden": 1},
        {"height": 100},
        {"page_size": 0},
        {"page_size": True},
        {"max_entries": 1.5},
        {"max_entries": True},
        {"max_preview_bytes": 0},
        {"cache_ttl": float("nan")},
        {"cache_ttl": "2"},
        {"extensions": ".csv"},
        {"extensions": [1]},
        {"extensions": ["../file"]},
        {"label": 1},
    ],
)
def test_invalid_configuration_is_reported(workspace, adapter, settings):
    with pytest.raises(ValueError):
        file_explorer({"Workspace": workspace}, **({"key": "picker"} | settings))


def test_suffixes_are_normalized(workspace, adapter):
    file_explorer({"Workspace": workspace}, key="picker", extensions=["CSV", ".csv"])
    assert [entry["name"] for entry in adapter[1].call_args.kwargs["data"]["entries"]] == [
        "results",
        "a.csv",
    ]
