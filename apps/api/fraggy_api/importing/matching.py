"""Deterministic, explainable candidates. Never writes or merges."""

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Brand, BrandAlias, Fragrance, FragranceRelease, FragranceVariant
from .formats import Record, concentration, key


async def brands(session: AsyncSession, name: str) -> list[Brand]:
    aliases = select(BrandAlias.brand_id).where(BrandAlias.name_key == key(name))
    return list(
        (
            await session.scalars(
                select(Brand)
                .where(or_(Brand.name_key == key(name), Brand.id.in_(aliases)))
                .order_by(Brand.id)
                .limit(21)
            )
        ).all()
    )


async def candidates(session: AsyncSession, record: Record) -> dict[str, Any]:
    owners = await brands(session, record.brand_name)
    reasons: list[str] = []
    if len(owners) > 1:
        return {
            "classification": "conflict_requiring_review",
            "confidence": "ambiguous",
            "reasons": ["ambiguous_brand_alias"],
            "release_ids": [],
        }
    rows = []
    if owners:
        rows = list(
            (
                await session.execute(
                    select(FragranceRelease, Fragrance)
                    .join(Fragrance, Fragrance.id == FragranceRelease.fragrance_id)
                    .where(
                        Fragrance.brand_id == owners[0].id,
                        Fragrance.name_key == key(record.fragrance_name),
                    )
                    .order_by(FragranceRelease.id)
                    .limit(21)
                )
            ).all()
        )
    identifiers = []
    if record.gtin:
        identifiers = list(
            (
                await session.scalars(
                    select(FragranceVariant.release_id)
                    .where(FragranceVariant.gtin == record.gtin)
                    .distinct()
                    .order_by(FragranceVariant.release_id)
                    .limit(21)
                )
            ).all()
        )
    variant_rows = (
        await session.execute(
            select(FragranceVariant.release_id, FragranceVariant.bottle_size_ml)
            .where(FragranceVariant.release_id.in_([r.id for r, _ in rows]))
            .order_by(FragranceVariant.release_id, FragranceVariant.id)
            .limit(441)
        )
    ).all()
    sizes_by_release: dict[UUID, list[Decimal | None]] = {}
    for release_id, size in variant_rows:
        sizes_by_release.setdefault(release_id, []).append(size)
    exact, possible = [], []
    normalized = concentration(record.concentration)
    for release, fragrance in rows:
        same_concentration = (
            normalized is not None and release.concentration == normalized
        )
        same_year = (
            record.release_year is not None
            and release.release_year == record.release_year
        )
        versions = record.version_label is None and release.version_label is None
        sizes = sizes_by_release.get(release.id, [])
        size_match = not record.bottle_sizes_ml or all(
            any(s is not None and float(s) == size for s in sizes)
            for size in record.bottle_sizes_ml
        )
        identifier_match = record.gtin is None or release.id in identifiers
        if (
            same_concentration
            and same_year
            and versions
            and size_match
            and identifier_match
        ):
            exact.append(str(release.id))
        else:
            possible.append(str(release.id))
            if not same_concentration:
                reasons.append("different_or_unknown_concentration")
            if not same_year:
                reasons.append("different_or_unknown_year")
            if not versions:
                reasons.append("version_requires_review")
            if not size_match or not identifier_match:
                reasons.append("variant_or_identifier_conflict")
    all_ids = sorted(set([*exact, *possible, *(str(i) for i in identifiers)]))[:20]
    if identifiers and any(str(i) not in exact for i in identifiers):
        classification = "conflict_requiring_review"
        reasons.append("identifier_does_not_prove_release_identity")
    elif len(exact) == 1 and not possible:
        classification = "exact_identity_match"
        reasons.append("brand_name_concentration_year_and_supplied_variant_agree")
    elif rows:
        classification = "possible_duplicate"
    else:
        # Detect related names only within the identified house; never auto-link.
        fragment = (
            key(record.fragrance_name)
            .split()[0]
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        related = list(
            (
                await session.scalars(
                    select(Fragrance.id)
                    .where(
                        Fragrance.brand_id.in_([b.id for b in owners]),
                        Fragrance.name_key.like(fragment + "%", escape="\\"),
                    )
                    .order_by(Fragrance.id)
                    .limit(20)
                )
            ).all()
        )
        classification = "possible_duplicate" if related else "new_fragrance"
        reasons.append(
            "related_name_requires_review" if related else "no_identity_candidate"
        )
    if len(rows) > 20 or len(identifiers) > 20 or len(variant_rows) == 441:
        classification = "conflict_requiring_review"
        reasons.append("candidate_limit_requires_manual_inspection")
    return {
        "classification": classification,
        "confidence": "high" if classification == "exact_identity_match" else "review",
        "reasons": sorted(set(reasons)),
        "release_ids": all_ids,
        "automatic_merge": False,
    }
