from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fraggy_api.contracts import BrandRead, ReleaseRead
from fraggy_api.database import Base
from fraggy_api.models import (
    Brand,
    BrandAlias,
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    Fragrance,
    FragranceRelease,
    FragranceVariant,
    IngestionRun,
    MediaAsset,
    Note,
    NoteAlias,
    Perfumer,
    ReleaseNote,
    SourceEntityLink,
    SourceRecord,
)
from fraggy_api.seed import demo_id, seed_demo
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


@pytest.fixture
async def seeded(session: AsyncSession) -> dict[str, UUID]:
    return await seed_demo(session, allow_demo_data=True)


async def reject(session: AsyncSession, model: object) -> None:
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(model)
            await session.flush()


async def test_relationships_and_distinct_releases(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    statement = (
        select(Brand)
        .where(Brand.id == seeded["brand:1"])
        .options(
            selectinload(Brand.fragrances)
            .selectinload(Fragrance.releases)
            .selectinload(FragranceRelease.variants)
        )
    )
    brand = (await session.scalars(statement)).one()
    assert len(brand.fragrances) == 2
    fragrance = next(f for f in brand.fragrances if f.id == seeded["fragrance:1"])
    assert {r.concentration for r in fragrance.releases} == {
        "eau_de_toilette",
        "eau_de_parfum",
    }
    assert len(fragrance.releases) == 3  # EDT, EDP, separate reformulation.
    edp = next(r for r in fragrance.releases if r.id == seeded["release:edp"])
    assert len(edp.variants) == 3
    assert sorted(v.bottle_size_ml for v in edp.variants) == [50, 50, 100]
    assert edp.release_year is None
    reformulation = await session.get(FragranceRelease, seeded["release:reformulation"])
    assert reformulation.reformulation_of_id == edp.id
    assert BrandRead.model_validate(brand).id == brand.id
    assert ReleaseRead.model_validate(edp).release_year is None


async def test_seed_is_opt_in_idempotent_and_preserves_edits(
    session: AsyncSession,
) -> None:
    with pytest.raises(ValueError):
        await seed_demo(session)
    ids = await seed_demo(session, allow_demo_data=True)
    counts = {
        name: await session.scalar(select(func.count()).select_from(table))
        for name, table in Base.metadata.tables.items()
    }
    brand = await session.get(Brand, ids["brand:1"])
    original_time, original_slug = brand.created_at, brand.slug
    brand.name = "Revised Fictional House"
    await session.flush()
    assert await seed_demo(session, allow_demo_data=True) == ids
    await session.refresh(brand)
    assert brand.name == "Revised Fictional House"
    assert brand.id == demo_id("brand:1")
    assert brand.slug == original_slug
    assert brand.created_at == original_time
    for name, table in Base.metadata.tables.items():
        assert (
            await session.scalar(select(func.count()).select_from(table))
            == counts[name]
        )
    assert all(
        counts.values()
    )  # Every catalog/provenance table has a synthetic example.


@pytest.mark.parametrize(
    "kind,name",
    [
        (Brand, "  NACRE   WORKSHOP "),
        (Brand, "\tNacre Workshop\n"),
        (Brand, "ＮＡＣＲＥ ＷＯＲＫＳＨＯＰ"),
        (Note, "  CEDAR  "),
    ],
)
async def test_computed_normalized_keys_prevent_duplicates(
    session: AsyncSession, seeded: dict[str, UUID], kind: type, name: str
) -> None:
    await reject(session, kind(name=name, slug="another-slug"))


async def test_aliases_and_legitimate_same_names(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    await reject(
        session, BrandAlias(brand_id=seeded["brand:1"], name=" NACRE  STUDIO ")
    )
    await reject(session, NoteAlias(note_id=seeded["note:1"], name=" CEDAR  WOOD "))
    # Different owners may share an alias; no automatic matching is inferred.
    session.add(BrandAlias(brand_id=seeded["brand:2"], name="Nacre Studio"))
    session.add(Perfumer(name="Lina Vale", slug="another-person-same-name"))
    session.add(
        Fragrance(
            brand_id=seeded["brand:1"],
            name="Paper Horizon",
            slug="paper-horizon-distinct-line",
        )
    )
    session.add(
        FragranceRelease(
            fragrance_id=seeded["fragrance:1"], concentration="eau_de_parfum"
        )
    )
    await session.flush()


async def test_unknowns_attribution_conflicts_and_manual_review(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    record = await session.get(SourceRecord, seeded["record:1"])
    assert record.collected_at.tzinfo is not None
    assert record.collected_at.utcoffset().total_seconds() == 0
    assert record.storage_status == "synthetic"
    claims = (
        await session.execute(
            select(FieldProvenance, SourceRecord, DataSource)
            .join(
                SourceEntityLink, FieldProvenance.entity_link_id == SourceEntityLink.id
            )
            .join(SourceRecord, SourceEntityLink.source_record_id == SourceRecord.id)
            .join(DataSource, SourceRecord.source_id == DataSource.id)
        )
    ).all()
    assert {claim.value for claim, _, _ in claims} == {2020, 2021}
    assert len({source.id for _, _, source in claims}) == 2
    for claim, origin, _ in claims:
        assert (
            claim.value_state == "conflicting" and claim.selection_status == "candidate"
        )
        assert claim.usage_rights_status == "synthetic"
        assert claim.confidence == Decimal("0.8")
        assert claim.transformations[0]["version"] == "1"
        assert origin.source_url.startswith("https://example.invalid/")
    assert (await session.get(DataReviewQueue, seeded["review:1"])).status == "pending"
    unknown = await session.get(FragranceRelease, seeded["release:2"])
    assert unknown.concentration is None and unknown.release_year is None
    notes = (await session.scalars(select(ReleaseNote))).all()
    assert {n.position for n in notes} == {"top", "heart", "base", "unknown"}
    media = await session.get(MediaAsset, seeded["media:1"])
    assert media.storage_path is None and media.usage_status == "pending_review"
    candidates = (
        await session.scalars(
            select(DataSource).where(DataSource.source_type == "website")
        )
    ).all()
    assert len(candidates) == 7
    assert all(
        not s.enabled
        and s.authorization_status == "pending_review"
        and s.licensing_status == "pending_review"
        for s in candidates
    )


@pytest.mark.parametrize("year", [999, 3000, -1])
async def test_invalid_years(
    session: AsyncSession, seeded: dict[str, UUID], year: int
) -> None:
    await reject(
        session, FragranceRelease(fragrance_id=seeded["fragrance:1"], release_year=year)
    )


@pytest.mark.parametrize("size", [0, -1])
async def test_positive_sizes(
    session: AsyncSession, seeded: dict[str, UUID], size: int
) -> None:
    await reject(
        session, FragranceVariant(release_id=seeded["release:edp"], bottle_size_ml=size)
    )


async def test_variant_formats_and_slug_constraints(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    await reject(
        session, FragranceVariant(release_id=seeded["release:edp"], original_size=50)
    )
    await reject(
        session, FragranceVariant(release_id=seeded["release:edp"], gtin="not-a-gtin")
    )
    await reject(session, Brand(name="", slug="empty-name"))
    await reject(session, Brand(name="\t\n", slug="blank-whitespace"))
    await reject(session, Brand(name="Another House", slug="Invalid slug"))
    await reject(session, Brand(name="Another House", slug="nacre-workshop"))


@pytest.mark.parametrize("confidence", [Decimal("-0.1"), Decimal("1.1")])
async def test_confidence_bounds(
    session: AsyncSession, seeded: dict[str, UUID], confidence: Decimal
) -> None:
    await reject(
        session,
        FieldProvenance(
            entity_link_id=seeded["link:1"],
            field_path="name",
            value="Example",
            value_state="known",
            collected_at=datetime.now(UTC),
            confidence=confidence,
        ),
    )


async def test_payload_retention_and_media_rights_are_fail_closed(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    for values in [
        {"payload": {"unlicensed": "content"}},
        {"payload": {}, "storage_status": "approved"},
        {"payload": [], "storage_status": "synthetic"},
        {"redistribution_status": "approved"},
    ]:
        await reject(
            session,
            SourceRecord(
                source_id=seeded["demo-source:1"],
                source_record_id=str(uuid4()),
                collected_at=datetime.now(UTC),
                **values,
            ),
        )
    await reject(
        session,
        MediaAsset(
            entity_link_id=seeded["link:1"],
            source_url="https://example.invalid/a",
            storage_path="assets/a",
        ),
    )
    await reject(
        session,
        DataSource(
            key="not-approved",
            name="Unreviewed",
            website="https://example.invalid",
            source_type="website",
            enabled=True,
        ),
    )
    await reject(
        session,
        FieldProvenance(
            entity_link_id=seeded["link:1"],
            field_path="name",
            value="Example",
            value_state="known",
            collected_at=datetime.now(UTC),
            usage_rights_status="approved",
        ),
    )


async def test_link_integrity_and_source_run_consistency(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    await reject(session, SourceEntityLink(source_record_id=seeded["record:1"]))
    await reject(
        session,
        SourceEntityLink(
            source_record_id=seeded["record:1"],
            brand_id=seeded["brand:1"],
            release_id=seeded["release:edp"],
        ),
    )
    await reject(
        session,
        SourceEntityLink(
            source_record_id=seeded["record:1"], release_id=seeded["release:edp"]
        ),
    )
    await reject(
        session,
        SourceEntityLink(source_record_id=seeded["record:1"], release_id=uuid4()),
    )
    await reject(
        session,
        SourceRecord(
            source_id=seeded["demo-source:1"],
            ingestion_run_id=seeded["run:2"],
            source_record_id="wrong-run",
            collected_at=datetime.now(UTC),
        ),
    )
    await reject(
        session,
        FragranceRelease(
            fragrance_id=seeded["fragrance:2"],
            reformulation_of_id=seeded["release:edp"],
        ),
    )
    identity = uuid4()
    await reject(
        session,
        FragranceRelease(
            id=identity,
            fragrance_id=seeded["fragrance:1"],
            reformulation_of_id=identity,
        ),
    )


@pytest.mark.parametrize(
    "model,key",
    [
        (Brand, "brand:1"),
        (Fragrance, "fragrance:1"),
        (FragranceRelease, "release:edp"),
        (Note, "note:1"),
        (SourceRecord, "record:1"),
        (DataSource, "demo-source:1"),
        (SourceEntityLink, "link:1"),
        (FieldProvenance, "claim:2"),
        (IngestionRun, "run:1"),
    ],
)
async def test_foreign_keys_restrict_deletion(
    session: AsyncSession, seeded: dict[str, UUID], model: type, key: str
) -> None:
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            await session.delete(await session.get(model, seeded[key]))
            await session.flush()


def test_all_metadata_foreign_keys_use_restrict() -> None:
    assert len(Base.metadata.tables) == 20
    assert all(
        fk.ondelete == "RESTRICT"
        for table in Base.metadata.tables.values()
        for fk in table.foreign_keys
    )


async def test_native_full_text_search_and_indexes(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    query = select(Fragrance).where(
        Fragrance.search_vector.op("@@")(func.plainto_tsquery("simple", "horizon"))
    )
    matches = (await session.scalars(query)).all()
    assert [item.id for item in matches] == [seeded["fragrance:1"]]
    assert "ix_fragrances_search" in {
        index.name for index in Fragrance.__table__.indexes
    }
    assert "ix_records_source_collected" in {
        index.name for index in SourceRecord.__table__.indexes
    }


async def test_default_unknown_note_and_invalid_claim_states(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    entry = ReleaseNote(release_id=seeded["release:edt"], note_id=seeded["note:1"])
    session.add(entry)
    await session.flush()
    assert entry.position == "unknown"
    for state, value in [("unknown", 2020), ("known", None)]:
        await reject(
            session,
            FieldProvenance(
                entity_link_id=seeded["link:1"],
                field_path="release_year",
                value_state=state,
                value=value,
                collected_at=datetime.now(UTC),
            ),
        )
    await reject(
        session,
        DataReviewQueue(
            source_record_id=seeded["record:1"],
            reason="Conflicting claim",
            status="resolved",
        ),
    )


async def test_external_ids_are_source_scoped_versioned_and_stable(
    session: AsyncSession, seeded: dict[str, UUID]
) -> None:
    await reject(
        session,
        SourceRecord(
            source_id=seeded["demo-source:1"],
            source_record_id="synthetic-release-1",
            collected_at=datetime.now(UTC),
        ),
    )
    session.add(
        SourceRecord(
            source_id=seeded["demo-source:1"],
            source_record_id="synthetic-release-1",
            revision=2,
            collected_at=datetime.now(UTC),
        )
    )
    session.add(
        SourceRecord(
            source_id=seeded["demo-source:2"],
            source_record_id="synthetic-release-1",
            collected_at=datetime.now(UTC),
        )
    )
    await session.flush()
