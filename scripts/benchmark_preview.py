"""Original-only search/filter/page/detail/media measurements in an owned DB."""

import argparse
import asyncio
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
from fraggy_api.database import create_engine, request_session_factory
from fraggy_api.main import create_app
from fraggy_api.preview import prepare
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from pydantic import SecretStr
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]


async def run(repeats: int, warmup: int) -> dict[str, Any]:
    if not 1 <= repeats <= 30 or not 0 <= warmup <= 5:
        raise ValueError("Bounded benchmark repetitions required")
    settings = Settings()
    parsed = make_url(settings.database_url.get_secret_value())
    if settings.app_env == "production" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ValueError("Nonproduction loopback PostgreSQL required")
    admin = await asyncpg.connect(
        parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    name = "fraggy_preview_" + uuid4().hex
    created = False
    engine = None
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        url = parsed.set(database=name).render_as_string(hide_password=False)
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
            env={**os.environ, "DATABASE_URL": url, "MIGRATION_DATABASE_URL": url},
            capture_output=True,
        )
        if migration.returncode:
            raise ValueError("Owned benchmark migration failed")
        with tempfile.TemporaryDirectory(prefix="fraggy-preview-bench-") as folder:
            root = Path(folder)
            config = Settings(
                app_env="test",
                database_url=SecretStr(url),
                catalog_include_synthetic=True,
                media_root=root / "media",
            )
            engine = create_engine(config)
            async with async_sessionmaker(
                engine, expire_on_commit=False
            ).begin() as session:
                fixture = await prepare(session, root, 100)
            async with engine.begin() as connection:
                await connection.execute(text("ANALYZE"))
            app = create_app(config)
            app.state.session_factory = request_session_factory(engine)
            reads = []

            def capture(
                connection: Any,
                cursor: Any,
                statement: str,
                parameters: Any,
                context: Any,
                many: Any,
            ) -> None:
                if statement.lstrip().upper().startswith(("SELECT", "WITH")):
                    reads.append(statement)

            event.listen(engine.sync_engine, "before_cursor_execute", capture)
            scenarios = {
                "search": "/api/v1/fragrances/search?q=Cedar&limit=20",
                "filter": "/api/v1/fragrances?brand=invented-house-000&concentration=eau_de_parfum&limit=20",
                "pagination": "/api/v1/fragrances?offset=20&limit=20",
                "detail": "/api/v1/fragrances/" + fixture["fragrance_id"],
                "image": "/api/v1/media/" + fixture["image_ids"][0] + "/display",
            }
            results = {}
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                for label, route in scenarios.items():
                    samples = []
                    counts = []
                    errors = []
                    for iteration in range(warmup + repeats):
                        reads.clear()
                        started = time.perf_counter()
                        response = await client.get(route)
                        elapsed = (time.perf_counter() - started) * 1000
                        if response.status_code != 200:
                            errors.append(
                                {"iteration": iteration, "status": response.status_code}
                            )
                        elif label == "image":
                            assert (
                                response.headers["content-type"] == "image/webp"
                                and response.content
                            )
                        else:
                            assert response.json()["data"]
                        if iteration >= warmup:
                            samples.append(elapsed)
                            counts.append(len(reads))
                    results[label] = {
                        "median_ms": round(statistics.median(samples), 3),
                        "p95_ms": round(
                            sorted(samples)[math.ceil(0.95 * len(samples)) - 1], 3
                        ),
                        "query_counts": counts,
                        "failures": errors,
                        "timed_requests": repeats,
                        "all_attempts": warmup + repeats,
                    }
            event.remove(engine.sync_engine, "before_cursor_execute", capture)
            return {
                "synthetic_only": True,
                "genuine_records": 0,
                "genuine_images": 0,
                "fixture_fragrances": 100,
                "fixture_images": 4,
                "repeats": repeats,
                "warmup": warmup,
                "python": platform.python_version(),
                "method": "real ASGI HTTP routing, database, projection and serialization; image includes private file read/hash; no socket/browser/CDN/network timing",
                "scenarios": results,
                "error_rate": sum(len(r["failures"]) for r in results.values())
                / ((warmup + repeats) * len(results)),
                "cleanup": "Only this invocation UUID-owned DB and original image directory removed",
            }
    finally:
        if engine is not None:
            await engine.dispose()
        if created:
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args.repeats, args.warmup))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": "Original preview benchmark failed; owned cleanup attempted",
                    "type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(result))
    if result["error_rate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
