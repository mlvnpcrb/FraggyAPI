"""Sanitized aggregate checks. Identifiers/counts only, never private evidence."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..attribution import safe_public_url
from ..database import Base
from ..models import (
    Accord,
    Brand,
    BrandAlias,
    DataSource,
    FieldProvenance,
    Fragrance,
    FragranceFamily,
    FragranceRelease,
    FragranceVariant,
    MediaAsset,
    Note,
    NoteAlias,
    Perfumer,
    ReleaseAccord,
    ReleaseNote,
    SourceEntityLink,
    SourceRecord,
)
from ..public_catalog import rights_condition, visible
from ..public_rights import Access, read_access, reviewed_attribution
from .duplicates import classify_pair

SAMPLE_LIMIT = 25
SCAN_LIMIT = 100000


async def catalog_quality(session: AsyncSession) -> dict[str, Any]:
    """Caller supplies a consistent read-only transaction; this function never writes."""
    model: Any
    findings: list[dict[str, Any]] = []
    complete = True

    async def count(statement: Any) -> int:
        return int(
            await session.scalar(select(func.count()).select_from(statement.subquery()))
            or 0
        )

    async def finding(code: str, severity: str, statement: Any) -> int:
        total = await count(statement)
        if total:
            samples = (
                await session.scalars(
                    statement.order_by(None)
                    .order_by(statement.selected_columns[0])
                    .limit(SAMPLE_LIMIT)
                )
            ).all()
            findings.append(
                {
                    "code": code,
                    "severity": severity,
                    "count": total,
                    "sample_ids": [str(v) for v in samples],
                    "samples_truncated": total > SAMPLE_LIMIT,
                }
            )
        return total

    models: dict[str, Any] = {
        "brands": Brand,
        "fragrances": Fragrance,
        "releases": FragranceRelease,
        "notes": Note,
        "accords": Accord,
    }
    totals = {name: await count(select(model.id)) for name, model in models.items()}
    totals["awaiting_review"] = await count(
        select(SourceRecord.id).where(
            SourceRecord.processing_state.in_(("pending_review", "validated"))
        )
    )
    missing: dict[str, Any] = {}
    for model, fields in (
        (Brand, ("name",)),
        (Fragrance, ("name", "brand_id", "family_id")),
        (FragranceRelease, ("concentration", "release_year")),
    ):
        total = await count(select(model.id))
        for field in fields:
            col = getattr(model, field)
            condition = col.is_(None)
            if field == "name":
                condition = or_(condition, func.length(func.btrim(col)) == 0)
            n = await count(select(model.id).where(condition))
            missing[f"{model.__tablename__}.{field}"] = {
                "missing": n,
                "total": total,
                "percent": round(n * 100 / total, 2) if total else 0.0,
            }
            if field in {"name", "brand_id"}:
                await finding(
                    f"missing_{model.__tablename__}_{field}",
                    "error",
                    select(model.id).where(condition),
                )
    current_year = datetime.now(UTC).year
    for model in (Fragrance, FragranceRelease):
        await finding(
            f"implausible_year_{model.__tablename__}",
            "warning",
            select(model.id).where(
                or_(model.release_year < 1700, model.release_year > current_year + 2)
            ),
        )
    for field, association in (("notes", ReleaseNote), ("accords", ReleaseAccord)):
        absent = not_(
            exists(
                select(1)
                .select_from(association)
                .where(association.release_id == FragranceRelease.id)
            )
        )
        n = await count(select(FragranceRelease.id).where(absent))
        total = totals["releases"]
        missing[f"fragrance_releases.{field}"] = {
            "missing": n,
            "total": total,
            "percent": round(n * 100 / total, 2) if total else 0.0,
        }
    versioned = select(FragranceRelease.id).where(
        or_(
            FragranceRelease.version_label.is_not(None),
            FragranceRelease.reformulation_of_id.is_not(None),
        )
    )
    await finding("version_distinction", "info", versioned)
    allowed = (
        "parfum",
        "extrait_de_parfum",
        "eau_de_parfum",
        "eau_de_toilette",
        "eau_de_cologne",
        "eau_fraiche",
        "oil",
        "other",
    )
    await finding(
        "invalid_concentration",
        "error",
        select(FragranceRelease.id).where(
            FragranceRelease.concentration.not_in(allowed)
        ),
    )
    await finding(
        "unknown_concentration",
        "info",
        select(FragranceRelease.id).where(FragranceRelease.concentration.is_(None)),
    )
    await finding(
        "invalid_note_position",
        "error",
        select(ReleaseNote.id).where(
            ReleaseNote.position.not_in(("top", "heart", "base", "unknown"))
        ),
    )
    await finding(
        "unknown_note_position",
        "info",
        select(ReleaseNote.id).where(ReleaseNote.position == "unknown"),
    )
    # Schema constraints normally prevent these defects; independently inspect
    # every FK so restored/legacy databases do not receive a silent clean bill.
    for table in Base.metadata.sorted_tables:
        for constraint in sorted(
            table.foreign_key_constraints, key=lambda c: str(c.name or "")
        ):
            elements = list(constraint.elements)
            other = elements[0].column.table.alias()
            # PostgreSQL MATCH SIMPLE skips a composite FK when any component
            # is NULL. Compare the whole tuple, never each component separately.
            broken = and_(
                *(element.parent.is_not(None) for element in elements),
                not_(
                    exists(
                        select(1)
                        .select_from(other)
                        .where(
                            *(
                                other.c[element.column.name] == element.parent
                                for element in elements
                            )
                        )
                    )
                ),
            )
            columns = "_".join(element.parent.name for element in elements)
            await finding(
                f"broken_relationship_{table.name}_{columns}",
                "error",
                select(table.c.id).where(broken),
            )
    # Composite same-line reformulation identity needs more than a simple FK.
    prior = FragranceRelease.__table__.alias("prior")
    await finding(
        "invalid_reformulation",
        "error",
        select(FragranceRelease.id).where(
            FragranceRelease.reformulation_of_id.is_not(None),
            not_(
                exists(
                    select(1)
                    .select_from(prior)
                    .where(
                        prior.c.id == FragranceRelease.reformulation_of_id,
                        prior.c.fragrance_id == FragranceRelease.fragrance_id,
                    )
                )
            ),
        ),
    )
    await finding(
        "conflicting_source_claim",
        "warning",
        select(FieldProvenance.id).where(FieldProvenance.value_state == "conflicting"),
    )
    for model, target in (
        (Brand, "brand_id"),
        (Fragrance, "fragrance_id"),
        (FragranceRelease, "release_id"),
        (FragranceVariant, "variant_id"),
        (Note, "note_id"),
        (Accord, "accord_id"),
        (Perfumer, "perfumer_id"),
        (FragranceFamily, "family_id"),
    ):
        provenance = exists(
            select(1)
            .select_from(SourceEntityLink)
            .join(FieldProvenance)
            .where(getattr(SourceEntityLink, target) == model.id)
        )
        await finding(
            f"missing_provenance_{model.__tablename__}",
            "warning",
            select(model.id).where(not_(provenance)),
        )
    # Canonical names are constrained unique for houses/taxonomies, but aliases
    # can be ambiguous across owners or shadow another house's canonical name.
    for alias, owner, target in (
        (BrandAlias, Brand, "brand_id"),
        (NoteAlias, Note, "note_id"),
    ):
        duplicate_keys = (
            select(alias.name_key)
            .group_by(alias.name_key)
            .having(func.count(func.distinct(getattr(alias, target))) > 1)
        )
        await finding(
            f"ambiguous_{alias.__tablename__}",
            "warning",
            select(alias.id).where(alias.name_key.in_(duplicate_keys)),
        )
        await finding(
            f"shadowing_{alias.__tablename__}",
            "warning",
            select(alias.id).join(
                owner,
                and_(
                    owner.name_key == alias.name_key, owner.id != getattr(alias, target)
                ),
            ),
        )
    duplicate_brand_keys = (
        select(Brand.name_key).group_by(Brand.name_key).having(func.count() > 1)
    )
    await finding(
        "duplicate_brand",
        "warning",
        select(Brand.id).where(Brand.name_key.in_(duplicate_brand_keys)),
    )
    # Same normalized house/name blocks only; related-name flankers are not
    # merged. SQL bounds each block before forming candidate pairs.
    ranked = (
        select(
            FragranceRelease.id.label("id"),
            Fragrance.brand_id.label("brand"),
            Fragrance.name_key.label("name"),
            FragranceRelease.concentration,
            FragranceRelease.release_year.label("year"),
            FragranceRelease.version_label.label("version"),
            FragranceRelease.reformulation_of_id.label("reformulation"),
            func.row_number()
            .over(
                partition_by=(Fragrance.brand_id, Fragrance.name_key),
                order_by=FragranceRelease.id,
            )
            .label("rn"),
        )
        .join(Fragrance, Fragrance.id == FragranceRelease.fragrance_id)
        .subquery()
    )
    left, right = ranked.alias("left_release"), ranked.alias("right_release")
    pair_statement = (
        select(left, right)
        .join(
            right,
            and_(
                left.c.brand == right.c.brand,
                left.c.name == right.c.name,
                left.c.rn < right.c.rn,
            ),
        )
        .where(left.c.rn <= 21, right.c.rn <= 21)
        .order_by(left.c.id, right.c.id)
    )
    pairs = (await session.execute(pair_statement.limit(1001))).all()
    block_overflow = await count(select(ranked.c.id).where(ranked.c.rn > 21))
    duplicates = []
    for row in pairs[:1000]:
        values = tuple(row)
        a = dict(
            zip(
                (
                    "id",
                    "brand",
                    "name",
                    "concentration",
                    "year",
                    "version",
                    "reformulation",
                    "rn",
                ),
                values[:8],
                strict=True,
            )
        )
        b = dict(
            zip(
                (
                    "id",
                    "brand",
                    "name",
                    "concentration",
                    "year",
                    "version",
                    "reformulation",
                    "rn",
                ),
                values[8:],
                strict=True,
            )
        )
        a["brand"], b["brand"] = str(a["brand"]), str(b["brand"])
        duplicates.append(
            {
                "left_id": str(a["id"]),
                "right_id": str(b["id"]),
                "classification": classify_pair(a, b),
                "automatic_merge": False,
            }
        )
    roots = select(
        Fragrance.id,
        Fragrance.brand_id,
        Fragrance.name_key,
        func.split_part(Fragrance.name_key, " ", 1).label("prefix"),
        func.row_number()
        .over(
            partition_by=(
                Fragrance.brand_id,
                func.split_part(Fragrance.name_key, " ", 1),
            ),
            order_by=Fragrance.id,
        )
        .label("rn"),
    ).subquery()
    root_a, root_b = roots.alias("line_a"), roots.alias("line_b")
    related = (
        await session.execute(
            select(root_a.c.id, root_b.c.id)
            .join(
                root_b,
                and_(
                    root_a.c.brand_id == root_b.c.brand_id,
                    root_a.c.prefix == root_b.c.prefix,
                    root_a.c.rn < root_b.c.rn,
                    root_a.c.name_key != root_b.c.name_key,
                ),
            )
            .where(root_a.c.rn <= 21, root_b.c.rn <= 21)
            .order_by(root_a.c.id, root_b.c.id)
            .limit(1001)
        )
    ).all()
    remaining = max(0, 1000 - len(duplicates))
    duplicates.extend(
        {
            "left_id": str(a),
            "right_id": str(b),
            "classification": "related_name_review",
            "automatic_merge": False,
        }
        for a, b in related[:remaining]
    )
    related_overflow = len(related) > remaining or bool(
        await count(select(roots.c.id).where(roots.c.rn > 21))
    )
    if len(pairs) > 1000 or block_overflow or related_overflow:
        complete = False
        findings.append(
            {
                "code": "duplicate_analysis_truncated",
                "severity": "warning",
                "count": 1,
                "overflow_releases": block_overflow,
                "sample_ids": [],
                "samples_truncated": True,
            }
        )
    # URL values stay private; reports contain only entity UUIDs/categories.
    for model, field in (
        (DataSource, "website"),
        (SourceRecord, "source_url"),
        (MediaAsset, "source_url"),
        (MediaAsset, "license_url"),
    ):
        invalid: list[str] = []
        scanned = 0
        rows = await session.stream(
            select(model.id, getattr(model, field))
            .where(getattr(model, field).is_not(None))
            .order_by(model.id)
            .limit(SCAN_LIMIT + 1)
        )
        async for identity, url in rows:
            scanned += 1
            if scanned > SCAN_LIMIT:
                complete = False
                break
            try:
                safe_public_url(url)
            except ValueError:
                invalid.append(str(identity))
        if invalid:
            findings.append(
                {
                    "code": f"unsafe_public_url_{model.__tablename__}_{field}",
                    "severity": "warning",
                    "count": len(invalid),
                    "sample_ids": invalid[:SAMPLE_LIMIT],
                    "samples_truncated": len(invalid) > SAMPLE_LIMIT,
                }
            )
    access = await read_access(session, True)
    production = Access(False, access.sources)
    source_rows = (
        await session.scalars(select(DataSource).order_by(DataSource.id).limit(1001))
    ).all()
    source_counts = (
        await session.execute(
            select(SourceRecord.source_id, func.count()).group_by(
                SourceRecord.source_id
            )
        )
    ).all()
    counts_by_source = {identity: total for identity, total in source_counts}
    source_coverage = []
    attribution_required = attribution_supported = 0
    for source_entry in source_rows[:1000]:
        if source_entry.source_type in {"file_import", "synthetic_file_import"}:
            reviewed, attribution = reviewed_attribution(source_entry)
            # Requirements themselves and legal evidence are never copied out.
            reviews = [
                e
                for e in source_entry.evidence
                if isinstance(e, dict) and e.get("kind") == "operator_source_review"
            ]
            latest_manifest = reviews[-1].get("manifest") if reviews else None
            active_publication = source_entry.authorization_status in {
                "approved",
                "synthetic",
            } and source_entry.licensing_status in {"approved", "synthetic"}
            required = active_publication and (
                bool(source_entry.reuse_restrictions)
                or (
                    isinstance(latest_manifest, dict)
                    and bool(latest_manifest.get("attribution"))
                )
            )
            attribution_required += int(required)
            attribution_supported += int(
                required and reviewed and attribution is not None
            )
            if required and not reviewed:
                findings.append(
                    {
                        "code": "missing_or_unsupported_attribution",
                        "severity": "error",
                        "count": 1,
                        "sample_ids": [str(source_entry.id)],
                        "samples_truncated": False,
                    }
                )
        source_coverage.append(
            {
                "source_id": str(source_entry.id),
                "source_type": source_entry.source_type,
                "records": counts_by_source.get(source_entry.id, 0),
                "authorization_status": source_entry.authorization_status,
                "licensing_status": source_entry.licensing_status,
                "collection_enabled": source_entry.enabled,
            }
        )
    if len(source_rows) > 1000:
        complete = False
    c, link, record, source = (
        FieldProvenance,
        SourceEntityLink,
        SourceRecord,
        DataSource,
    )
    claimed = (
        select(c.id)
        .join(link, c.entity_link_id == link.id)
        .join(record, link.source_record_id == record.id)
        .join(source, record.source_id == source.id)
        .where(
            c.selection_status == "selected",
            c.value_state == "known",
            c.field_path.in_(
                (
                    "name",
                    "slug",
                    "brand_id",
                    "fragrance_id",
                    "concentration",
                    "release_year",
                    "notes",
                    "accords",
                )
            ),
            or_(
                *(
                    getattr(link, target).is_not(None)
                    for target in (
                        "brand_id",
                        "fragrance_id",
                        "release_id",
                        "note_id",
                        "accord_id",
                    )
                )
            ),
            link.review_status == "approved",
            record.processing_state == "linked",
        )
    )
    blocked = await finding(
        "unapproved_publication_permission",
        "warning",
        claimed.where(not_(rights_condition(access))),
    )
    approved = await count(claimed.where(rights_condition(access)))
    # Scalar selected claims must still equal current canonical values. This
    # identifies stale grants even if another source keeps the entity visible.
    for model, target, fields in (
        (Brand, "brand_id", ("name", "slug")),
        (Fragrance, "fragrance_id", ("name", "slug", "brand_id")),
        (
            FragranceRelease,
            "release_id",
            ("fragrance_id", "concentration", "release_year"),
        ),
        (Note, "note_id", ("name", "slug")),
        (Accord, "accord_id", ("name", "slug")),
    ):
        mismatch = or_(
            *(
                and_(
                    c.field_path == field,
                    c.value.is_distinct_from(func.to_jsonb(getattr(model, field))),
                )
                for field in fields
            )
        )
        await finding(
            f"stale_claim_{model.__tablename__}",
            "warning",
            select(c.id)
            .join(link, c.entity_link_id == link.id)
            .join(model, getattr(link, target) == model.id)
            .where(
                c.selection_status == "selected", c.value_state == "known", mismatch
            ),
        )
    visible_fragrances = and_(
        visible(Fragrance, "fragrance_id", access), visible(Brand, "brand_id", access)
    )
    from ..public_catalog import grant

    visible_fragrances = and_(
        visible_fragrances,
        grant("fragrance_id", Fragrance.id, "brand_id", Fragrance.brand_id, access),
    )
    eligible = await count(select(Fragrance.id).join(Brand).where(visible_fragrances))
    prod_eligible = await count(
        select(Fragrance.id)
        .join(Brand)
        .where(
            visible(Fragrance, "fragrance_id", production),
            visible(Brand, "brand_id", production),
            grant(
                "fragrance_id", Fragrance.id, "brand_id", Fragrance.brand_id, production
            ),
        )
    )
    severities = {
        level: sum(f["count"] for f in findings if f["severity"] == level)
        for level in ("error", "warning", "info")
    }
    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "read_only": True,
        "complete": complete,
        "totals": totals,
        "missing_fields": missing,
        "duplicate_candidates": duplicates,
        "duplicate_analysis": {
            "returned_pairs": len(duplicates),
            "block_limit": 21,
            "pair_limit": 1000,
            "overflow_releases": block_overflow,
            "related_name_candidates_truncated": related_overflow,
        },
        "findings": findings,
        "severity_counts": severities,
        "source_coverage": source_coverage,
        "source_coverage_truncated": len(source_rows) > 1000,
        "publication_eligibility": {
            "fragrances_development": eligible,
            "fragrances_production": prod_eligible,
            "selected_claims_with_rights": approved,
            "selected_claims_blocked": blocked,
        },
        "licensing_blockers": {
            "sources_not_approved": sum(
                s.licensing_status not in {"approved", "synthetic"}
                for s in source_rows[:1000]
            ),
            "claim_blockers": blocked,
        },
        "attribution_coverage": {
            "sources_requiring_credit": attribution_required,
            "sources_with_supported_credit": attribution_supported,
        },
        "automatic_changes": 0,
    }


def human_report(report: dict[str, Any]) -> str:
    lines = ["FraggyAPI catalog quality (read-only)", f"Complete: {report['complete']}"]
    lines += [f"{name}: {count}" for name, count in report["totals"].items()]
    lines += [f"{level}: {count}" for level, count in report["severity_counts"].items()]
    lines += [
        f"Duplicate candidate pairs: {len(report['duplicate_candidates'])}",
        f"Publication eligibility: {report['publication_eligibility']}",
        f"Licensing blockers: {report['licensing_blockers']}",
        f"Attribution coverage: {report['attribution_coverage']}",
    ]
    lines += [
        f"Missing {name}: {v['percent']}% ({v['missing']}/{v['total']})"
        for name, v in report["missing_fields"].items()
    ]
    lines += [
        f"{f['severity'].upper()} {f['code']}: {f['count']}" for f in report["findings"]
    ]
    lines += [
        f"SOURCE {s['source_id']}: {s['source_type']}; records={s['records']}; authorization={s['authorization_status']}; licensing={s['licensing_status']}"
        for s in report["source_coverage"]
    ]
    lines += [
        f"CANDIDATE {p['classification']}: {p['left_id']} / {p['right_id']}; automatic_merge=false"
        for p in report["duplicate_candidates"]
    ]
    return "\n".join(lines) + "\n"
