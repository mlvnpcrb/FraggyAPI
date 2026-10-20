"""Provider-independent durable admission; existing Collector owns execution."""

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..importing.authorization import check_storage
from ..importing.formats import Manifest, Record, digest, key
from ..importing.formats import concentration as normalize_concentration
from ..models import (
    CollectionRun,
    CollectionSource,
    DataReviewQueue,
    DataSource,
    EnrichmentIntent,
    FragranceRelease,
    FragranceVariant,
    SourceRecord,
)
from .intelligence import claim, match
from .policy import CollectionError, authorize
from .providers import PROVIDERS

if TYPE_CHECKING:
    from .engine import Collector

COOLDOWN_SECONDS = 3600
MAX_REQUESTS_PER_DAY = 4


async def request_intent(
    session: AsyncSession,
    provider: str,
    query: str,
    at: datetime,
    *,
    fragrance_id: UUID | None = None,
    concentration: str | None = None,
    variant_id: UUID | None = None,
) -> EnrichmentIntent:
    if (
        not at.tzinfo
        or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,99}", provider)
        or not query.strip()
        or len(query) > 120
        or len(key(query)) > 120
        or any(ord(char) < 32 for char in key(query))
    ):
        raise CollectionError("invalid_enrichment_request")
    if variant_id is not None:
        owner = await session.scalar(
            select(FragranceRelease.fragrance_id)
            .join(FragranceVariant, FragranceVariant.release_id == FragranceRelease.id)
            .where(FragranceVariant.id == variant_id)
        )
        if fragrance_id is None or owner != fragrance_id:
            raise CollectionError("enrichment_variant_identity_mismatch")
    # Private structured request, not a log or an upstream query. No client IDs.
    request = {
        "query": key(query),
        "fragrance_id": str(fragrance_id) if fragrance_id else None,
        "concentration": normalize_concentration(concentration),
        "variant_id": str(variant_id) if variant_id else None,
    }
    fingerprint = digest(request)
    await session.execute(
        insert(EnrichmentIntent)
        .values(
            id=uuid4(),
            provider=provider,
            request_digest=fingerprint,
            request=request,
            fragrance_id=fragrance_id,
            status="pending",
            next_allowed_at=at + timedelta(seconds=COOLDOWN_SECONDS),
        )
        .on_conflict_do_nothing(constraint="uq_enrichment_request")
    )
    intent = await session.scalar(
        select(EnrichmentIntent)
        .where(
            EnrichmentIntent.provider == provider,
            EnrichmentIntent.request_digest == fingerprint,
        )
        .with_for_update()
    )
    assert intent is not None
    if intent.status != "running" and intent.next_allowed_at <= at:
        intent.status = "pending"
        intent.diagnostic = None
        intent.next_allowed_at = at + timedelta(seconds=COOLDOWN_SECONDS)
    return intent


def intent_summary(intent: EnrichmentIntent) -> dict[str, Any]:
    # No raw search query, source evidence or private request fields in summaries.
    return {
        "id": str(intent.id),
        "provider": intent.provider,
        "status": intent.status,
        "diagnostic": intent.diagnostic,
        "collection_run_id": str(intent.collection_run_id)
        if intent.collection_run_id
        else None,
    }


async def admit(
    session: AsyncSession,
    intent_id: UUID,
    config: CollectionSource,
    source: DataSource,
    at: datetime,
) -> EnrichmentIntent:
    intent = await session.scalar(
        select(EnrichmentIntent)
        .where(EnrichmentIntent.id == intent_id)
        .with_for_update(skip_locked=True)
    )
    if (
        intent is None
        or intent.provider != source.key
        or (
            intent.status != "pending"
            and not (
                intent.status == "running"
                and intent.collection_run_id == config.current_run_id
                and config.lease_until
                and config.lease_until <= at
            )
        )
    ):
        raise CollectionError("enrichment_not_pending_or_source_mismatch")
    grant = authorize(config, source, at)
    # Phase 2M never enables external dispatch, including unknown future providers.
    # Synthetic dispatch still needs the existing reviewed loopback grant/lease.
    if not grant.manifest.synthetic:
        spec = PROVIDERS.get(intent.provider)
        raise CollectionError(
            "provider_live_disabled"
            if spec is None or not spec.live_enabled
            else "external_enrichment_not_approved"
        )
    if config.schedule_enabled:
        raise CollectionError("enrichment_requires_unscheduled_collection")
    if config.current_run_id and config.lease_until and config.lease_until > at:
        raise CollectionError("enrichment_source_busy")
    if config.next_due_at and config.next_due_at > at:
        raise CollectionError("enrichment_source_cooldown")
    if (
        grant.endpoint.retries + 1 > MAX_REQUESTS_PER_DAY
        or grant.endpoint.max_pages > MAX_REQUESTS_PER_DAY
    ):
        raise CollectionError("enrichment_request_budget_exceeded")
    attempts = await session.scalar(
        select(func.coalesce(func.sum(CollectionRun.attempts), 0)).where(
            CollectionRun.collection_id == config.id,
            CollectionRun.started_at >= at - timedelta(days=1),
        )
    )
    reserve = grant.endpoint.max_pages * (grant.endpoint.retries + 1)
    if (attempts or 0) + reserve > MAX_REQUESTS_PER_DAY:
        raise CollectionError("enrichment_request_budget_exceeded")
    return intent


