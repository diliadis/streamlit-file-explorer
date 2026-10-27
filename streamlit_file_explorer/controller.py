"""Per-instance navigation state and validated frontend actions."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict
from pathlib import PurePosixPath
from typing import Any

from .filesystem import LocalFilesystem, relative_path
from .models import Entry, ExplorerError, ExplorerResult, Listing, SelectionMode, SortBy


class ExplorerController:
    """One controller per Streamlit session and component key. No global cache."""

    def __init__(
        self,
        fs: LocalFilesystem,
        *,
        selection_mode: SelectionMode,
        multiple: bool,
        extensions: tuple[str, ...],
        show_hidden: bool,
        preview: bool,
        page_size: int,
        max_preview_bytes: int,
        cache_ttl: float,
    ) -> None:
        self.fs = fs
        self.instance_id = str(uuid.uuid4())
        self.selection_mode = selection_mode
        self.multiple = multiple
        self.extensions = extensions
        self.root = next(iter(fs.roots))
        self.path = ""
        self.selected: list[str] = []
        self.query = ""
        self.sort: SortBy = "name"
        self.descending = False
        self.page = 0
        self.show_hidden = show_hidden
        self.show_preview = preview
        self.page_size = page_size
        self.max_preview_bytes = max_preview_bytes
        self.cache_ttl = cache_ttl
        self.error: str | None = None
        self.confirmed = False
        self.ack = ""
        self.revision = 0
        self._listing: tuple[tuple[str, str, bool], float, Listing] | None = None

    def apply(self, event: Any) -> None:
        self.confirmed = False
        if not isinstance(event, dict):
            return
        action_id = event.get("id")
        if not isinstance(action_id, str) or not action_id or len(action_id) > 128:
            self.error = "Invalid explorer action. Refresh the folder."
            return
        if action_id == self.ack:
            return
        self.ack = action_id
        self.revision += 1
        self.error = None
        try:
            # Reject delayed actions from a folder that has already been left.
            if event.get("context") != {"root": self.root, "path": self.path}:
                return
            action = event.get("type")
            if action == "navigate":
                target_root = event.get("root")
                if not isinstance(target_root, str):
                    raise ExplorerError("Invalid location.")
                target_path = relative_path(event.get("path"))
                if self.fs.inspect(target_root, target_path).kind != "directory":
                    raise ExplorerError("This item is not a folder.")
                self.root, self.path = target_root, target_path
                self.selected, self.query, self.page = [], "", 0
                self._listing = None
            elif action == "select":
                self.selected = self._validate_selection(event.get("paths"), confirming=False)
            elif action == "confirm":
                selection = self._validate_selection(event.get("paths"), confirming=True)
                if not selection:
                    raise ExplorerError("Select an item first.")
                self.selected, self.confirmed = selection, True
            elif action == "search":
                query = event.get("query")
                if not isinstance(query, str) or len(query) > 1000:
                    raise ExplorerError("Search must be at most 1,000 characters.")
                self.query, self.page = query, 0
            elif action == "sort":
                sort = event.get("sort")
                descending = event.get("descending")
                if sort not in ("name", "size", "modified", "type") or type(descending) is not bool:
                    raise ExplorerError("Invalid sort option.")
                self.sort, self.descending, self.page = sort, descending, 0
            elif action == "page":
                page = event.get("page")
                if type(page) is not int or not 0 <= page <= self.fs.max_entries:
                    raise ExplorerError("Invalid page.")
                self.page = page
            elif action == "hidden":
                self.show_hidden = not self.show_hidden
                self.page = 0
                self._listing = None
            elif action == "preview":
                self.show_preview = not self.show_preview
            elif action == "refresh":
                self._listing = None
            else:
                raise ExplorerError("Unknown explorer action.")
        except ExplorerError as exc:
            self.error = str(exc)

    def _validate_selection(self, paths: Any, *, confirming: bool) -> list[str]:
        if not isinstance(paths, list) or len(paths) > (1000 if self.multiple else 1):
            raise ExplorerError("Invalid selection.")
        validated: list[str] = []
        for value in paths:
            path = relative_path(value)
            parent = str(PurePosixPath(path).parent)
            parent = "" if parent == "." else parent
            if path != self.path and parent != self.path:
                raise ExplorerError("Select items from the current folder.")
            entry = self.fs.inspect(self.root, path)
            if (
                entry.kind == "file"
                and self.extensions
                and not path.lower().endswith(self.extensions)
            ):
                raise ExplorerError("This file type is not allowed by the app.")
            if confirming and not self.can_select(entry):
                raise ExplorerError(f"Choose a {self.selection_mode} for this picker.")
            if path not in validated:
                validated.append(path)
        return validated

    def can_select(self, entry: Entry) -> bool:
        return self.selection_mode == "any" or entry.kind == self.selection_mode

    def _read_listing(self) -> Listing:
        key = (self.root, self.path, self.show_hidden)
        now = time.monotonic()
        if self._listing and self._listing[0] == key and now - self._listing[1] < self.cache_ttl:
            return self._listing[2]
        listing = self.fs.list_directory(self.root, self.path, show_hidden=self.show_hidden)
        self._listing = (key, now, listing)
        return listing

    def payload(self, *, label: str, environment: str, height: int) -> dict[str, Any]:
        listing = Listing(())
        selected_entries = []
        preview: dict[str, Any] | None = None
        try:
            listing = self._read_listing()
            # Revalidate references even when the listing came from cache.
            for path in self.selected:
                selected_entries.append(self.fs.inspect(self.root, path))
        except ExplorerError as exc:
            self.error = str(exc)
            self.selected, selected_entries, self.confirmed = [], [], False
        if self.show_preview and selected_entries:
            try:
                preview = self.fs.preview(
                    self.root, selected_entries[-1].path, max_bytes=self.max_preview_bytes
                )
            except ExplorerError as exc:
                preview = {"kind": "error", "message": str(exc)}
        entries = [
            e
            for e in listing.entries
            if (not self.extensions or e.kind != "file" or e.name.lower().endswith(self.extensions))
            and self.query.casefold() in e.name.casefold()
        ]

        def sort_key(entry: Entry) -> tuple[Any, str]:
            if self.sort == "size":
                return (entry.size or 0), entry.name.casefold()
            if self.sort == "modified":
                return (entry.modified or 0), entry.name.casefold()
            if self.sort == "type":
                return PurePosixPath(entry.name).suffix.casefold(), entry.name.casefold()
            return entry.name.casefold(), entry.name

        entries.sort(key=sort_key, reverse=self.descending)
        entries.sort(key=lambda entry: entry.kind != "directory")
        pages = max(1, (len(entries) + self.page_size - 1) // self.page_size)
        self.page = min(self.page, pages - 1)
        start = self.page * self.page_size
        return {
            "instance_id": self.instance_id,
            "label": label,
            "environment": environment,
            "height": height,
            "locations": [{"id": name, "label": name} for name in self.fs.roots],
            "root": self.root,
            "path": self.path,
            "display_path": str(self.fs.path(self.root, self.path)),
            "entries": [asdict(entry) for entry in entries[start : start + self.page_size]],
            "total": len(entries),
            "page": self.page,
            "pages": pages,
            "page_size": self.page_size,
            "truncated": listing.truncated,
            "max_entries": self.fs.max_entries,
            "selected": self.selected,
            "selected_entries": [asdict(entry) for entry in selected_entries],
            "query": self.query,
            "sort": self.sort,
            "descending": self.descending,
            "show_hidden": self.show_hidden,
            "show_preview": self.show_preview,
            "preview": preview,
            "multiple": self.multiple,
            "selection_mode": self.selection_mode,
            "can_confirm": bool(selected_entries)
            and all(self.can_select(e) for e in selected_entries),
            "error": self.error,
            "ack": self.ack,
            "revision": self.revision,
        }

    def result(self) -> ExplorerResult:
        return ExplorerResult(
            directory=self.fs.path(self.root, self.path),
            selection=tuple(self.fs.path(self.root, path) for path in self.selected),
            confirmed=self.confirmed,
            error=self.error,
        )
