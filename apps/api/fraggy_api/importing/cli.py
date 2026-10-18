"""Trusted local operator entry point, deliberately absent from FastAPI routers."""

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..database import create_engine
from ..models import (
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    FragranceRelease,
    IngestionRun,
    SourceEntityLink,
    SourceRecord,
)
from ..settings import Settings
from .authorization import review_source, revoke
from .formats import ImportErrorSafe, manifest_file, parse_file
from .pipeline import decide, preview, publish, stage


class ImportBatchFailure(ImportErrorSafe):
    def __init__(self, completed: list[dict[str, Any]], row: int):
        super().__init__(
            "Import batch rolled back; rerun the identical file to resume safely"
        )
        self.completed = completed
        self.row = row


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Local rights-aware catalog operator; no HTTP upload endpoint"
    )
    commands = root.add_subparsers(dest="command", required=True)
    load = commands.add_parser("import")
    load.add_argument("--file", type=Path, required=True)
    load.add_argument("--manifest", type=Path, required=True)
    load.add_argument("--dry-run", action="store_true")
    load.add_argument("--batch-size", type=int, default=100)
    source = commands.add_parser("source-review")
    source.add_argument("--manifest", type=Path, required=True)
    source.add_argument("--allow-storage", action="store_true")
    source.add_argument("--publish-fields", default="")
    revocation = commands.add_parser("revoke")
    revocation.add_argument("--source", required=True)
    review = commands.add_parser("review")
    review.add_argument("--review-id", type=UUID, required=True)
    review.add_argument(
        "--decision",
        choices=["approve_new", "link_existing", "separate_release", "reject", "defer"],
        required=True,
    )
    review.add_argument("--target-release", type=UUID)
    publication = commands.add_parser("publish")
    publication.add_argument("--record-id", type=UUID, required=True)
    publication.add_argument("--fields", required=True)
    for command in (source, revocation, review, publication):
        command.add_argument("--reviewer", required=True)
        command.add_argument("--reason", required=True)
    pending = commands.add_parser("pending")
    pending.add_argument("--source")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--record-id", type=UUID, required=True)
    results = commands.add_parser("results")
    results.add_argument("--run-id", type=UUID, required=True)
    permissions = commands.add_parser("source-status")
    permissions.add_argument("--source", required=True)
    provenance = commands.add_parser("provenance")
    provenance.add_argument("--fragrance-id", type=UUID, required=True)
    for command in (pending, results, provenance):
        command.add_argument("--limit", type=int, default=50)
        command.add_argument("--offset", type=int, default=0)
    return root


