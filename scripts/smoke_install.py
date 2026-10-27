"""Use pip in a clean environment to test wheel and sdist installation outside the checkout."""

import importlib.metadata
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*command: str, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    (wheel,) = (root / "dist").glob("*.whl")
    (sdist,) = (root / "dist").glob("*.tar.gz")
    streamlit_version = importlib.metadata.version("streamlit")
    with tempfile.TemporaryDirectory(prefix="explorer-install-") as directory:
        work = Path(directory)
        run(sys.executable, "-m", "venv", str(work / "venv"), cwd=work)
        python = work / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            str(wheel),
            f"streamlit=={streamlit_version}",
            "pytest",
            cwd=work,
        )
        (work / "tests").mkdir()
        for path in (root / "tests").glob("*.py"):
            shutil.copy2(path, work / "tests" / path.name)
        probe = """
from importlib.metadata import version
from pathlib import Path
import sys
import streamlit_file_explorer as package
assert Path(package.__file__).is_relative_to(Path(sys.prefix))
assert package.__version__ == version('streamlit-file-explorer')
print('Installed package:', package.__file__, package.__version__)
"""
        run(str(python), "-I", "-c", probe, cwd=work)
        run(str(python), "-I", "-m", "pytest", "tests", "-q", cwd=work)
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--force-reinstall",
            "--no-deps",
            str(sdist),
            cwd=work,
        )
        run(str(python), "-I", "-c", probe, cwd=work)
        run(str(python), "-I", "-m", "pytest", "tests", "-q", cwd=work)
        run(
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--force-reinstall",
            "--no-deps",
            str(root),
            cwd=work,
        )
        run(str(python), "-I", "-c", probe, cwd=work)
        # AppTest exercises Python registration inside a real Streamlit runtime.
        # Interactive browser checks remain part of the release checklist.
        app = work / "app.py"
        app.write_text(
            "import streamlit as st\n"
            "from streamlit_file_explorer import file_explorer\n"
            f"result = file_explorer({{'Files': {str(work)!r}}}, key='installed')\n"
            "st.write(result.directory.name)\n"
        )
        run(
            str(python),
            "-I",
            "-c",
            "from streamlit.testing.v1 import AppTest; "
            "app = AppTest.from_file('app.py').run(timeout=20); "
            "assert not app.exception, app.exception; print('Installed component mounted')",
            cwd=work,
        )


if __name__ == "__main__":
    main()
