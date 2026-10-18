"""Non-production loopback-only, read-only quality reports on stdout."""

import argparse
import asyncio
import json
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..database import create_engine
from ..importing.formats import ImportErrorSafe
from ..settings import Settings
from .report import catalog_quality, human_report


async def run() -> dict[str, Any]:
    config = Settings()
    if config.app_env == "production" or make_url(
        config.database_url.get_secret_value()
    ).host not in {"localhost", "127.0.0.1", "::1"}:
        raise ImportErrorSafe(
            "Quality reports require non-production loopback PostgreSQL"
        )
    engine = create_engine(config)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            result = await catalog_quality(session)
            await session.rollback()
            return result
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument(
        "--fail-on", choices=("error", "warning", "none"), default="none"
    )
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--":
        arguments = arguments[1:]
    args = parser.parse_args(arguments)
    try:
        report = asyncio.run(run())
    except ImportErrorSafe as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(1) from None
    except Exception as exc:
        print(
            json.dumps(
                {
                    "error": "Quality report failed; no changes made",
                    "type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
    print(
        json.dumps(report, ensure_ascii=True, allow_nan=False)
        if args.format == "json"
        else human_report(report),
        end="\n" if args.format == "json" else "",
    )
    errors = report["severity_counts"]["error"]
    warnings = report["severity_counts"]["warning"]
    if args.fail_on != "none" and (
        errors or not report["complete"] or (args.fail_on == "warning" and warnings)
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