async def run(args: argparse.Namespace) -> dict[str, Any]:
    settings = Settings()
    if settings.app_env == "production" or make_url(
        settings.database_url.get_secret_value()
    ).host not in {"localhost", "127.0.0.1", "::1"}:
        raise ImportErrorSafe(
            "Phase 2C operator CLI is restricted to non-production loopback PostgreSQL"
        )
    if hasattr(args, "limit") and (
        not 1 <= args.limit <= 100 or not 0 <= args.offset <= 10000
    ):
        raise ImportErrorSafe("Invalid operator pagination")
    engine = create_engine(settings)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        if args.command == "import":
            if not 1 <= args.batch_size <= 200:
                raise ImportErrorSafe("Batch size must be 1–200")
            manifest, records = manifest_file(args.manifest), parse_file(args.file)
            if args.dry_run:
                async with factory() as session:
                    result = await preview(session, records, manifest)
                    await session.rollback()
                    return result
            batches = []
            for offset in range(0, len(records), args.batch_size):
                try:
                    async with factory() as session, session.begin():
                        batches.append(
                            await stage(
                                session,
                                records[offset : offset + args.batch_size],
                                manifest,
                            )
                        )
                except Exception:
                    raise ImportBatchFailure(batches, offset + 1) from None
            return {
                "batches": batches,
                "summary": {
                    key: sum(b[key] for b in batches)
                    for key in [
                        "inserted",
                        "linked",
                        "skipped",
                        "rejected",
                        "review_required",
                        "quarantined",
                    ]
                },
            }
        async with factory() as session, session.begin():
            if args.command == "source-review":
                source = await review_source(
                    session,
                    manifest_file(args.manifest),
                    args.reviewer,
                    args.reason,
                    allow_storage=args.allow_storage,
                    publish_fields=[
                        s.strip() for s in args.publish_fields.split(",") if s.strip()
                    ],
                )
                return {
                    "source_id": source.key,
                    "storage_authorization": source.authorization_status,
                    "publication_status": source.licensing_status,
                }
            if args.command == "review":
                return await decide(
                    session,
                    args.review_id,
                    args.decision,
                    args.reviewer,
                    args.reason,
                    args.target_release,
                )
            if args.command == "publish":
                return await publish(
                    session,
                    args.record_id,
                    [s.strip() for s in args.fields.split(",") if s.strip()],
                    args.reviewer,
                    args.reason,
                )
            if args.command == "revoke":
                await revoke(session, args.source, args.reviewer, args.reason)
                return {"source_id": args.source, "publication": "revoked"}
            if args.command == "pending":
                statement = (
                    select(DataReviewQueue)
                    .join(SourceRecord)
                    .join(DataSource, DataSource.id == SourceRecord.source_id)
                    .where(
                        DataReviewQueue.status == "pending",
                        DataSource.source_type.in_(
                            ["file_import", "synthetic_file_import"]
                        ),
                    )
                )
                if args.source:
                    statement = statement.where(DataSource.key == args.source)
                items = (
                    await session.scalars(
                        statement.order_by(
                            DataReviewQueue.created_at, DataReviewQueue.id
                        )
                        .limit(args.limit)
                        .offset(args.offset)
                    )
                ).all()
                return {
                    "reviews": [
                        {
                            "id": str(item.id),
                            "record_id": str(item.source_record_id),
                            "reason": item.reason,
                            "context": item.context,
                        }
                        for item in items
                    ]
                }
            if args.command == "inspect":
                record = await session.get(SourceRecord, args.record_id)
                if record is None:
                    raise ImportErrorSafe("Record not found")
                return {
                    "record_id": str(record.id),
                    "source_id": str(record.source_id),
                    "revision": record.revision,
                    "processing_state": record.processing_state,
                    "storage_status": record.storage_status,
                    "redistribution_status": record.redistribution_status,
                    "payload": record.payload
                    if record.storage_status in {"approved", "synthetic"}
                    else None,
                }
            if args.command == "results":
                run = await session.get(IngestionRun, args.run_id)
                if run is None:
                    raise ImportErrorSafe("Run not found")
                imported_records = (
                    await session.scalars(
                        select(SourceRecord)
                        .where(SourceRecord.ingestion_run_id == run.id)
                        .order_by(SourceRecord.id)
                        .limit(args.limit)
                        .offset(args.offset)
                    )
                ).all()
                return {
                    "run_id": str(run.id),
                    "status": run.status,
                    "seen": run.records_seen,
                    "accepted": run.records_accepted,
                    "records": [
                        {"id": str(r.id), "state": r.processing_state}
                        for r in imported_records
                    ],
                }
            if args.command == "source-status":
                inspected_source = await session.scalar(
                    select(DataSource).where(
                        DataSource.key == args.source,
                        DataSource.source_type.in_(
                            ["file_import", "synthetic_file_import"]
                        ),
                    )
                )
                if inspected_source is None:
                    raise ImportErrorSafe("File-import source not found")
                return {
                    "source": inspected_source.key,
                    "authorization": inspected_source.authorization_status,
                    "licensing": inspected_source.licensing_status,
                    "permitted_fields": inspected_source.permitted_fields,
                    "reviews": inspected_source.evidence,
                }
            releases = select(FragranceRelease.id).where(
                FragranceRelease.fragrance_id == args.fragrance_id
            )
            record_ids = select(SourceEntityLink.source_record_id).where(
                or_(
                    SourceEntityLink.fragrance_id == args.fragrance_id,
                    SourceEntityLink.release_id.in_(releases),
                )
            )
            rows = (
                await session.execute(
                    select(FieldProvenance, SourceEntityLink.source_record_id)
                    .join(SourceEntityLink)
                    .where(SourceEntityLink.source_record_id.in_(record_ids))
                    .order_by(FieldProvenance.id)
                    .limit(args.limit)
                    .offset(args.offset)
                )
            ).all()
            return {
                "claims": [
                    {
                        "id": str(c.id),
                        "record_id": str(record_id),
                        "field": c.field_path,
                        "value": c.value,
                        "state": c.value_state,
                        "selection": c.selection_status,
                        "rights": c.usage_rights_status,
                        "collected_at": c.collected_at.isoformat(),
                        "transformations": c.transformations,
                    }
                    for c, record_id in rows
                ]
            }
    finally:
        await engine.dispose()


def main() -> None:
    import sys

    arguments = sys.argv[1:]
    if arguments and arguments[0] == "--":
        arguments.pop(0)
    # pnpm forwards an optional literal '--'; accept the documented convention.
    args = parser().parse_args(
        [
            value
            for index, value in enumerate(arguments)
            if not (index == 1 and value == "--")
        ]
    )
    try:
        result = asyncio.run(run(args))
    except ImportBatchFailure as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "failed_batch_start_row": exc.row,
                    "completed_batches": exc.completed,
                }
            )
        )
        raise SystemExit(1) from None
    except ImportErrorSafe as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(1) from None
    except Exception as exc:
        # SQL, file content, credentials and exception messages stay out of reports.
        print(
            json.dumps(
                {
                    "error": "Catalog operation failed; transaction rolled back for the current batch",
                    "type": type(exc).__name__,
                }
            )
        )
        raise SystemExit(1) from None
    print(json.dumps(result, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
