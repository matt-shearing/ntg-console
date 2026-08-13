"""JSON-line socket between the GUI and the background engine."""

from __future__ import annotations

import json
import os
import socket
import time
from pathlib import Path

STATE_DIR = Path.home() / ".local" / "state" / "ntg-console"
SOCKET_PATH = STATE_DIR / "engine.sock"


def _ensure_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


class Client:
    def __init__(self, path: Path = SOCKET_PATH) -> None:
        self.path = path

    def alive(self) -> bool:
        try:
            reply = self.request({"cmd": "ping"}, timeout=0.4)
            return reply.get("ok") is True
        except OSError:
            return False

    def wait(self, seconds: float = 3.0) -> bool:
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self.alive():
                return True
            time.sleep(0.1)
        return False

    def request(self, payload: dict, timeout: float = 2.0) -> dict:
        raw = (json.dumps(payload) + "\n").encode()
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect(str(self.path))
            sock.sendall(raw)
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
        if not buf:
            return {"ok": False, "error": "empty reply"}
        return json.loads(buf.decode())


def serve(handler, stop) -> None:
    """Accept connections until stop is set. handler(dict) -> dict."""
    _ensure_dir()
    if SOCKET_PATH.exists():
        SOCKET_PATH.unlink()
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(SOCKET_PATH))
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(8)
    server.settimeout(0.4)
    try:
        while not stop.is_set():
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            with conn:
                conn.settimeout(2.0)
                buf = b""
                try:
                    while b"\n" not in buf:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        buf += chunk
                    if not buf:
                        continue
                    req = json.loads(buf.decode())
                    reply = handler(req)
                except Exception as exc:  # noqa: BLE001
                    reply = {"ok": False, "error": str(exc)}
                conn.sendall((json.dumps(reply) + "\n").encode())
    finally:
        server.close()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()


def ensure_daemon() -> Client:
    """Start the user service (or a detached process) if it is not up.

    Does not change the default source or sink.
    """
    import subprocess
    import sys

    client = Client()
    if client.alive():
        return client
    subprocess.run(
        ["systemctl", "--user", "start", "ntg-console.service"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if client.wait(2.5):
        return client
    here = Path(__file__).resolve()
    launcher = here.parents[1] / "ntg-console"
    if launcher.is_file():
        cmd = [sys.executable, str(launcher), "daemon"]
    else:
        cmd = [sys.executable, "-m", "ntg_console", "daemon"]
    log = Path.home() / ".local" / "state" / "ntg-console" / "daemon.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as fh:
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=fh,
            stderr=subprocess.STDOUT,
        )
    client.wait(3.0)
    return client
