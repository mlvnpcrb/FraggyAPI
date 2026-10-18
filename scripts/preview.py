"""Run a loopback-only, original synthetic catalog in an owned disposable DB."""

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen
from uuid import uuid4

import asyncpg
from fraggy_api.database import create_engine
from fraggy_api.preview import prepare
from fraggy_api.settings import Settings
from pydantic import SecretStr
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--synthetic",
        action="store_true",
        required=True,
        help="Explicitly authorize original fixture creation and local publication only",
    )
    result.add_argument("--size", type=int, choices=(20, 100), default=100)
    result.add_argument("--api-port", type=int, default=8000)
    result.add_argument("--web-port", type=int, default=3000)
    result.add_argument(
        "--report", type=Path, default=ROOT / "data/reports/local-preview.json"
    )
    return result


def ports(api: int, web: int) -> None:
    if api == web or any(not 1024 <= value <= 65535 for value in (api, web)):
        raise ValueError("Distinct unprivileged ports required")
    for port in (api, web):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))


def wait(url: str, process: subprocess.Popen[bytes]) -> None:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            pass
        time.sleep(0.2)
    raise RuntimeError("Preview service failed readiness")


async def run(args: argparse.Namespace) -> None:
    settings = Settings()
    parsed = make_url(settings.database_url.get_secret_value())
    if (
        not args.synthetic
        or settings.app_env == "production"
        or parsed.host not in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("Explicit synthetic, nonproduction loopback preview required")
    ports(args.api_port, args.web_port)
    # Never drop/migrate the application's configured database. Only this name
    # generated in this invocation is eligible for finally cleanup.
    name = "fraggy_preview_" + uuid4().hex
    admin = await asyncpg.connect(
        parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    created = False
    processes: list[subprocess.Popen[bytes]] = []
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        with tempfile.TemporaryDirectory(
            prefix=name + "-", dir=ROOT / "data/private"
        ) as folder:
            directory = Path(folder)
            url = parsed.set(database=name).render_as_string(hide_password=False)
            environment = {
                **os.environ,
                "DATABASE_URL": url,
                "MIGRATION_DATABASE_URL": url,
                "APP_ENV": "development",
                "CATALOG_INCLUDE_SYNTHETIC": "true",
                "MEDIA_ROOT": str(directory / "media"),
                "API_BASE_URL": f"http://127.0.0.1:{args.api_port}/api/v1",
                "NEXT_TELEMETRY_DISABLED": "1",
            }
            migration = await asyncio.to_thread(
                subprocess.run,
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "apps/api/alembic.ini",
                    "upgrade",
                    "head",
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
            )
            if migration.returncode:
                raise RuntimeError("Owned preview migration failed")
            engine = create_engine(
                Settings(
                    app_env="test",
                    database_url=SecretStr(url),
                    media_root=directory / "media",
                )
            )
            async with async_sessionmaker(
                engine, expire_on_commit=False
            ).begin() as session:
                fixture = await prepare(session, directory, args.size)
            commands = [
                [
                    str(ROOT / ".venv/bin/uvicorn"),
                    "fraggy_api.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(args.api_port),
                    "--no-access-log",
                ],
                [
                    "pnpm",
                    "--filter",
                    "@fraggy/web",
                    "exec",
                    "next",
                    "dev",
                    "--hostname",
                    "127.0.0.1",
                    "--port",
                    str(args.web_port),
                ],
            ]
            log_handles = []
            try:
                for i, command in enumerate(commands):
                    handle = (directory / f"service-{i}.log").open("wb")
                    log_handles.append(handle)
                    processes.append(
                        subprocess.Popen(
                            command,
                            cwd=ROOT,
                            env=environment,
                            stdout=handle,
                            stderr=handle,
                            start_new_session=True,
                        )
                    )
                api = f"http://127.0.0.1:{args.api_port}"
                web = f"http://127.0.0.1:{args.web_port}"
                await asyncio.to_thread(wait, api + "/ready", processes[0])
                await asyncio.to_thread(wait, web + "/fragrances", processes[1])
                report: dict[str, Any] = {
                    "running": True,
                    "supervisor_pid": os.getpid(),
                    "api_pid": processes[0].pid,
                    "web_pid": processes[1].pid,
                    "synthetic_only": True,
                    "database_name": name,
                    "private_directory": str(directory),
                    "api": api,
                    "frontend": web,
                    "docs": api + "/docs",
                    "health": api + "/health",
                    "ready": api + "/ready",
                    "external_accessible": False,
                    "forwarded_url": None,
                    **fixture,
                }
                args.report.parent.mkdir(parents=True, exist_ok=True)
                args.report.write_text(json.dumps(report, indent=2) + "\n")
                os.chmod(args.report, 0o600)
                print(
                    json.dumps(
                        {
                            key: value
                            for key, value in report.items()
                            if key not in {"private_directory"}
                        }
                    ),
                    flush=True,
                )
                # Signal handlers allow finally cleanup; no process is daemonized.
                stop = asyncio.Event()
                loop = asyncio.get_running_loop()
                for signum in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(signum, stop.set)
                while not stop.is_set():
                    if any(process.poll() is not None for process in processes):
                        raise RuntimeError("Owned preview service exited")
                    try:
                        await asyncio.wait_for(stop.wait(), timeout=1)
                    except TimeoutError:
                        pass
            finally:
                for process in reversed(processes):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGTERM)
                for process in processes:
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                for handle in log_handles:
                    handle.close()
                if args.report.exists():
                    # State cannot be mistaken for a currently running preview.
                    args.report.write_text(
                        json.dumps({"running": False, "synthetic_only": True}) + "\n"
                    )
    finally:
        if engine is not None:
            await engine.dispose()
        if created:
            if admin.is_closed():
                admin = await asyncpg.connect(
                    parsed.set(drivername="postgresql").render_as_string(
                        hide_password=False
                    )
                )
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()


def main() -> None:
    args = parser().parse_args()
    (ROOT / "data/private").mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        asyncio.run(run(args))
    except Exception:
        print(
            "Preview stopped or refused; verify nonproduction settings, free ports, migrations and fixture checks.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