async def stage_evidence_comparison(
    session: AsyncSession, left_id: UUID, right_id: UUID
) -> dict[str, Any]:
    """Compare privately stored approved observations; never select canonical claims."""
    if left_id == right_id:
        raise CollectionError("distinct_observations_required")
    rows = [
        await session.get(SourceRecord, identity) for identity in (left_id, right_id)
    ]
    if any(
        row is None
        or row.storage_status not in {"approved", "synthetic"}
        or not row.payload
        for row in rows
    ):
        raise CollectionError("evidence_storage_not_authorized")
    left, right = rows
    assert left is not None and right is not None and left.payload and right.payload
    for row in (left, right):
        source = await session.get(DataSource, row.source_id)
        if source is None or source.authorization_status not in {
            "approved",
            "synthetic",
        }:
            raise CollectionError("evidence_source_revoked")
        try:
            reviews = [
                event
                for event in source.evidence
                if event.get("kind") == "operator_source_review"
            ]
            manifest = Manifest.model_validate(reviews[-1]["manifest"])
            if (
                row.payload is None
                or row.payload.get("manifest_digest")
                != digest(manifest.model_dump(mode="json"))
                or not check_storage(
                    source, manifest, Record.model_validate(row.payload["original"])
                )
            ):
                raise ValueError("unreviewed")
        except (ValueError, IndexError, KeyError) as error:
            raise CollectionError("evidence_storage_not_authorized") from error
    a, b = (
        Record.model_validate(left.payload["original"]),
        Record.model_validate(right.payload["original"]),
    )
    fields = {}
    for field in Record.model_fields:
        x, y = getattr(a, field), getattr(b, field)
        if field == "concentration":
            x, y = normalize_concentration(x), normalize_concentration(y)
        if field in {"source_record_id", "source_url", "source_metadata"}:
            continue
        fields[field] = {
            "left_source_record": str(left.id),
            "right_source_record": str(right.id),
            "state": "missing"
            if x is None or y is None or x == [] or y == []
            else "agrees"
            if claim(x) == claim(y)
            else "conflict",
        }
    report = {
        "match": match(a, b),
        "fields": fields,
        "automatic_merge": False,
        "publication_authorized": False,
    }
    # Existing manual review item, not a second review queue or canonical write.
    item = await session.scalar(
        select(DataReviewQueue)
        .where(
            DataReviewQueue.source_record_id == right.id,
            DataReviewQueue.status == "pending",
        )
        .order_by(DataReviewQueue.id)
        .limit(1)
        .with_for_update()
    )
    if item is None:
        raise CollectionError("manual_review_item_missing")
    comparisons = list(item.context.get("enrichment_comparisons", []))
    if report not in comparisons:
        if len(comparisons) >= 20:
            raise CollectionError("comparison_budget_exceeded")
        comparisons.append(report)
    item.context = {**item.context, "enrichment_comparisons": comparisons}
    return report


async def run_intent(collector: "Collector", intent_id: UUID) -> dict[str, Any]:
    """Explicit operator invocation, never called by GET/search or recurring jobs.

    The reviewed collection configuration fixes the endpoint/scope; arbitrary search
    strings are never substituted into URLs. All real dispatch is blocked in 2M.
    """
    async with collector.factory() as session:
        intent = await session.get(EnrichmentIntent, intent_id)
        if intent is None:
            raise CollectionError("enrichment_not_found")
        identity = await session.scalar(
            select(CollectionSource.id)
            .join(DataSource, CollectionSource.source_id == DataSource.id)
            .where(DataSource.key == intent.provider)
        )
    try:
        if identity is None:
            raise CollectionError("provider_collection_not_configured")
        run_id = await collector.claim(identity, enrichment_intent_id=intent_id)
        if run_id is None:
            return {"status": "deferred", "external_requests": 0}
        return await collector.execute(identity, run_id)
    except CollectionError as error:
        # Only known internal error codes, never arbitrary exception text.
        safe = (
            str(error)
            if re.fullmatch(r"[a-z_]{1,80}", str(error))
            else "enrichment_failed"
        )
        async with collector.factory.begin() as session:
            intent = await session.get(
                EnrichmentIntent, intent_id, with_for_update=True
            )
            assert intent is not None
            if intent.status == "pending":
                intent.status = "blocked"
                intent.diagnostic = safe
            return intent_summary(intent)
