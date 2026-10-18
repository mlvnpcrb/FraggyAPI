"""Trusted local operators only. Nothing is scheduled or fetched at app startup."""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..database import create_engine
from ..importing.formats import bounded, loads, read_text
from ..models import CollectionRun, CollectionSource
from ..settings import Settings
from .engine import Collector, activate, cancel, revoke_collection
from .policy import CollectionError, Grant, review_collection
from .transport import HTTPTransport


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review")
    review.add_argument("grant", type=Path)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--reason", required=True)
    enable = sub.add_parser("activate")
    enable.add_argument("id", type=UUID)
    enable.add_argument("--reviewer", required=True)
    enable.add_argument("--reason", required=True)
    enable.add_argument("--schedule", action="store_true")
    enable.add_argument("--interval", type=int, default=86400)
    for name in ("revoke", "cancel", "history"):
        command = sub.add_parser(name)
        command.add_argument("id", type=UUID)
        if name != "history":
            command.add_argument("--reviewer", required=True)
            command.add_argument("--reason", required=True)
    run = sub.add_parser("run")
    run.add_argument("id", type=UUID)
    run.add_argument("--allow-external", action="store_true")
    tick = sub.add_parser("tick")
    tick.add_argument("--allow-external", action="store_true")
    sub.add_parser("list")
    sub.add_parser("quality")
    return root


async def run(args: argparse.Namespace) -> Any:
    settings = Settings()
    if settings.app_env == "production" or make_url(
        settings.database_url.get_secret_value()
    ).host not in {"localhost", "127.0.0.1", "::1"}:
        raise CollectionError("nonproduction_loopback_database_required")
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    collector = Collector(
        factory, HTTPTransport(allow_external=getattr(args, "allow_external", False))
    )
    try:
        if args.command == "run":
            return await collector.run(args.id)
        if args.command == "tick":
            return await collector.tick()
        if args.command == "quality":
            return await collector.quality()
        if args.command == "history":
            async with factory() as session:
                identities = list(
                    (
                        await session.scalars(
                            select(CollectionRun.id)
                            .where(CollectionRun.collection_id == args.id)
                            .order_by(CollectionRun.started_at.desc(), CollectionRun.id)
                            .limit(50)
                        )
                    ).all()
                )
            return [await collector.summary(i) for i in identities]
        async with factory.begin() as session:
            if args.command == "review":
                body = loads(read_text(args.grant))
                bounded(body)
                grant = Grant.model_validate(body)
                config = await review_collection(
                    session, grant, args.reviewer, args.reason
                )
                return {
                    "collection_id": str(config.id),
                    "enabled": False,
                    "schedule_enabled": False,
                }
            if args.command == "activate":
                await activate(
                    session,
                    args.id,
                    args.reviewer,
                    args.reason,
                    schedule=args.schedule,
                    interval=args.interval,
                )
                return {"enabled": True, "schedule_enabled": args.schedule}
            if args.command == "revoke":
                await revoke_collection(session, args.id, args.reviewer, args.reason)
                return {"status": "revoked"}
            if args.command == "cancel":
                await cancel(session, args.id, args.reviewer, args.reason)
                return {"status": "cancel_requested"}
            rows = (
                await session.scalars(
                    select(CollectionSource).order_by(CollectionSource.id).limit(100)
                )
            ).all()
            return [
                {
                    "collection_id": str(r.id),
                    "source_id": str(r.source_id),
                    "state": r.state,
                    "enabled": r.enabled,
                    "schedule_enabled": r.schedule_enabled,
                    "interval_seconds": r.interval_seconds,
                    "next_due_at": r.next_due_at.isoformat() if r.next_due_at else None,
                    "active_run_id": str(r.current_run_id)
                    if r.current_run_id
                    else None,
                    "lease_until": r.lease_until.isoformat() if r.lease_until else None,
                }
                for r in rows
            ]
    finally:
        await engine.dispose()


def main() -> None:
    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--":
        arguments.pop(0)
    args = parser().parse_args(arguments)
    try:
        result = asyncio.run(run(args))
    except CollectionError as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(1) from None
    except Exception:
        print(json.dumps({"error": "collection_operation_failed"}))
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))
    if isinstance(result, dict) and result.get("status") in {
        "failed",
        "cancelled",
        "interrupted",
    }:
        raise SystemExit(2)
    if isinstance(result, list) and any(
        isinstance(r, dict) and r.get("status") in {"failed", "denied"} for r in result
    ):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
