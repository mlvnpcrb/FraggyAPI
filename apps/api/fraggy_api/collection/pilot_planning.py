"""Bounded offline enrichment planning and private field-review explanations.

This module has no transport or canonical publication path. Supplied snapshots and
assessments are planning inputs, never authorization grants or factual certainty.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..importing.formats import Record, Strict, concentration
from .enrichment import intent_summary, request_intent
from .intelligence import claim, match
from .providers import PROVIDERS

FIELDS = tuple(
    field
    for field in Record.model_fields
    if field not in {"source_record_id", "source_metadata", "brand_aliases"}
)


class Assessment(Strict):
    field: str = Field(min_length=1, max_length=80)
    reliability: str = Field(pattern=r"^(unknown|limited|corroborated|brand_authored)$")
    evidence_reference: str = Field(min_length=1, max_length=200)
    reviewer: str = Field(min_length=1, max_length=100)
    verified_at: AwareDatetime


class Observation(Strict):
    source: str = Field(min_length=1, max_length=100)
    reference: str = Field(min_length=1, max_length=160)
    collected_at: AwareDatetime
    record: Record
    assessments: list[Assessment] = Field(default_factory=list, max_length=30)


def missing(value: Any) -> bool:
    return value is None or value == [] or value == ""


def normalized(field: str, value: Any) -> Any:
    if missing(value):
        return None
    if field in {"source_url", "release_year", "gtin"}:
        return value
    if field == "bottle_sizes_ml":
        return sorted(value)
    return concentration(value) if field == "concentration" else claim(value)


def compare_observations(
    observations: list[Observation], at: datetime
) -> dict[str, Any]:
    """Review advice only. Callers storing this must enforce current storage rights."""
    if not at.tzinfo or not 2 <= len(observations) <= 10:
        raise ValueError("Two to ten observations and aware clock required")
    if len({(o.source, o.reference) for o in observations}) != len(observations):
        raise ValueError("Duplicate observation reference")
    fields: dict[str, Any] = {}
    for field in FIELDS:
        claims = []
        for observation in observations:
            value = getattr(observation.record, field)
            assessments = [
                a
                for a in observation.assessments
                if a.field == field and observation.collected_at <= a.verified_at <= at
            ]
            assessment = (
                max(assessments, key=lambda a: a.verified_at) if assessments else None
            )
            claims.append(
                {
                    "source": observation.source,
                    "source_record_reference": observation.reference,
                    "source_url": observation.record.source_url,
                    "original_value": observation.record.model_dump(mode="json")[field],
                    "normalized_value": normalized(field, value),
                    "collected_at": observation.collected_at.isoformat(),
                    "last_verified_at": assessment.verified_at.isoformat()
                    if assessment
                    else None,
                    "reliability": assessment.reliability if assessment else "unknown",
                    "evidence": assessment.model_dump(mode="json")
                    if assessment
                    else None,
                    "confidence": "unassessed",
                }
            )
        known = [
            c["normalized_value"] for c in claims if c["normalized_value"] is not None
        ]
        conflict = len({repr(v) for v in known}) > 1
        fields[field] = {
            "claims": claims,
            "state": "conflict"
            if conflict
            else "missing"
            if not known
            else "partial"
            if len(known) < len(claims)
            else "agrees",
            "preferred_claim": None,
            "review_reason": "conflicting_claims"
            if conflict
            else "human_selection_required",
        }
    return {
        "fields": fields,
        "identity_comparisons": [
            {
                "left": observations[0].reference,
                "right": other.reference,
                "evidence": match(observations[0].record, other.record),
            }
            for other in observations[1:]
        ],
        "independent_source_count": len({o.source for o in observations}),
        "automatic_merge": False,
        "publication_authorized": False,
        "unsupported_fields": ["images", "image_rights", "gender_positioning"],
    }


class SearchSnapshot(Strict):
    query: str = Field(min_length=1, max_length=120)
    fragrance_id: UUID | None = None
    concentration: str | None = None
    record: Record | None = None
    verified_fields: dict[str, AwareDatetime] = Field(
        default_factory=dict, max_length=30
    )
    required_fields: list[str] = Field(
        default_factory=lambda: [
            "brand_name",
            "fragrance_name",
            "concentration",
            "release_year",
            "notes",
            "perfumers",
        ],
        max_length=25,
    )
    providers: list[str] = Field(default_factory=lambda: list(PROVIDERS), max_length=10)


def plan_enrichment(snapshot: SearchSnapshot, at: datetime) -> dict[str, Any]:
    if not at.tzinfo or any(field not in FIELDS for field in snapshot.required_fields):
        raise ValueError("Aware clock and supported required fields required")
    if any(provider not in PROVIDERS for provider in snapshot.providers):
        raise ValueError("Unknown provider")
    concentration(snapshot.concentration)
    absent, stale = [], []
    for field in dict.fromkeys(snapshot.required_fields):
        if snapshot.record is None or missing(getattr(snapshot.record, field)):
            absent.append(field)
        elif (
            field not in snapshot.verified_fields
            or not at - timedelta(days=90) <= snapshot.verified_fields[field] <= at
        ):
            stale.append(field)
    return {
        "needs_enrichment": bool(absent or stale),
        "missing_fields": absent,
        "stale_or_unverified_fields": stale,
        "providers": [
            {
                "provider": name,
                "live_eligible": False,
                "reason": "source_specific_activity_approval_required",
                "contract": PROVIDERS[name].contract,
            }
            for name in dict.fromkeys(snapshot.providers)
        ],
        "search_waits_for_collection": False,
        "network_requests": 0,
        "publication_authorized": False,
    }


async def enqueue_plan(
    session: AsyncSession, snapshot: SearchSnapshot, at: datetime
) -> dict[str, Any]:
    """Trusted post-search operator action; creates existing intents, not runs."""
    plan = plan_enrichment(snapshot, at)
    plan["intents"] = (
        [
            intent_summary(
                await request_intent(
                    session,
                    row["provider"],
                    snapshot.query,
                    at,
                    fragrance_id=snapshot.fragrance_id,
                    concentration=snapshot.concentration,
                )
            )
            for row in plan["providers"]
        ]
        if plan["needs_enrichment"]
        else []
    )
    return plan
