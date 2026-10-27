"""Validate both distributions, their metadata, and the bundled component assets."""

import argparse
import fnmatch
import tarfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


def validate(directory: Path) -> None:
    wheels = list(directory.glob("*.whl"))
    sources = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected exactly one wheel and one sdist")
    with ZipFile(wheels[0]) as wheel:
        names = wheel.namelist()
        prefix = "streamlit_file_explorer/"
        for required in ["__init__.py", "component.py", "pyproject.toml", "py.typed"]:
            if prefix + required not in names:
                raise ValueError(f"Missing {required}")
        for pattern in [f"{prefix}frontend/build/index-*.js", f"{prefix}frontend/build/*.css"]:
            matches = fnmatch.filter(names, pattern)
            if len(matches) != 1 or not wheel.read(matches[0]):
                raise ValueError(f"Expected exactly one nonempty asset matching {pattern}")
        if any("node_modules" in name or "frontend/src" in name for name in names):
            raise ValueError("Wheel must not contain development frontend files")
        for notice in ["LICENSE", "THIRD_PARTY_NOTICES.md"]:
            if not any(name.endswith(f".dist-info/licenses/{notice}") for name in names):
                raise ValueError(f"Missing license notice {notice}")
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(wheel.read(metadata_name))
        if metadata["Name"] != "streamlit-file-explorer":
            raise ValueError("Unexpected distribution name")
        if metadata["License-Expression"] != "Apache-2.0" or not metadata["Requires-Python"]:
            raise ValueError("Missing license or Python compatibility metadata")
        if not metadata.get_all("Project-URL"):
            raise ValueError("Missing project links")
        manifest = wheel.read(prefix + "pyproject.toml")
        if b'asset_dir = "frontend/build"' not in manifest:
            raise ValueError("Component asset manifest is missing")
        with tarfile.open(sources[0]) as source:
            root = source.getnames()[0].split("/")[0]
            for name in names:
                if name.startswith(prefix):
                    member = source.extractfile(f"{root}/{name}")
                    if member is None or member.read() != wheel.read(name):
                        raise ValueError(f"Wheel and sdist differ for {name}")
            for required in ["build_support.py", "pyproject.toml", "THIRD_PARTY_NOTICES.md"]:
                source.getmember(f"{root}/{required}")
    print(f"Validated {wheels[0].name} and {sources[0].name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", nargs="?", type=Path, default=Path("dist"))
    validate(parser.parse_args().directory)
