"""Real HTTP checks, optionally owning temporary API/web processes and a DB outage."""

import argparse
import os
import signal
import socket
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def request(url: str) -> tuple[int, str]:
    try:
        with urlopen(url, timeout=6) as response:
            return response.status, response.read().decode()
    except HTTPError as exc:
        return exc.code, exc.read().decode()


def wait(url: str) -> None:
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            if request(url)[0] == 200:
                return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Service did not become ready: {url}")


def check(url: str, status: int, content: str) -> None:
    actual, body = request(url)
    assert actual == status, f"{url}: expected {status}, got {actual}"
    assert content in body, f"{url}: expected content absent"
    print(f"PASS {url} -> {actual}", flush=True)


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manage-services", action="store_true")
    parser.add_argument("--check-db-outage", action="store_true")
    args = parser.parse_args()
    processes: list[subprocess.Popen[bytes]] = []
    try:
        with tempfile.TemporaryFile() as logs:
            if args.manage_services:
                for port in (3000, 8000):
                    with socket.socket() as probe:
                        try:
                            probe.bind(("127.0.0.1", port))
                        except OSError as exc:
                            raise RuntimeError(
                                f"Port {port} is occupied; stop your development server first"
                            ) from exc
                commands = [
                    [
                        str(ROOT / ".venv/bin/uvicorn"),
                        "fraggy_api.main:app",
                        "--app-dir",
                        "apps/api",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                        "--no-access-log",
                    ],
                    ["pnpm", "--filter", "@fraggy/web", "start"],
                ]
                for command in commands:
                    processes.append(
                        subprocess.Popen(
                            command,
                            cwd=ROOT,
                            stdout=logs,
                            stderr=logs,
                            start_new_session=True,
                        )
                    )
            try:
                wait("http://127.0.0.1:8000/health")
                wait("http://127.0.0.1:3000/")
                if any(p.poll() is not None for p in processes):
                    raise RuntimeError(
                        "A managed server exited; refusing to test another process"
                    )
                check("http://127.0.0.1:8000/health", 200, '"status":"ok"')
                check("http://127.0.0.1:8000/ready", 200, '"status":"ready"')
                check("http://127.0.0.1:8000/api/v1", 200, "FraggyAPI")
                check("http://127.0.0.1:8000/docs", 200, "swagger-ui")
                for path, content in [
                    ("/", "A world of scent."),
                    ("/fragrances", "Santal No. 04"),
                    ("/fragrances/santal-no-04", "Cardamom"),
                    ("/fragrances/figue-sauvage", "Fig leaf"),
                    ("/brands", "Atelier Vert"),
                    ("/fragrances?q=not-a-real-scent", "No scents found"),
                ]:
                    check("http://127.0.0.1:3000" + path, 200, content)
                check(
                    "http://127.0.0.1:3000/fragrances/unknown-scent",
                    404,
                    "A little off the trail.",
                )
                if args.check_db_outage:
                    try:
                        compose("stop", "db")
                        check(
                            "http://127.0.0.1:8000/ready", 503, '"status":"not_ready"'
                        )
                        check("http://127.0.0.1:8000/health", 200, '"status":"ok"')
                    finally:
                        compose("up", "-d", "--wait", "db")
                    wait("http://127.0.0.1:8000/ready")
                    check("http://127.0.0.1:8000/ready", 200, '"status":"ready"')
            except BaseException:
                logs.seek(0)
                print(logs.read().decode(errors="replace")[-8000:])
                raise
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)


if __name__ == "__main__":
    main()
