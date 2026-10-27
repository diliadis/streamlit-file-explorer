# Contributing

Start with a small issue describing the problem or a pull request with a focused change. For filesystem bugs, use synthetic files rather than private data. See README for supported platforms and known limits.

## Set up

Use Python 3.10+ and Node.js 24+:

```bash
uv sync --frozen
npm --prefix streamlit_file_explorer/frontend ci
uv run streamlit run streamlit_app.py --server.address 127.0.0.1
```

The production frontend bundle is committed so package users can install directly from source without Node. After editing TypeScript/CSS, run the frontend build and commit the changed bundle alongside source changes. The build cleans old hashed files. CI rebuilds and checks that committed assets are current.

```bash
npm --prefix streamlit_file_explorer/frontend run format
npm --prefix streamlit_file_explorer/frontend test
npm --prefix streamlit_file_explorer/frontend run build
uv run ruff format .
uv run ruff check .
uv run mypy
uv run pytest
uv run python scripts/check_release.py
uv build
uv run python scripts/check_distribution.py
uv run twine check --strict dist/*
uv run python scripts/smoke_install.py
```

`smoke_install.py` creates a temporary environment, installs both artifacts using pip, and tests the installed code outside the checkout. It needs access to PyPI for dependencies. It also starts a real localhost Streamlit server and verifies the installed JS/CSS asset responses. Before a release, run `tests/apps/visual.py` for real-browser interaction checks in light/dark themes and narrow layouts.

Preserve the separation between filesystem I/O, controller state, the Streamlit adapter and frontend presentation. Keep all file reads bounded, use the v2 component API, and never interpolate filenames or preview contents as HTML. Tests should exercise behavior, failures and regressions.

See [the release guide](docs/releasing.md) for versioning and publishing.
