"""Use pip in a clean environment to test wheel and sdist installation outside the checkout."""

import importlib.metadata
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZipFile


def run(*command: str, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def check_server(python: Path, work: Path, wheel: Path) -> None:
    """Verify packaged asset discovery with the real server, including Streamlit 1.53."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    with (work / "server.log").open("w+") as log:
        process = subprocess.Popen(
            [
                str(python),
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.address=127.0.0.1",
                f"--server.port={port}",
                "--server.headless=true",
                "--server.fileWatcherType=none",
                "--browser.gatherUsageStats=false",
            ],
            cwd=work,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    raise RuntimeError(log.read())
                try:
                    with urlopen(f"{base}/_stcore/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except URLError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Streamlit did not become healthy within 30 seconds")
            with ZipFile(wheel) as archive:
                assets = [name for name in archive.namelist() if "/frontend/build/" in name]
                if not assets:
                    raise RuntimeError("No packaged frontend assets")
                for name in assets:
                    url = (
                        f"{base}/_stcore/bidi-components/"
                        f"streamlit-file-explorer.streamlit_file_explorer/{Path(name).name}"
                    )
                    with urlopen(url, timeout=5) as response:
                        if response.read() != archive.read(name):
                            raise RuntimeError(f"Served asset differs from wheel: {name}")
            print("Installed component assets served correctly by Streamlit")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


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
        # Older AppTest versions mock the v2 registry and cannot resolve packaged
        # assets. Exercise the public HTTP asset route on a real server instead.
        # Interactive browser checks remain part of the release checklist.
        app = work / "app.py"
        app.write_text(
            "import streamlit as st\n"
            "from streamlit_file_explorer import file_explorer\n"
            f"result = file_explorer({{'Files': {str(work)!r}}}, key='installed')\n"
            "st.write(result.directory.name)\n"
        )
        check_server(python, work, wheel)


if __name__ == "__main__":
    main()
