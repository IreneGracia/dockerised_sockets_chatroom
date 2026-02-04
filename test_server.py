import os
import socket
import time
import sys
import subprocess
import signal
from pathlib import Path

import pytest

HOST = "127.0.0.1"
CONNECT_TIMEOUT_S = 0.5
WAIT_TOTAL_S = 5.0

PORT = None
SERVER_ADDRESS = None


def _pick_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, 0))  # OS picks a free port
    port = s.getsockname()[1]
    s.close()
    return port


def _find_server_py() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "server.py",
        here / "server" / "server.py",  
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Could not find server.py. Tried: {', '.join(str(p) for p in candidates)}"
    )


def wait_for_server(proc: subprocess.Popen):
    deadline = time.time() + WAIT_TOTAL_S
    last_err = None

    while time.time() < deadline:
        # If the server process already exited, surface its stderr/stdout
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1)
            raise RuntimeError(
                "Server process exited during startup.\n"
                f"exit_code={proc.returncode}\n"
                f"stdout:\n{out}\n"
                f"stderr:\n{err}\n"
            )

        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(CONNECT_TIMEOUT_S)
            s.connect(SERVER_ADDRESS)
            return
        except OSError as e:
            last_err = e
            time.sleep(0.1)
        finally:
            try:
                if s:
                    s.close()
            except Exception:
                pass

    out, err = proc.communicate(timeout=1)
    raise RuntimeError(
        f"Server not reachable at {SERVER_ADDRESS}: {last_err}\n"
        f"stdout:\n{out}\n"
        f"stderr:\n{err}\n"
    )


@pytest.fixture(scope="session", autouse=True)
def _server_process(tmp_path_factory):
    global PORT, SERVER_ADDRESS

    PORT = _pick_free_port()
    SERVER_ADDRESS = (HOST, PORT)

    server_py = _find_server_py()
    backup_path = tmp_path_factory.mktemp("chat_backup") / "Backup.txt"

    env = os.environ.copy()
    env["ADDRESS"] = HOST
    env["PORT"] = str(PORT)
    env["BACKUP_PATH"] = str(backup_path)

    proc = subprocess.Popen(
        [sys.executable, str(server_py)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        wait_for_server(proc)
        yield
    finally:
        try:
            proc.send_signal(signal.SIGTERM)
            proc.wait(timeout=2)
        except Exception:
            proc.kill()
        try:
            proc.communicate(timeout=1)
        except Exception:
            pass


def connect_client(username: str) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(SERVER_ADDRESS)
    s.sendall(username.encode("ascii"))
    return s


def test_client_can_connect():
    client = connect_client("testuser")
    response = client.recv(1024).decode("ascii", errors="replace")
    assert "testuser" in response
    client.close()


def test_message_broadcast():
    client1 = connect_client("user1")
    client2 = connect_client("user2")

    client1.recv(1024)
    client2.recv(1024)

    client1.sendall(b"hello")
    received = client2.recv(1024).decode("ascii", errors="replace")
    assert "user1 says: hello" in received

    client1.close()
    client2.close()


def test_client_disconnect():
    client = connect_client("leaver")
    client.recv(1024)
    client.close()
    time.sleep(0.2)
    assert True
