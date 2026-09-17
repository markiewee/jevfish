import os
import re
import signal
import socket
import subprocess
import sys

import pytest

from jevfish.config import PACKAGE_ROOT

LAUNCH = PACKAGE_ROOT / "launcher" / "launch.sh"
mac_only = pytest.mark.skipif(sys.platform != "darwin", reason="Mac launcher")

FAKE_SERVER = """#!{python}
import http.server, json, os, sys
port = int(sys.argv[sys.argv.index("--port") + 1])
open({pidfile!r}, "a").write(str(os.getpid()) + "\\n")
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({{"app": "jevfish", "ok": True}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""

FAKE_UV = """#!/bin/sh
echo "uv $*" >> "{calls}"
mkdir -p .venv/bin
cp "{server}" .venv/bin/jevfish
chmod +x .venv/bin/jevfish
"""


def test_built_web_app_is_present():
    dist = PACKAGE_ROOT / "web" / "dist"
    html = (dist / "index.html").read_text()
    assets = re.findall(r'(?:src|href)="/(assets/[^"]+)"', html)
    assert assets and all((dist / a).is_file() for a in assets)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def sandbox(tmp_path):
    root = tmp_path / "repo"
    jf = root / "jevfish"
    (jf / "web" / "dist").mkdir(parents=True)
    (jf / "web" / "dist" / "index.html").write_text("<p>app</p>")
    (jf / "pyproject.toml").write_text("")
    (jf / "uv.lock").write_text("")
    server = tmp_path / "fake-server"
    pidfile = tmp_path / "pids"
    server.write_text(FAKE_SERVER.format(python=sys.executable, pidfile=str(pidfile)))
    server.chmod(0o755)
    calls = tmp_path / "uv-calls"
    uv = tmp_path / "fake-uv"
    uv.write_text(FAKE_UV.format(calls=calls, server=server))
    uv.chmod(0o755)
    home = tmp_path / "home"
    env = {
        "HOME": str(home), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "JEVFISH_EXTRA_PATH": "",
        "JEVFISH_NO_GUI": "1", "JEVFISH_NO_OPEN": "1", "JEVFISH_PORTS": str(free_port()),
    }
    box = dict(root=root, jf=jf, uv=uv, calls=calls, env=env, home=home,
               state=home / "Library" / "Application Support" / "JevFish",
               log=home / "Library" / "Logs" / "JevFish" / "launcher.log")
    yield box
    if pidfile.exists():
        for pid in pidfile.read_text().split():
            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass


def launch(box, **extra):
    return subprocess.run(["/bin/bash", str(LAUNCH), str(box["root"])], env={**box["env"], **extra}, timeout=90)


@mac_only
def test_first_start_installs_then_second_reuses(sandbox):
    (sandbox["state"] / "bin").mkdir(parents=True)
    (sandbox["state"] / "bin" / "uv").symlink_to(sandbox["uv"])
    assert launch(sandbox).returncode == 0
    log = sandbox["log"].read_text()
    port = sandbox["env"]["JEVFISH_PORTS"]
    assert f"ready http://127.0.0.1:{port}/" in log
    assert sandbox["calls"].read_text().strip() == "uv sync --frozen"
    assert (sandbox["jf"] / ".venv" / ".jevfish-synced").exists()
    assert (sandbox["state"] / "repo-path").read_text().strip() == str(sandbox["root"])
    assert launch(sandbox).returncode == 0
    assert f"already running on {port}" in sandbox["log"].read_text()
    assert sandbox["calls"].read_text().count("sync") == 1


@mac_only
def test_installs_uv_when_missing(sandbox, tmp_path):
    installer = tmp_path / "install.sh"
    installer.write_text(f'#!/bin/sh\nmkdir -p "$UV_INSTALL_DIR"\ncp "{sandbox["uv"]}" "$UV_INSTALL_DIR/uv"\n')
    assert launch(sandbox, JEVFISH_UV_INSTALLER=f"file://{installer}").returncode == 0
    log = sandbox["log"].read_text()
    assert "Installing uv" in log and "ready http://" in log
    assert (sandbox["state"] / "bin" / "uv").exists()


@mac_only
def test_missing_files_fail_cleanly(sandbox):
    (sandbox["jf"] / "pyproject.toml").unlink()
    assert launch(sandbox).returncode == 1
    assert "error: The JevFish files are missing" in sandbox["log"].read_text()
