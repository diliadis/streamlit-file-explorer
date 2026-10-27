"""Public result types and internal filesystem records; independent of Streamlit."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

SelectionMode = Literal["file", "directory", "any"]
SortBy = Literal["name", "size", "modified", "type"]


@dataclass(frozen=True)
class ExplorerResult:
    """Validated server paths. ``confirmed`` is true only on an explicit Use action.

    Paths are references, not open handles: consumers must handle files changing
    between selection and use. Selection is scoped to the current directory.
    """

    directory: Path
    selection: tuple[Path, ...] = ()
    confirmed: bool = False
    error: str | None = None

    @property
    def selected_path(self) -> Path | None:
        """The first selected path, or None when the selection is empty."""
        return self.selection[0] if self.selection else None


@dataclass(frozen=True)
class Entry:
    name: str
    path: str
    kind: Literal["file", "directory", "symlink", "other", "unavailable"]
    size: int | None
    modified: float | None
    error: str | None = None


@dataclass(frozen=True)
class Listing:
    entries: tuple[Entry, ...]
    truncated: bool = False


class ExplorerError(Exception):
    """A filesystem or input error safe to show inside the explorer."""
