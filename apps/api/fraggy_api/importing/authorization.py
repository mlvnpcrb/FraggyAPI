"""Operator-owned authorization. File claims never authorize themselves."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    SourceEntityLink,
    SourceRecord,
)
from .formats import ImportErrorSafe, Manifest, Record, digest


# A single transaction-scoped lock serializes these trusted writers, including
# cross-source canonical review. No additional lock service or table is needed.
async def writer_lock(session: AsyncSession) -> None:
    await session.execute(text("SELECT pg_advisory_xact_lock(70422319)"))


def actor(reviewer: str, reason: str) -> None:
    if (
        not reviewer.strip()
        or not reason.strip()
        or len(reviewer) > 100
        or len(reason) > 1000
    ):
        raise ImportErrorSafe("Reviewer and bounded reason are required")


async def source_for(
    session: AsyncSession, manifest: Manifest, *, create: bool = False
) -> DataSource | None:
    # The seven candidate websites cannot be enabled through a file-import review.
    import json
    from pathlib import Path

    reserved = json.loads(
        (Path(__file__).resolve().parents[4] / "config/sources.json").read_text()
    )["sources"]
    if manifest.source_id in {s["id"] for s in reserved}:
        raise ImportErrorSafe("Website sources are outside the file-import workflow")
    source = await session.scalar(
        select(DataSource).where(DataSource.key == manifest.source_id)
    )
    expected_type = "synthetic_file_import" if manifest.synthetic else "file_import"
    if source is not None and source.source_type != expected_type:
        raise ImportErrorSafe("Source identity is not a file-import source")
    if source is None and create:
        source = DataSource(
            id=uuid4(),
            key=manifest.source_id,
            name=manifest.source_name,
            website="https://example.invalid/local-file",
            source_type=expected_type,
            enabled=False,
        )
        session.add(source)
        await session.flush()
    return source


def policy(source: DataSource | None, manifest: Manifest) -> dict[str, Any] | None:
    if source is None or source.authorization_status not in {"approved", "synthetic"}:
        return None
    # Only this trusted DB event (not file statuses or license URLs) is authority.
    entries = [e for e in source.evidence if e.get("kind") == "operator_source_review"]
    if not entries:
        return None
    latest = entries[-1]
    if latest.get("manifest_digest") != digest(
        manifest.model_dump(mode="json")
    ) or not latest.get("storage"):
        return None
    return latest


async def review_source(
    session: AsyncSession,
    manifest: Manifest,
    reviewer: str,
    reason: str,
    *,
    allow_storage: bool,
    publish_fields: list[str],
    accept_attribution: bool = False,
) -> DataSource:
    actor(reviewer, reason)
    await writer_lock(session)
    if allow_storage and not manifest.storage_permissions:
        raise ImportErrorSafe("Manifest does not declare storage permission")
    if publish_fields and (
        not allow_storage
        or not manifest.redistribution_permissions
        or manifest.redistribution_conditions
        or (manifest.attribution_requirements and manifest.attribution is None)
        or (
            manifest.attribution is not None
            and (
                not accept_attribution
                or not manifest.attribution.supported()
                or manifest.attribution.provider != manifest.provider
            )
        )
    ):
        raise ImportErrorSafe(
            "Publication requires storage, redistribution and a supported attribution policy"
        )
    if not set(publish_fields) <= set(manifest.permitted_fields):
        raise ImportErrorSafe("Publication fields exceed the reviewed manifest")
    source = await source_for(session, manifest, create=True)
    assert source is not None
    now = datetime.now(UTC)
    event = {
        "kind": "operator_source_review",
        "manifest_digest": digest(manifest.model_dump(mode="json")),
        "reviewer": reviewer,
        "reason": reason,
        "at": now.isoformat(),
        "storage": allow_storage,
        "attribution_accepted": bool(manifest.attribution and accept_attribution),
        "publication_fields": sorted(set(publish_fields)),
        "manifest": manifest.model_dump(mode="json"),
    }
    # Re-review never silently resurrects withdrawn field grants, even when a
    # later manifest has the same digest. Publication remains a record decision.
    snapshots = select(SourceRecord.id).where(SourceRecord.source_id == source.id)
    links = select(SourceEntityLink.id).where(
        SourceEntityLink.source_record_id.in_(snapshots)
    )
    await session.execute(
        update(FieldProvenance)
        .where(FieldProvenance.entity_link_id.in_(links))
        .values(usage_rights_status="restricted")
    )
    await session.execute(
        update(SourceRecord)
        .where(SourceRecord.source_id == source.id)
        .values(redistribution_status="restricted")
    )
    if not allow_storage:
        # Retain minimal historical audit metadata, never an unauthorized raw
        # snapshot after an operator withdraws storage permission.
        await session.execute(
            update(SourceRecord)
            .where(SourceRecord.source_id == source.id)
            .values(payload=None, storage_status="restricted")
        )
    source.evidence = [*source.evidence, event]
    source.authorization_status = (
        ("synthetic" if manifest.synthetic else "approved")
        if allow_storage
        else "restricted"
    )
    source.licensing_status = (
        ("synthetic" if manifest.synthetic else "approved")
        if publish_fields
        else "restricted"
    )
    source.reviewed_at = now
    source.permitted_fields = sorted(set(publish_fields))
    source.reuse_restrictions = list(manifest.attribution_requirements)
    # Collection remains disabled even with a reviewed licensed file.
    source.enabled = False
    return source


def check_storage(
    source: DataSource | None, manifest: Manifest, record: Record
) -> dict[str, Any] | None:
    reviewed = policy(source, manifest)
    if reviewed:
        supplied = {
            k for k, v in record.model_dump().items() if v is not None and v != []
        }
        if not supplied <= set(manifest.permitted_fields):
            raise ImportErrorSafe(
                "Record contains fields outside reviewed storage permissions"
            )
    return reviewed


async def revoke(
    session: AsyncSession, source_id: str, reviewer: str, reason: str
) -> None:
    actor(reviewer, reason)
    await writer_lock(session)
    source = await session.scalar(
        select(DataSource).where(
            DataSource.key == source_id,
            DataSource.source_type.in_(["file_import", "synthetic_file_import"]),
        )
    )
    if source is None:
        raise ImportErrorSafe("File-import source not found")
    snapshots = select(SourceRecord.id).where(SourceRecord.source_id == source.id)
    links = select(SourceEntityLink.id).where(
        SourceEntityLink.source_record_id.in_(snapshots)
    )
    await session.execute(
        update(FieldProvenance)
        .where(FieldProvenance.entity_link_id.in_(links))
        .values(usage_rights_status="restricted")
    )
    await session.execute(
        update(SourceRecord)
        .where(SourceRecord.source_id == source.id)
        .values(redistribution_status="restricted")
    )
    source.licensing_status = "restricted"
    source.permitted_fields = []
    # Latest authorization event invalidates publication until explicit re-review.
    source.evidence = [
        *source.evidence,
        {
            "kind": "publication_revocation",
            "at": datetime.now(UTC).isoformat(),
            "reviewer": reviewer,
            "reason": reason,
        },
    ]
    # Retain snapshots/provenance and create an auditable record of the operation.
    record = await session.scalar(
        select(SourceRecord)
        .where(SourceRecord.source_id == source.id)
        .order_by(SourceRecord.id)
        .limit(1)
    )
    if record is not None:
        session.add(
            DataReviewQueue(
                source_record_id=record.id,
                reason="Publication revoked",
                status="resolved",
                reviewer=reviewer,
                resolution=reason,
                resolved_at=datetime.now(UTC),
                context={"decision": "revoke_publication"},
            )
        )
