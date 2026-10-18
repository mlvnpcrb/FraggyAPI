"""Explicit local synthetic benchmark; creates/drops only its UUID-owned databases."""

import argparse
import asyncio
import gc
import json
import math
import os
import platform
import resource
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import asyncpg
from fraggy_api.catalog_api import CatalogQuery, catalog
from fraggy_api.database import create_engine, request_session_factory
from fraggy_api.importing.formats import ImportErrorSafe
from fraggy_api.public_rights import read_access
from fraggy_api.quality.benchmark_data import generate
from fraggy_api.settings import Settings
from pydantic import SecretStr
from sqlalchemy import event, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]


async def measure(url: str, size: int, repeats: int, warmup: int) -> dict[str, Any]:
    config = Settings(
        app_env="test", database_url=SecretStr(url), catalog_include_synthetic=True
    )
    engine = create_engine(config)
    factory = request_session_factory(engine)
    try:
        started = time.perf_counter()
        async with (
            async_sessionmaker(engine, expire_on_commit=False)() as session,
            session.begin(),
        ):
            fixture = await generate(session, size)
        gc.collect()
        async with engine.begin() as connection:
            await connection.execute(text("ANALYZE"))
            version = await connection.scalar(text("SELECT version()"))
            pg_settings = dict(
                (
                    await connection.execute(
                        text(
                            "SELECT name,setting FROM pg_settings WHERE name IN ('shared_buffers','work_mem','max_connections')"
                        )
                    )
                )
                .tuples()
                .all()
            )
        loaded_ms = (time.perf_counter() - started) * 1000
        scenarios = {
            "search": CatalogQuery(q="Cedar", limit=20),
            "filter": CatalogQuery(
                concentration="eau_de_parfum",
                year=2020,
                notes=[fixture["note_id"]],
                limit=20,
            ),
            "pagination": CatalogQuery(
                offset=min(size - 20, 500), limit=20, sort="name"
            ),
        }
        results = {}
        for name, params in scenarios.items():
            samples = []
            query_counts = []
            captured: list[tuple[str, Any]] = []

            def capture(
                conn: Any,
                cursor: Any,
                statement: str,
                parameters: Any,
                context: Any,
                many: Any,
            ) -> None:
                if statement.lstrip().upper().startswith(("SELECT", "WITH")):
                    captured.append((statement, parameters))

            event.listen(engine.sync_engine, "before_cursor_execute", capture)
            failures = []
            total = returned = 0
            try:
                for iteration in range(warmup + repeats):
                    captured.clear()
                    started = time.perf_counter()
                    try:
                        async with factory() as session:
                            access = await read_access(session, True)
                            page = await catalog(session, params, access)
                            payload = page.model_dump(mode="json")
                            returned = len(payload["data"])
                            total = page.pagination.total
                            assert returned and all(
                                f["synthetic"] and f["attributions"]
                                for f in payload["data"]
                            )
                        elapsed = (time.perf_counter() - started) * 1000
                        if iteration >= warmup:
                            samples.append(elapsed)
                            query_counts.append(len(captured))
                    except Exception as exc:
                        failures.append(
                            {
                                "iteration": iteration,
                                "type": type(exc).__name__,
                                "elapsed_ms": round(
                                    (time.perf_counter() - started) * 1000, 3
                                ),
                            }
                        )
                        break
                peak = 0
                if not failures:
                    # Allocation tracing materially distorts latency. Measure a
                    # separate untimed request, never the latency samples.
                    captured.clear()
                    tracemalloc.start()
                    async with factory() as memory_session:
                        memory_access = await read_access(memory_session, True)
                        memory_page = await catalog(
                            memory_session, params, memory_access
                        )
                        memory_page.model_dump(mode="json")
                    _, peak = tracemalloc.get_traced_memory()
            finally:
                if tracemalloc.is_tracing():
                    tracemalloc.stop()
                event.remove(engine.sync_engine, "before_cursor_execute", capture)
            plans = []
            if not failures:
                async with factory() as session:
                    for index, (statement, parameters) in enumerate(captured):
                        started = time.perf_counter()
                        connection = await session.connection()
                        result = await connection.exec_driver_sql(
                            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement,
                            parameters,
                        )
                        plan = result.scalar_one()
                        if isinstance(plan, str):
                            plan = json.loads(plan)
                        plans.append(
                            {
                                "query": index + 1,
                                "wall_ms": round(
                                    (time.perf_counter() - started) * 1000, 3
                                ),
                                "explain": plan,
                            }
                        )
            sorted_samples = sorted(samples)
            results[name] = {
                "samples_ms": [round(n, 3) for n in samples],
                "median_ms": round(statistics.median(samples), 3) if samples else None,
                "p95_ms": round(sorted_samples[math.ceil(len(samples) * 0.95) - 1], 3)
                if samples
                else None,
                "min_ms": round(min(samples), 3) if samples else None,
                "max_ms": round(max(samples), 3) if samples else None,
                "query_counts": query_counts,
                "matched": total,
                "returned": returned,
                "python_peak_bytes": peak,
                "failures": failures,
                "plans": plans,
            }
            print(
                json.dumps(
                    {
                        "size": size,
                        "scenario": name,
                        "median_ms": results[name]["median_ms"],
                        "p95_ms": results[name]["p95_ms"],
                        "query_counts": query_counts,
                        "failures": failures,
                    }
                ),
                flush=True,
            )
        return {
            "size": size,
            "fixture": fixture,
            "fixture_load_ms": round(loaded_ms, 3),
            "postgresql": version,
            "postgresql_settings": pg_settings,
            "scenarios": results,
            "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        }
    finally:
        await engine.dispose()


async def run(args: argparse.Namespace) -> dict[str, Any]:
    config = Settings()
    parsed = make_url(config.database_url.get_secret_value())
    if config.app_env == "production" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise ImportErrorSafe("Benchmarks require non-production loopback PostgreSQL")
    sizes = [int(v) for v in args.sizes.split(",")]
    if (
        not sizes
        or len(sizes) > 3
        or len(set(sizes)) != len(sizes)
        or any(not 20 <= n <= 10000 for n in sizes)
        or not 1 <= args.repeats <= 30
        or not 0 <= args.warmup <= 5
    ):
        raise ImportErrorSafe("Invalid bounded benchmark parameters")
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "synthetic_only": True,
        "statement_timeout_seconds": config.database_timeout_seconds,
        "repeats": args.repeats,
        "warmup": args.warmup,
        "method": "in-process real API query/projection/DTO serialization; warm local PostgreSQL; no HTTP/network/browser timing",
        "results": [],
    }
    admin = await asyncpg.connect(
        parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    try:
        for size in sizes:
            name = "fraggy_bench_" + uuid4().hex
            await admin.execute(f'CREATE DATABASE "{name}"')
            try:
                url = parsed.set(database=name).render_as_string(hide_password=False)
                environment = {
                    **os.environ,
                    "DATABASE_URL": url,
                    "MIGRATION_DATABASE_URL": url,
                    "APP_ENV": "test",
                }
                result = await asyncio.to_thread(
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
                    text=True,
                )
                if result.returncode:
                    raise ImportErrorSafe("Disposable benchmark migration failed")
                output["results"].append(
                    await measure(url, size, args.repeats, args.warmup)
                )
            finally:
                await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
    finally:
        await admin.close()
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100,1000,10000")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = asyncio.run(run(args))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Explicitly requested local benchmark artifact; contains synthetic plans
        # only, no connection strings, query parameters or private source evidence.
        args.output.write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": "Benchmark failed; owned database cleanup attempted",
                    "type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
    if any(s["failures"] for r in output["results"] for s in r["scenarios"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
