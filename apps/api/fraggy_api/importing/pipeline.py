"""Transactional staging, manual decisions and independent publication approval."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    IngestionRun,
    SourceEntityLink,
    SourceRecord,
)
from .authorization import actor, check_storage, policy, source_for, writer_lock
from .formats import ImportErrorSafe, Manifest, Record, digest
from .matching import candidates
from .writing import materialize


async def preview(
    session: AsyncSession, records: list[Record], manifest: Manifest
) -> dict[str, Any]:
    source = await source_for(session, manifest)
    rows = []
    for number, record in enumerate(records, 1):
        reviewed = check_storage(source, manifest, record)
        match = (
            await candidates(session, record)
            if reviewed
            else {
                "classification": "rights_review_required",
                "reasons": ["no_trusted_storage_review"],
            }
        )
        rows.append(
            {
                "row": number,
                "record_digest": digest(record.model_dump(mode="json")),
                **match,
            }
        )
    return {
        "dry_run": True,
        "rows": rows,
        "review_required": len(rows),
        "canonical_writes": 0,
    }


async def stage(
    session: AsyncSession, records: list[Record], manifest: Manifest
) -> dict[str, Any]:
    """Caller owns the transaction. A failed batch leaves no rows or partial run."""
    await writer_lock(session)
    source = await source_for(session, manifest, create=True)
    assert source is not None
    now = datetime.now(UTC)
    run = IngestionRun(
        id=uuid4(),
        source_id=source.id,
        status="running",
        started_at=now,
        records_seen=len(records),
        records_accepted=0,
    )
    session.add(run)
    await session.flush()
    summary: dict[str, Any] = {
        "run_id": str(run.id),
        "inserted": 0,
        "linked": 0,
        "skipped": 0,
        "rejected": 0,
        "review_required": 0,
        "quarantined": 0,
        "records": [],
    }
    for record in records:
        reviewed = check_storage(source, manifest, record)
        content_digest = digest(record.model_dump(mode="json"))
        manifest_digest = digest(manifest.model_dump(mode="json"))
        external = (
            record.source_record_id if reviewed else "quarantine:" + content_digest
        )
        latest = await session.scalar(
            select(SourceRecord)
            .where(
                SourceRecord.source_id == source.id,
                SourceRecord.source_record_id == external,
            )
            .order_by(SourceRecord.revision.desc())
            .limit(1)
        )
        if latest is not None and (
            (
                reviewed
                and latest.payload
                and latest.payload.get("content_digest") == content_digest
                and latest.payload.get("manifest_digest") == manifest_digest
            )
            or (not reviewed and latest.payload is None)
        ):
            summary["skipped"] += 1
            summary["linked"] += int(latest.processing_state == "linked")
            summary["rejected"] += int(latest.processing_state == "rejected")
            summary["review_required"] += int(
                latest.processing_state not in {"linked", "rejected"}
            )
            summary["records"].append(str(latest.id))
            continue
        snapshot = SourceRecord(
            id=uuid4(),
            source_id=source.id,
            ingestion_run_id=run.id,
            source_record_id=external,
            source_url=record.source_url if reviewed else None,
            revision=latest.revision + 1 if latest else 1,
            collected_at=now,
            storage_status=("synthetic" if manifest.synthetic else "approved")
            if reviewed
            else "pending_review",
            storage_evidence=f"operator_source_review:{manifest_digest}"
            if reviewed
            else None,
            redistribution_status="pending_review",
            payload={
                "original": record.model_dump(mode="json"),
                "content_digest": content_digest,
                "manifest_digest": manifest_digest,
            }
            if reviewed
            else None,
        )
        session.add(snapshot)
        await session.flush()
        match = (
            await candidates(session, record)
            if reviewed
            else {
                "classification": "rights_review_required",
                "reasons": ["no_trusted_storage_review"],
            }
        )
        session.add(
            DataReviewQueue(
                id=uuid4(),
                source_record_id=snapshot.id,
                reason="File import requires operator decision",
                context={
                    "run_id": str(run.id),
                    "manifest_digest": manifest_digest,
                    "record_digest": content_digest,
                    "match": match,
                    "history": [],
                },
            )
        )
        summary["inserted"] += 1
        summary["review_required"] += 1
        summary["quarantined"] += int(not bool(reviewed))
        summary["records"].append(str(snapshot.id))
    run.records_accepted = summary["inserted"]
    run.status = "succeeded"
    run.completed_at = datetime.now(UTC)
    source.last_successful_sync = run.completed_at
    await session.flush()
    return summary


async def snapshot_data(
    session: AsyncSession, identity: UUID
) -> tuple[SourceRecord, DataSource, Manifest, Record]:
    snapshot = await session.get(SourceRecord, identity)
    if (
        snapshot is None
        or snapshot.payload is None
        or snapshot.storage_status not in {"approved", "synthetic"}
    ):
        raise ImportErrorSafe(
            "Stored authorized snapshot required; reimport after source review"
        )
    source = await session.get(DataSource, snapshot.source_id)
    assert source is not None
    if source.source_type not in {"file_import", "synthetic_file_import"}:
        raise ImportErrorSafe("File-import source required")
    entries = [e for e in source.evidence if e.get("kind") == "operator_source_review"]
    if not entries:
        raise ImportErrorSafe("Trusted source review missing")
    manifest = Manifest.model_validate(entries[-1]["manifest"])
    if policy(source, manifest) is None or snapshot.payload.get(
        "manifest_digest"
    ) != digest(manifest.model_dump(mode="json")):
        raise ImportErrorSafe(
            "Source review changed; reimport before decision/publication"
        )
    return (
        snapshot,
        source,
        manifest,
        Record.model_validate(snapshot.payload["original"]),
    )


async def decide(
    session: AsyncSession,
    review_id: UUID,
    decision: str,
    reviewer: str,
    reason: str,
    target: UUID | None = None,
) -> dict[str, Any]:
    actor(reviewer, reason)
    if decision not in {
        "approve_new",
        "link_existing",
        "separate_release",
        "reject",
        "defer",
    }:
        raise ImportErrorSafe("Unsupported review decision")
    if target is not None and decision not in {"link_existing", "separate_release"}:
        raise ImportErrorSafe(
            "Target release is only valid for linking or a separate release"
        )
    await writer_lock(session)
    item = await session.get(DataReviewQueue, review_id, with_for_update=True)
    if item is None or item.status != "pending":
        raise ImportErrorSafe(
            "Pending review item required; resolved decisions cannot be overwritten"
        )
    snapshot = await session.get(SourceRecord, item.source_record_id)
    assert snapshot is not None
    owner = await session.get(DataSource, snapshot.source_id)
    if owner is None or owner.source_type not in {
        "file_import",
        "synthetic_file_import",
    }:
        raise ImportErrorSafe("File-import review item required")
    if snapshot.processing_state in {"linked", "rejected"}:
        raise ImportErrorSafe("Snapshot already has a final decision")
    now = datetime.now(UTC)
    result: dict[str, Any] = {
        "decision": decision,
        "record_id": str(snapshot.id),
        "inserted": 0,
        "linked": 0,
        "skipped": 0,
        "rejected": 0,
        "review_required": int(decision == "defer"),
    }
    if decision == "reject":
        snapshot.processing_state = "rejected"
        result["rejected"] = 1
    elif decision != "defer":
        snapshot, _, _, record = await snapshot_data(session, snapshot.id)
        release = await materialize(session, snapshot, record, decision, target)
        result["release_id"] = str(release.id)
        result["linked" if decision == "link_existing" else "inserted"] = 1
        item.release_id = release.id
    event = {
        "decision": decision,
        "reviewer": reviewer,
        "at": now.isoformat(),
        "reason": reason,
        "target": str(target) if target else None,
        "result": result,
    }
    item.context = {
        **item.context,
        "history": [*item.context.get("history", []), event],
    }
    item.reviewer = reviewer
    item.resolution = reason
    item.resolved_at = now
    if decision != "defer":
        item.status = "dismissed" if decision == "reject" else "resolved"
    await session.flush()
    return result


async def publish(
    session: AsyncSession,
    record_id: UUID,
    fields: list[str],
    reviewer: str,
    reason: str,
) -> dict[str, Any]:
    actor(reviewer, reason)
    await writer_lock(session)
    snapshot, source, manifest, _ = await snapshot_data(session, record_id)
    if (
        snapshot.processing_state != "linked"
        or source.licensing_status not in {"approved", "synthetic"}
        or manifest.attribution_requirements
    ):
        raise ImportErrorSafe("Reviewed linked record and publication policy required")
    fields = sorted(set(fields))
    if not fields or not set(fields) <= set(source.permitted_fields):
        raise ImportErrorSafe(
            "Explicit publication fields must be allowed by operator-reviewed source policy"
        )
    evidence_id = uuid4()
    evidence = f"operator_publication:{evidence_id}"
    links = select(SourceEntityLink.id).where(
        SourceEntityLink.source_record_id == snapshot.id,
        SourceEntityLink.review_status == "approved",
    )
    result = await session.execute(
        update(FieldProvenance)
        .where(
            FieldProvenance.entity_link_id.in_(links),
            FieldProvenance.selection_status == "selected",
            FieldProvenance.value_state == "known",
            FieldProvenance.field_path.in_(fields),
        )
        .values(
            usage_rights_status="synthetic" if manifest.synthetic else "approved",
            rights_evidence=evidence,
        )
    )
    snapshot.redistribution_status = "synthetic" if manifest.synthetic else "approved"
    snapshot.redistribution_evidence = evidence
    session.add(
        DataReviewQueue(
            id=evidence_id,
            source_record_id=snapshot.id,
            reason="Explicit field publication approval",
            status="resolved",
            reviewer=reviewer,
            resolution=reason,
            resolved_at=datetime.now(UTC),
            context={
                "decision": "publish",
                "fields": fields,
                "manifest_digest": digest(manifest.model_dump(mode="json")),
            },
        )
    )
    await session.flush()
    return {
        "record_id": str(snapshot.id),
        "publication_fields": fields,
        "approved_claims": getattr(result, "rowcount", 0),
    }
