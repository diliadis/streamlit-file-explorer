"""Check source versions and, optionally, an exact release tag before publication."""

import argparse
import json
import sys
from pathlib import Path

from packaging.version import Version

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def check_release(root: Path, tag: str | None = None) -> str:
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    version = project["version"]
    if str(Version(version)) != version:
        raise ValueError("Use a canonical Python package version")
    manifest = tomllib.loads((root / "streamlit_file_explorer/pyproject.toml").read_text())
    frontend = root / "streamlit_file_explorer/frontend"
    package = json.loads((frontend / "package.json").read_text())
    lock = json.loads((frontend / "package-lock.json").read_text())
    versions = [manifest["project"]["version"], package["version"], lock["version"]]
    versions.append(lock["packages"][""]["version"])
    if any(value != version for value in versions):
        raise ValueError(
            "Versions differ between Python metadata, component manifest, and npm files"
        )
    if manifest["project"]["name"] != project["name"]:
        raise ValueError("Component manifest and Python project names differ")
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Expected release tag v{version}; received {tag!r}")
    return version


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag")
    args = parser.parse_args()
    print("Validated version", check_release(Path(__file__).resolve().parents[1], args.tag))
