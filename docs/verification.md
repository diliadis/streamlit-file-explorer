# Verification record

Checked locally on macOS arm64 with Python 3.12.2 on 2026-10-25.

- Streamlit 1.66.1 in the development environment: 61 Python tests passed, 92% Python statement coverage.
- Streamlit 1.53.0 in a separate temporary environment: installed the built wheel, copied tests outside the source checkout, and passed all 61 Python tests.
- Frontend: 10 Vitest tests passed; TypeScript check and production Vite build passed.
- Ruff lint/format and strict mypy checks passed.
- Wheel validated to contain the Python package, typing marker, v2 manifest, one JS bundle and one stylesheet, without frontend source or node_modules.
- Batch launcher checked with `bash -n`.

Manual browser checks used the real Streamlit v2 bridge, not a static mockup:

- Main demo: file selection, CSV preview, explicit confirmation returning an absolute path, folder navigation, back navigation, filename search, and configuration reset when enabling multiple selection.
- Installed wheel on Streamlit 1.53: dark theme, narrow and standard layouts, independent component instances, multiple selection, confirmation, and pagination.

The regression suite exercises traversal rejection, child symlinks, path replacement, nonblocking special-file rejection, deleted files, permission errors, preview truncation, escaped markup, stale actions, callback delivery, and session/instance isolation.

Linux CI is configured but has not been run from this local checkout. No live SLURM allocation, Windows environment, accessibility audit, or very large network-filesystem benchmark has been exercised. Browser checks are manual; frontend unit tests do not replace an end-to-end browser suite.

## Packaging checks — 2026-10-27

- Added and validated complete Apache-2.0 and bundled third-party license notices.
- Twine strict metadata/README checks passed for wheel and sdist.
- Fresh pip environments passed all 61 Python tests after installing the wheel and again after installing the sdist. Streamlit's testing runtime mounted the installed component.
- Missing-asset builds and mismatched version tags were correctly rejected.
- Frontend rebuild matched the committed bundle; all 10 frontend tests passed.
- Repository destination confirmed as `diliadis/streamlit-file-explorer`; PyPI publication still requires Trusted Publisher configuration.
