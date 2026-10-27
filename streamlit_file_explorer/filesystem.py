"""Bounded, read-only filesystem access without recursive traversal or shared caches."""

from __future__ import annotations

import base64
import codecs
import csv
import errno
import io
import os
import stat
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .models import Entry, ExplorerError, Listing


def relative_path(value: object) -> str:
    """Validate the platform-independent path format used by the frontend."""
    if not isinstance(value, str) or len(value) > 4096 or "\x00" in value:
        raise ExplorerError("Invalid path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or PureWindowsPath(value).drive:
        raise ExplorerError("Choose a path inside a configured location.")
    return "" if str(path) == "." else path.as_posix()


def friendly_error(exc: OSError) -> str:
    if exc.errno in {errno.EACCES, errno.EPERM}:
        return "Permission denied. The app's account cannot access this item."
    if exc.errno == errno.ENOENT:
        return "This item is no longer available. Refresh the folder."
    if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
        return "This path is a symbolic link or is no longer a folder."
    return "The filesystem could not read this item. Try refreshing the folder."


class LocalFilesystem:
    """Access explicit filesystem roots using the Streamlit process's OS identity.

    Symbolic links below a root are never followed. On POSIX, reads walk directory
    descriptors with O_NOFOLLOW, so replacing a child with a symlink cannot redirect
    the read. Roots and their ancestors must be controlled by the deploying app.
    """

    def __init__(self, roots: Mapping[str, str | Path], *, max_entries: int = 10_000):
        if (
            not isinstance(roots, Mapping)
            or not roots
            or any(not isinstance(label, str) or not label.strip() for label in roots)
        ):
            raise ValueError("roots must contain at least one nonempty location label")
        if type(max_entries) is not int or not 1 <= max_entries <= 100_000:
            raise ValueError("max_entries must be between 1 and 100,000")
        if any(not isinstance(path, (str, Path)) for path in roots.values()):
            raise ValueError("root paths must be strings or pathlib.Path objects")
        self.roots = {label: Path(path).expanduser().resolve() for label, path in roots.items()}
        self.max_entries = max_entries

    def path(self, root: str, relative: object) -> Path:
        if root not in self.roots:
            raise ExplorerError("Unknown filesystem location.")
        return self.roots[root] / relative_path(relative)

    @contextmanager
    def _open(self, root: str, relative: object, *, directory: bool = False) -> Iterator[int]:
        rel = relative_path(relative)
        path = self.path(root, rel)
        descriptors: list[int] = []
        try:
            if os.open in os.supports_dir_fd and hasattr(os, "O_NOFOLLOW"):
                flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
                fd = os.open(self.roots[root], flags | os.O_DIRECTORY)
                descriptors.append(fd)
                parts = PurePosixPath(rel).parts
                for index, part in enumerate(parts):
                    child_flags = flags
                    if index < len(parts) - 1 or directory:
                        child_flags |= os.O_DIRECTORY
                    fd = os.open(part, child_flags, dir_fd=fd)
                    descriptors.append(fd)
            else:
                # Portable fallback. OS permissions remain the security boundary;
                # concurrent path replacement is not defended on this platform.
                current = self.roots[root]
                for part in PurePosixPath(rel).parts:
                    current /= part
                    if current.is_symlink():
                        raise ExplorerError("Symbolic links are not followed.")
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_BINARY", 0))
                descriptors.append(fd)
            mode = os.fstat(fd).st_mode
            if directory and not stat.S_ISDIR(mode):
                raise ExplorerError("This item is not a folder.")
            if not directory and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                raise ExplorerError("Only regular files and folders can be selected.")
            yield fd
        except OSError as exc:
            raise ExplorerError(friendly_error(exc)) from exc
        finally:
            for descriptor in reversed(descriptors):
                os.close(descriptor)

    def inspect(self, root: str, relative: object) -> Entry:
        rel = relative_path(relative)
        with self._open(root, rel) as fd:
            info = os.fstat(fd)
        return Entry(
            name=PurePosixPath(rel).name or root,
            path=rel,
            kind="directory" if stat.S_ISDIR(info.st_mode) else "file",
            size=info.st_size if stat.S_ISREG(info.st_mode) else None,
            modified=info.st_mtime,
        )

    def list_directory(self, root: str, relative: object, *, show_hidden: bool) -> Listing:
        rel = relative_path(relative)
        entries: list[Entry] = []
        truncated = False
        with self._open(root, rel, directory=True) as fd:
            source: int | Path = fd if os.scandir in os.supports_fd else self.path(root, rel)
            with os.scandir(source) as items:
                for index, item in enumerate(items):
                    if index >= self.max_entries:
                        truncated = True
                        break
                    if not show_hidden and item.name.startswith("."):
                        continue
                    child = f"{rel}/{item.name}" if rel else item.name
                    try:
                        relative_path(child)
                        # Undecodable Unix filenames cannot be transported by JSON.
                        item.name.encode("utf-8")
                        info = item.stat(follow_symlinks=False)
                        mode = info.st_mode
                        kind: Any = (
                            "symlink"
                            if stat.S_ISLNK(mode)
                            else "directory"
                            if stat.S_ISDIR(mode)
                            else "file"
                            if stat.S_ISREG(mode)
                            else "other"
                        )
                        error = None
                        if kind == "symlink":
                            error = "Symbolic links are not followed."
                        elif kind == "other":
                            error = "Special filesystem entries cannot be opened."
                        entries.append(
                            Entry(
                                item.name,
                                child,
                                kind,
                                info.st_size if kind == "file" else None,
                                info.st_mtime,
                                error,
                            )
                        )
                    except (OSError, ExplorerError, UnicodeError):
                        # Include an unavailable row without leaking invalid Unicode.
                        safe_name = item.name.encode("utf-8", errors="replace").decode()
                        entries.append(
                            Entry(
                                safe_name,
                                "",
                                "unavailable",
                                None,
                                None,
                                "This entry is unavailable or has an unsupported name.",
                            )
                        )
        return Listing(tuple(entries), truncated)

    def preview(self, root: str, relative: str, *, max_bytes: int) -> dict[str, Any]:
        """Never deserialize documents, execute markup, or read an unbounded file."""
        with self._open(root, relative) as fd:
            info = os.fstat(fd)
            if stat.S_ISDIR(info.st_mode):
                return {"kind": "directory", "message": "Open this folder to browse its contents."}
            # read() is bounded even if a file grows after fstat().
            with os.fdopen(os.dup(fd), "rb") as stream:
                raw = stream.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
        image_type = _image_type(raw)
        if image_type:
            if truncated:
                return {"kind": "metadata", "message": "Image exceeds the preview size limit."}
            return {
                "kind": "image",
                "src": f"data:{image_type};base64," + base64.b64encode(raw).decode("ascii"),
            }
        if b"\x00" in raw:
            return {"kind": "metadata", "message": "Preview is unavailable for this binary file."}
        try:
            text = codecs.getincrementaldecoder("utf-8-sig")().decode(raw, final=not truncated)
        except UnicodeError:
            return {"kind": "metadata", "message": "Preview supports UTF-8 text and small images."}
        suffix = PurePosixPath(relative).suffix.lower()
        if suffix in {".csv", ".tsv"}:
            try:
                rows = []
                for index, row in enumerate(
                    csv.reader(io.StringIO(text), delimiter="\t" if suffix == ".tsv" else ",")
                ):
                    if index == 51:
                        truncated = True
                        break
                    truncated |= len(row) > 20 or any(len(cell) > 300 for cell in row)
                    rows.append([cell[:300] for cell in row[:20]])
                return {"kind": "table", "rows": rows, "truncated": truncated}
            except csv.Error:
                pass
        lines = text.splitlines()
        clipped = "\n".join(lines[:200])[:20_000]
        return {
            "kind": "text",
            "text": clipped,
            "truncated": truncated or len(lines) > 200 or len(text) > 20_000,
        }


def _image_type(raw: bytes) -> str | None:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if raw[:6] in {b"GIF87a", b"GIF89a"}:
        return "image/gif"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "image/webp"
    return None
