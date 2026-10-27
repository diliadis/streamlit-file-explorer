"""Thin Streamlit adapter around the independently testable filesystem controller."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import streamlit as st

from .controller import ExplorerController
from .filesystem import LocalFilesystem
from .models import ExplorerResult, SelectionMode


@lru_cache(maxsize=1)
def _get_component() -> Callable[..., Any]:
    # Register once, on first render, so importing the public API also works in
    # scripts and tests that do not have a Streamlit runtime.
    return st.components.v2.component(
        "streamlit-file-explorer.streamlit_file_explorer",
        js="index-*.js",
        css="*.css",
        html='<div class="react-root"></div>',
        isolate_styles=True,
    )


def file_explorer(
    roots: Mapping[str, str | Path],
    *,
    key: str,
    label: str = "Files",
    environment_label: str = "",
    selection_mode: SelectionMode = "file",
    multiple: bool = False,
    extensions: Sequence[str] | None = None,
    show_hidden: bool = False,
    preview: bool = True,
    height: int = 420,
    page_size: int = 100,
    max_entries: int = 10_000,
    max_preview_bytes: int = 262_144,
    cache_ttl: float = 2.0,
) -> ExplorerResult:
    """Browse explicitly configured server-side filesystem roots.

    roots maps visible location names to directories. The app's OS identity
    determines access locally and on a cluster. This component performs no writes,
    never follows child symlinks, and requires no second HTTP server.

    key must be unique and stable. Every instance and browser session has its
    own navigation and cache. Changing filesystem/selection settings resets that
    instance. height is the scrollable file-list height (240–500 pixels).

    selection_mode accepts 'file', 'directory', or 'any'. multiple permits
    selection within the current folder. extensions accepts suffixes such as
    ['.csv', '.tar.gz']; folders remain visible for navigation. Hidden-file
    visibility and extension filters are UI controls, not authorization policies.

    max_entries bounds scanned entries per folder. If hit, the UI explicitly
    reports that sorting/search apply to a partial listing. max_preview_bytes
    bounds reads; text/table rendering has additional row/character limits.

    Returns an immutable ExplorerResult. confirmed is true for one run only
    when the user presses Use. Highlighted items are available in selection.
    Place this call and its result handling inside st.fragment to isolate reruns.
    """
    if not isinstance(key, str) or not key:
        raise ValueError("key must be a nonempty string")
    if selection_mode not in ("file", "directory", "any"):
        raise ValueError("selection_mode must be 'file', 'directory', or 'any'")
    for name, flag in [("multiple", multiple), ("show_hidden", show_hidden), ("preview", preview)]:
        if type(flag) is not bool:
            raise ValueError(f"{name} must be a boolean")
    if not isinstance(label, str) or not isinstance(environment_label, str):
        raise ValueError("label and environment_label must be strings")
    for name, value, low, high in [
        ("height", height, 240, 500),
        ("page_size", page_size, 1, 500),
        ("max_preview_bytes", max_preview_bytes, 1024, 2_097_152),
    ]:
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{name} must be an integer between {low} and {high}")
    if type(cache_ttl) not in (int, float) or not 0 <= cache_ttl <= 60:
        raise ValueError("cache_ttl must be between 0 and 60 seconds")
    if extensions is not None and (
        not isinstance(extensions, Sequence)
        or isinstance(extensions, str)
        or any(not isinstance(s, str) for s in extensions)
    ):
        raise ValueError("extensions must be a sequence of string suffixes")
    suffixes = tuple(
        sorted({s.lower() if s.startswith(".") else "." + s.lower() for s in extensions or ()})
    )
    if any(s == "." or "/" in s or "\\" in s for s in suffixes):
        raise ValueError("extensions must contain valid filename suffixes")
    fs = LocalFilesystem(roots, max_entries=max_entries)
    config = (
        tuple(fs.roots.items()),
        selection_mode,
        multiple,
        suffixes,
        show_hidden,
        preview,
        page_size,
        max_entries,
        max_preview_bytes,
        cache_ttl,
    )
    state_key = f"_file_explorer:{key}"
    pending_key = f"{state_key}:pending"
    previous = st.session_state.get(state_key)
    controller: ExplorerController
    if previous is None or previous[0] != config:
        controller = ExplorerController(
            fs,
            selection_mode=selection_mode,
            multiple=multiple,
            extensions=suffixes,
            show_hidden=show_hidden,
            preview=preview,
            page_size=page_size,
            max_preview_bytes=max_preview_bytes,
            cache_ttl=cache_ttl,
        )
        st.session_state[state_key] = (config, controller)
        st.session_state.pop(pending_key, None)
    else:
        controller = previous[1]
    controller.apply(st.session_state.pop(pending_key, None))

    def receive_action() -> None:
        widget: Any = st.session_state.get(key, {})
        st.session_state[pending_key] = widget.get("action")

    _get_component()(
        key=key,
        data=controller.payload(label=label, environment=environment_label, height=height),
        on_action_change=receive_action,
        width="stretch",
        height="content",
    )
    return controller.result()
