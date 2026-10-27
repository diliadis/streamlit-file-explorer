# Streamlit File Explorer

A reusable Finder-style file picker built with **Streamlit Custom Components v2**, React, and TypeScript. Browse explicitly configured directories on the machine running Streamlit: your laptop, a server, or a SLURM compute node with mounted project storage.

Version **0.1.0** is the initial alpha release. Source: [diliadis/streamlit-file-explorer](https://github.com/diliadis/streamlit-file-explorer). It supports macOS and Linux. The public API may change in 0.x releases; a real SLURM deployment has not yet been validated.

## What it does

- Location sidebar, breadcrumbs, back/up navigation, and relative path entry.
- Detailed sortable file list, debounced filename search, paging, and hidden-file toggle.
- Optional previews for UTF-8 text, CSV/TSV, and small PNG/JPEG/GIF/WebP images.
- File, folder, or mixed selection; optional multiple selection and suffix filters.
- Explicit confirmation, returning typed `pathlib.Path` values to Python.
- Streamlit theme colors, isolated CSS, responsive layout, keyboard controls, and instance-local state.
- Read-only, shallow directory scans with bounded file reads and clear unavailable/partial states.

There are no file mutations, uploads, downloads, recursive search, remote SSH browsing, or extra filesystem HTTP endpoints. A browser connected to a server browses **that server's filesystem**, not the browser user's laptop. Preview contents are sent to the browser.

## Install

Requires Python 3.10+ and Streamlit 1.53+. Installing the package does **not** require Node.js: the production frontend is included.

Install from PyPI:

```bash
python -m pip install streamlit-file-explorer
```

Or install from this checkout:

```bash
python -m pip install .
```

Or install a built distribution:

```bash
python -m pip install dist/streamlit_file_explorer-0.1.0-py3-none-any.whl
```

Install the current development version directly from GitHub:

```bash
python -m pip install "git+https://github.com/diliadis/streamlit-file-explorer.git@main"
```

The GitHub install follows `main`; pin a commit for reproducibility. To pin the initial PyPI release, use `streamlit-file-explorer==0.1.0`.

## Run the demo

From this source checkout, after installing the package:

```bash
streamlit run streamlit_app.py --server.address 127.0.0.1
```

The demo defaults to bundled example files. To browse your own directories, configure named roots before starting it:

```bash
export FILE_EXPLORER_ROOTS='{"Projects":"/absolute/path/to/projects","Scratch":"/absolute/path/to/scratch"}'
streamlit run streamlit_app.py --server.address 127.0.0.1
```

Use directories visible to the Streamlit process. Missing or unreadable roots produce a recoverable UI error. See the contributor guide for the uv/Node development workflow.

## Use in your app

Install the package using one of the available methods above. Use a unique, stable `key` for each explorer.

```python
from pathlib import Path
import streamlit as st
from streamlit_file_explorer import file_explorer


# Replace /path/to/projects with a directory on the Streamlit host.
@st.fragment
def choose_input():
    result = file_explorer(
        {"Projects": Path("/path/to/projects")},
        key="input_picker",
        label="Choose input files",
        extensions=[".csv", ".tsv"],
        multiple=True,
    )
    if result.confirmed:
        # Persist accepted values if other parts of your app need them later.
        st.session_state["input_paths"] = result.selection
    if st.session_state.get("input_paths"):
        st.write([str(path) for path in st.session_state["input_paths"]])


choose_input()
```

Keep result handling inside the fragment. Interactions then rerun only this section. If another part of the page must immediately react to confirmation, call `st.rerun()` after storing the accepted values. A fragment is optional: the component also works with ordinary app reruns. Do not place it inside `st.form`; the explorer requires immediate callbacks.

`ExplorerResult` is immutable:

| Field | Meaning |
| --- | --- |
| `directory: Path` | Current absolute directory on the Streamlit host. |
| `selection: tuple[Path, ...]` | Highlighted items; highlighting a folder is allowed even in file mode. |
| `selected_path: Path \| None` | Convenience property: the first selected path, or `None` when nothing is selected. |
| `confirmed: bool` | True only on the run handling an explicit **Use selection** or **Use this folder** action. Only confirmed values satisfy the configured selection mode. |
| `error: str \| None` | Recoverable navigation or selection error, also displayed in the component. |

Selection is limited to the current folder and clears on navigation. Paths are revalidated at confirmation, but they are references, not open file handles: downstream code must handle files being moved, removed, or replaced later.

### Parameters

| Parameter | Default | Purpose |
| --- | --- | --- |
| `roots` | required | Mapping of visible location labels to directory paths. |
| `key` | required | Stable, unique Streamlit component key. |
| `label` | `"Files"` | Component heading and accessible name. |
| `environment_label` | `""` | Optional host/location caption. |
| `selection_mode` | `"file"` | `"file"`, `"directory"`, or `"any"`. |
| `multiple` | `False` | Enable selection of up to 1,000 items in one directory. |
| `extensions` | `None` | Case-insensitive suffixes such as `[".csv", ".tar.gz"]`; folders remain visible. |
| `show_hidden` | `False` | Initial dotfile visibility; user can toggle it. |
| `preview` | `True` | Initial preview-pane visibility; user can toggle it. |
| `height` | `420` | File-list height in pixels, 240–500. Toolbar/footer add height; narrow layouts adjust the list. |
| `page_size` | `100` | Rows sent to the frontend at once, 1–500. |
| `max_entries` | `10_000` | Entries examined per directory, 1–100,000. Includes hidden entries. |
| `max_preview_bytes` | `262_144` | File bytes read per preview, 1,024–2,097,152, plus one byte to detect truncation. |
| `cache_ttl` | `2.0` | Session-local listing lifetime in seconds, 0–60. Refresh bypasses it. |

Changing roots or filesystem/selection settings resets that instance's navigation. Changing its label, caption, or height preserves navigation. UI state persists through reruns in the same Streamlit session; it is not stored across new sessions or server restarts.

### Interaction

- Click a row to highlight it; double-click a folder, use its chevron, or press Enter to open it.
- With multiple selection enabled, use checkboxes or Cmd/Ctrl-click to add/remove items.
- Arrow Up/Down, Home, and End move focus between rows. Space highlights the focused row. Arrow Right opens a folder; Arrow Left goes to its parent.
- Cmd/Ctrl-F within the component focuses search. Search matches names in the current scanned folder, not file contents or subdirectories.
- Enter a **relative** path using the path button; an empty path opens the configured root.

## Local and cluster behavior

The same Python filesystem adapter runs locally and on a compute node. SLURM supplies an allocation; it is not a filesystem protocol. There is no cluster credential handling in the component. See [the SLURM guide](https://github.com/diliadis/streamlit-file-explorer/blob/main/docs/slurm.md) and [example batch script](https://github.com/diliadis/streamlit-file-explorer/blob/main/examples/launch_slurm.sbatch).

Only the current folder is scanned. A short per-session cache reduces repeated metadata operations, and only the current page reaches React. The `max_entries` cap is a **scan limit**, not a directory-wide index: when hit, the UI warns that sorting and search operate on a partial listing. Which entries are scanned first depends on filesystem enumeration order. Raise the limit deliberately or choose a narrower root for large directories.

Preview limits are independent: text uses at most 200 lines / 20,000 characters; CSV/TSV uses one header plus 50 data rows, 20 columns, and 300 characters per cell. Large images receive a metadata-only preview. Other binary formats are not decoded. Markup, filenames, and table values are rendered as text.

Filesystem calls are synchronous. An unresponsive NFS/Lustre mount can still stall a session despite bounded entry counts; there is no hard I/O timeout. The loading state exposes this, but cannot cancel a blocked kernel read.

## Access model

- The Streamlit process's OS identity determines access. Configure roots in trusted application code; do not accept root paths directly from an untrusted browser.
- On macOS/Linux, traversal uses directory descriptors and `O_NOFOLLOW`. Child symlinks are visible but cannot be opened, including links within the same root. Expose a desired target as its own configured root instead.
- Roots and their ancestors must be trusted, deployment-controlled directories. OS permissions and your deployment remain the security boundary; the picker does not create filesystem isolation or per-user Unix identities.
- Hidden-file visibility, suffix filters, and the preview toggle are UI features, not confidentiality controls. Everyone able to access an app instance may browse its configured roots with that process's permissions. A shared service account does not inherit each browser user's permissions.
- A returned `Path` can change after selection. Apply your app's own access policy and validation when consuming it. Do not use this component as authorization for destructive downstream operations.
- No root directory is registered as a Streamlit static asset directory. The component serves only its own bundled JS/CSS through the v2 asset manifest.
- Windows is not a supported target in this release; its path-opening semantics have not been validated.

## Development and release checks

Contributors need Node.js 24+ and [uv](https://docs.astral.sh/uv/). Start with `uv sync --frozen` and `npm --prefix streamlit_file_explorer/frontend ci`.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
npm --prefix streamlit_file_explorer/frontend test
npm --prefix streamlit_file_explorer/frontend run format:check
npm --prefix streamlit_file_explorer/frontend run build
uv run python scripts/check_release.py
uv build
uv run python scripts/check_distribution.py
uv run twine check --strict dist/*
uv run python scripts/smoke_install.py
```

When changing frontend code, rebuild its assets and commit them **before** building a wheel or sdist. Otherwise, the checked-in production assets are ready to package. The build refuses to create a package if its assets are missing or ambiguous. The resulting wheel contains the compiled assets, component manifest, Python code, and typing marker. Install that wheel into another app environment with `pip install /path/to/streamlit_file_explorer-0.1.0-py3-none-any.whl`. The sdist also contains frontend source and its lockfile so assets can be rebuilt. CI is configured to run the checks on Linux and macOS, verify both artifacts, and install each with pip in a clean environment. The Actions tab reports the status of each pushed commit.

For frontend iteration, run `npm --prefix streamlit_file_explorer/frontend run dev` in a second terminal. It rebuilds assets in watch mode. Restart the Streamlit process and reload the browser after a rebuild: registered asset paths can otherwise retain the previous bundle name. No Vite development server is exposed to users.

### Structure

- `filesystem.py`: bounded read-only I/O and path validation, independent of UI state.
- `controller.py`: validated actions, navigation, selection, sorting, pagination, and per-instance listing cache.
- `component.py`: public typed API, configuration checks, Streamlit callbacks and session state.
- `frontend/src/`: typed React UI, scoped styles and previews.
- `tests/`: filesystem, controller, and Streamlit adapter regression tests.
- `streamlit_app.py`: runnable demo with sample data and a fragment.

The template comes from Streamlit's [official v2 React/TypeScript starter](https://github.com/streamlit/component-template/tree/465144fa6764ac1227f299e222ef492262ed70c9/cookiecutter/v2). Component registration follows the [official v2 API](https://docs.streamlit.io/develop/api-reference/custom-components/st.components.v2.component). The interaction concept was inspired by [streamlit-file-browser](https://github.com/pragmatic-streamlit/streamlit-file-browser); this implementation does not depend on or copy that package's code.

Licensed under Apache-2.0. See [LICENSE](https://github.com/diliadis/streamlit-file-explorer/blob/main/LICENSE).

See the [contributor guide](https://github.com/diliadis/streamlit-file-explorer/blob/main/CONTRIBUTING.md), [changelog](https://github.com/diliadis/streamlit-file-explorer/blob/main/CHANGELOG.md), [release guide](https://github.com/diliadis/streamlit-file-explorer/blob/main/docs/releasing.md), and [security policy](https://github.com/diliadis/streamlit-file-explorer/blob/main/SECURITY.md).
