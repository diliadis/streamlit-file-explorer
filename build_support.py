"""Setuptools hooks that prevent shipping an unusable component without its UI."""

from pathlib import Path
from shutil import rmtree

from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist
from setuptools.errors import SetupError

ASSETS = Path("streamlit_file_explorer/frontend/build")


def check_assets() -> None:
    for pattern in ("index-*.js", "*.css"):
        matches = list(ASSETS.glob(pattern))
        if len(matches) != 1 or not matches[0].stat().st_size:
            raise SetupError(
                f"Expected one nonempty {pattern} bundle in {ASSETS}. "
                "Install an official wheel/sdist or build the source with "
                "'npm --prefix streamlit_file_explorer/frontend ci' and "
                "'npm --prefix streamlit_file_explorer/frontend run build'."
            )


class CheckedBuildPy(build_py):
    def run(self) -> None:
        check_assets()
        # A previous build can leave an obsolete hashed bundle in build/lib.
        # Only clear this command's generated asset output, never source files.
        generated = Path(self.build_lib) / ASSETS
        if generated.resolve() != ASSETS.resolve() and generated.is_dir():
            rmtree(generated)
        super().run()


class CheckedSdist(sdist):
    def run(self) -> None:
        check_assets()
        super().run()
