# Releasing Streamlit File Explorer

## Current status

The source tree and built wheel/sdist are pip-installable. The repository is **diliadis/streamlit-file-explorer**. A PyPI project has not yet been created; Trusted Publishing must be configured before uploading a release.

A PyPI lookup on 2026-10-25 found no existing `streamlit-file-explorer` project. That does not reserve the name or guarantee that PyPI will accept it.

## First repository setup

Push reviewed source and compiled assets to the GitHub repository and wait for CI to pass. The intended default branch is `main`. Keep `.venv`, `node_modules`, credentials, local screenshots and `dist` out of Git. The production JS/CSS in `streamlit_file_explorer/frontend/build/` **are** versioned so a source/Git install works without Node.

Enable the repository's private vulnerability reporting. Configure branch protections as appropriate for the maintainer team. The workflows use read-only repository permissions except for the isolated publisher job's OIDC permission. Action versions are pinned to immutable commits; dependency update configuration keeps those pins maintainable.

## One-time PyPI setup

Use PyPI Trusted Publishing rather than putting a long-lived upload token in the repository. This workflow follows the [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/).

1. Sign in to your PyPI and TestPyPI accounts (they are separate services).
2. Create GitHub environments named **testpypi** and **pypi**. Restrict deployments to version tags; configure required reviewers where your account supports them.
3. In each index, register a pending GitHub publisher with:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `streamlit-file-explorer` |
   | Repository owner | `diliadis` |
   | Repository | `streamlit-file-explorer` |
   | Workflow filename | `release.yml` |
   | Environment | `testpypi` on TestPyPI; `pypi` on PyPI |

A pending publisher creates the project on the first successful upload; it does not reserve the name. See [PyPI's setup documentation](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/). These account settings require access to your accounts and have not been configured here.

## Prepare a release

1. Set the same version in the root `pyproject.toml`, `streamlit_file_explorer/pyproject.toml`, and the frontend `package.json` / `package-lock.json` (both root version fields). The Python `__version__` is read from installed distribution metadata.
2. Update `CHANGELOG.md` with release notes and date. The first candidate is `0.1.0` / tag `v0.1.0`.
3. Update the README publication status when the repository and index are live. Confirm its project links resolve.
4. Update bundled dependency notices if runtime frontend dependencies change. Keep Apache-2.0 and the bundled React/Lucide notices in both distributions.
5. Rebuild frontend changes, run tests, and commit the generated assets. Validate version consistency with `uv run python scripts/check_release.py --tag v0.1.0`.
6. Run all commands in CONTRIBUTING.md. Remove obsolete releases from `dist` before building a new version; validation deliberately rejects multiple wheel/sdist versions.
7. Run `streamlit run tests/apps/visual.py` and check selection, navigation, previews, multiple instances, light/dark themes and narrow layouts. The Python tests alone cannot verify browser behavior.
8. Commit reviewed changes, push them, and create/push the version tag once CI passes.

The build checks for exactly one nonempty JS bundle and stylesheet. Distribution checks compare all package files between wheel and sdist and verify metadata/licenses. The pip smoke test installs both artifacts in a new environment, runs the API/filesystem/controller tests outside the checkout, and mounts the component in Streamlit's testing runtime.

## Rehearse on TestPyPI

Run **Publish package** from the version tag with the `repository` input set to `testpypi`. For example, from an authenticated GitHub CLI:

```bash
gh workflow run release.yml --ref v0.1.0 -f repository=testpypi
```

The workflow reruns CI and publishes only its tested Ubuntu/Python 3.12 artifacts. Run it from a version tag; branch runs intentionally skip publishing. Download just this package from TestPyPI, then resolve its dependencies from normal PyPI:

```bash
python -m pip download --no-deps --index-url https://test.pypi.org/simple/ \
  streamlit-file-explorer==0.1.0 --dest /tmp/explorer-release
python -m pip install /tmp/explorer-release/streamlit_file_explorer-0.1.0-py3-none-any.whl
```

Avoid using TestPyPI as an extra dependency index. TestPyPI may not contain your dependencies and package names there can be unrelated to PyPI owners.

## Publish to PyPI

Publishing a GitHub release for `v0.1.0` triggers the production publish job. Alternatively, dispatch the workflow from that tag with `repository=pypi`. Complete any configured environment approval.

The publisher receives a short-lived OIDC credential, downloads the artifacts from the successful verification workflow, and uploads them with provenance attestations. It does not rebuild artifacts during the publishing step. This separation follows the [PyPI Trusted Publishing guidance](https://docs.pypi.org/trusted-publishers/using-a-publisher/).

After success, verify `python -m pip install streamlit-file-explorer==0.1.0` in a fresh environment and run a small Streamlit app. Link the PyPI release in the GitHub release notes.

Published version files are immutable. Fix a faulty release with a new version and consider yanking the faulty release; never try to overwrite it. A failed name-availability or publisher-authorization check must be resolved explicitly rather than bypassed.
