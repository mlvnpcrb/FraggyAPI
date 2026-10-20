"""PostgreSQL search rights and durable provider-independent enrichment regressions."""

# ruff: noqa: F811

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fraggy_api.collection.enrichment import (
    intent_summary,
    request_intent,
    stage_evidence_comparison,
)
from fraggy_api.collection.providers import PROVIDERS, records_for_review
from fraggy_api.collection.transport import HTTPTransport
from fraggy_api.importing.authorization import review_source
from fraggy_api.importing.formats import Record, manifest_file
from fraggy_api.importing.pipeline import stage
from fraggy_api.models import (
    BrandAlias,
    EnrichmentIntent,
    FieldProvenance,
    Fragrance,
    FragranceAlias,
    SourceEntityLink,
)
from fraggy_api.seed import demo_id
from sqlalchemy import func, select
from test_openbeautyfacts import page
from test_public_api import client  # noqa: F401, F811 - shared rights-aware HTTP fixture


@pytest.mark.parametrize(
    "query,total",
    [
        ("Nacre Paper Hroizon", 1),
        ("Nacra Horizon", 1),
        ("Morrow amber", 1),
        ("Paper Horizon EDP", 1),
        ("Paper Horizon EDT", 1),
        ("Lattafa Khamrah", 0),
    ],
)
async def test_combined_brand_typo_and_concentration(client, query, total):
    response = await client.get("/api/v1/fragrances/search", params={"q": query})
    assert response.status_code == 200, response.text
    assert response.json()["pagination"]["total"] == total


async def test_aliases_require_current_field_rights(client, session):
    fragrance = demo_id("fragrance:1")
    session.add(FragranceAlias(fragrance_id=fragrance, name="Zephyr Codex"))
    await session.flush()

    async def count(query):
        return (
            await client.get("/api/v1/fragrances/search", params={"q": query})
        ).json()["pagination"]["total"]

    assert await count("Zephyr Codex") == 0
    claim = FieldProvenance(
        entity_link_id=demo_id("public-link:" + str(fragrance)),
        field_path="aliases",
        value=["Zephyr Codex"],
        value_state="known",
        selection_status="selected",
        usage_rights_status="synthetic",
        transformations=[],
        collected_at=datetime.now(UTC),
    )
    session.add(claim)
    await session.flush()
    assert await count("Zephyr Codex") == 1
    assert await count("Zephyr Cdoex") == 1
    claim.usage_rights_status = "restricted"
    await session.flush()
    assert await count("Zephyr Codex") == 0
    # Existing brand aliases are also private until explicitly permitted.
    alias = await session.scalar(
        select(BrandAlias).where(BrandAlias.name == "Nacre Studio")
    )
    assert alias
    assert await count("Studio Horizon") == 0
    session.add(
        FieldProvenance(
            entity_link_id=demo_id("public-link:" + str(alias.brand_id)),
            field_path="aliases",
            value=[alias.name],
            value_state="known",
            selection_status="selected",
            usage_rights_status="synthetic",
            transformations=[],
            collected_at=datetime.now(UTC),
        )
    )
    await session.flush()
    assert await count("Studio Horizon") == 1


async def test_search_never_dispatches_or_creates_intents(client, session, monkeypatch):
    def deny(*args, **kwargs):
        raise AssertionError("Search must never call transport")

    monkeypatch.setattr(HTTPTransport, "fetch", deny)
    assert (
        await client.get("/api/v1/fragrances/search", params={"q": "Paper\x00"})
    ).status_code == 400
    assert (await client.get("/api/v1/fragrances/search?q=Paper")).status_code == 200
    assert (
        await client.get("/api/v1/fragrances/search", params={"q": "ﬃ" * 100})
    ).status_code == 400
    assert await session.scalar(select(func.count()).select_from(EnrichmentIntent)) == 0
    assert (
        await client.get(
            "/api/v1/fragrances/search?q=Paper+EDP&concentration=eau_de_toilette"
        )
    ).status_code == 400
    assert (
        await client.get("/api/v1/fragrances/search", params={"q": "a " * 17})
    ).status_code == 400


async def test_provider_independent_deduplication_and_cooldown(session):
    at = datetime.now(UTC)
    a = await request_intent(session, "openbeautyfacts", "Lattafa   Khamrah", at)
    b = await request_intent(
        session, "openbeautyfacts", "LATTAFA KHAMRAH", at + timedelta(minutes=1)
    )
    other = await request_intent(session, "parfumo", "Lattafa Khamrah", at)
    strength = await request_intent(
        session, "openbeautyfacts", "Lattafa Khamrah", at, concentration="EDT"
    )
    assert a.id == b.id and a.id != other.id and a.id != strength.id
    original = a.next_allowed_at
    a.status = "review"
    assert (
        await request_intent(
            session, "openbeautyfacts", "Lattafa Khamrah", at + timedelta(minutes=2)
        )
    ).status == "review"
    assert a.next_allowed_at == original
    assert (
        await request_intent(
            session, "openbeautyfacts", "Lattafa Khamrah", at + timedelta(hours=2)
        )
    ).status == "pending"
    assert "query" not in intent_summary(a)
    assert all(not p.live_enabled for p in PROVIDERS.values())
    report, records = records_for_review("openbeautyfacts", page(), at)
    assert records[0].brand_name == "Original Fictional Studio"
    assert report["observations"][0]["raw"]["quantity"] == "50 ml"


async def test_per_field_review_retains_both_sources_and_no_canonical_writes(session):
    from pathlib import Path

    from fraggy_api.collection.policy import CollectionError

    manifest = manifest_file(
        Path(__file__).resolve().parents[3] / "data/examples/source-manifest.json"
    )
    ids = []
    sources = []
    for i in range(2):
        policy = manifest.model_copy(
            update={
                "source_id": "original-enrichment-" + uuid4().hex,
                "synthetic": True,
            }
        )
        source = await review_source(
            session,
            policy,
            "fixture-reviewer",
            "Original records only",
            allow_storage=True,
            publish_fields=[],
        )
        sources.append(source)
        record = Record(
            source_record_id="original",
            brand_name="Invented Workshop",
            fragrance_name="Imaginary River",
            concentration="EDP" if i == 0 else "eau_de_parfum",
            release_year=2020 + i,
            notes=[{"name": "Cedar" if not i else "Amber", "position": "base"}],
        )
        summary = await stage(session, [record], policy)
        from uuid import UUID

        ids.append(UUID(summary["records"][0]))
    before = await session.scalar(select(func.count()).select_from(Fragrance))
    report = await stage_evidence_comparison(session, *ids)
    assert report["fields"]["release_year"]["state"] == "conflict"
    assert report["fields"]["notes"]["state"] == "conflict"
    assert report["fields"]["brand_name"]["state"] == "agrees"
    assert report["fields"]["concentration"]["state"] == "agrees"
    assert report["fields"]["release_year"]["left_source_record"] == str(ids[0])
    assert not report["automatic_merge"] and not report["publication_authorized"]
    assert await session.scalar(select(func.count()).select_from(Fragrance)) == before
    sources[0].authorization_status = "restricted"
    await session.flush()
    with pytest.raises(CollectionError, match="evidence_source_revoked"):
        await stage_evidence_comparison(session, *ids)


async def test_bottle_filters_apply_to_one_rights_checked_variant(client, session):
    from fraggy_api.models import FragranceVariant

    variant = FragranceVariant(
        id=uuid4(),
        release_id=demo_id("release:edp"),
        bottle_size_ml=50,
        gtin="1234567890128",
    )
    session.add(variant)
    await session.flush()
    link = SourceEntityLink(
        id=uuid4(),
        source_record_id=demo_id("public-record"),
        variant_id=variant.id,
        review_status="approved",
    )
    session.add(link)
    await session.flush()
    for field, value in (("bottle_size_ml", 50), ("gtin", variant.gtin)):
        session.add(
            FieldProvenance(
                entity_link_id=link.id,
                field_path=field,
                value=value,
                value_state="known",
                selection_status="selected",
                collected_at=datetime.now(UTC),
                transformations=[],
                usage_rights_status="synthetic",
            )
        )
    await session.flush()

    async def count(**params):
        response = await client.get("/api/v1/fragrances/search", params=params)
        assert response.status_code == 200, response.text
        return response.json()["pagination"]["total"]

    assert await count(q="Paper eau de parfum", size_ml=50, gtin=variant.gtin) == 1
    assert await count(q="Paper EDT", size_ml=50, gtin=variant.gtin) == 0
    assert await count(q="Paper EDP", size_ml=100, gtin=variant.gtin) == 0
    claim = await session.scalar(
        select(FieldProvenance).where(
            FieldProvenance.entity_link_id == link.id,
            FieldProvenance.field_path == "gtin",
        )
    )
    claim.usage_rights_status = "restricted"
    await session.flush()
    assert await count(q="Paper EDP", gtin=variant.gtin) == 0


async def test_registered_provider_staging_preserves_raw_revisions_and_rights(session):
    from pathlib import Path
    from uuid import UUID

    from fraggy_api.collection.policy import CollectionError
    from fraggy_api.collection.providers import stage_provider_page
    from fraggy_api.models import SourceRecord

    at = datetime.now(UTC)
    manifest = manifest_file(
        Path(__file__).resolve().parents[3] / "data/examples/source-manifest.json"
    ).model_copy(update={"source_id": "openbeautyfacts", "synthetic": True})
    with pytest.raises(CollectionError, match="provider_storage_not_authorized"):
        await stage_provider_page(session, "openbeautyfacts", page(), at, manifest)
    manifest = manifest.model_copy(
        update={
            "permitted_fields": [
                *manifest.permitted_fields,
                "source_metadata",
                *[
                    "source_observation." + field
                    for field in (
                        "code",
                        "product_name",
                        "brands",
                        "categories_tags",
                        "quantity",
                        "product_type",
                        "last_modified_t",
                    )
                ],
            ]
        }
    )
    await review_source(
        session,
        manifest,
        "fixture-operator",
        "Original contract fixtures only",
        allow_storage=True,
        publish_fields=[],
    )
    first = await stage_provider_page(session, "openbeautyfacts", page(), at, manifest)
    again = await stage_provider_page(
        session, "openbeautyfacts", page(), at + timedelta(minutes=1), manifest
    )
    assert again["skipped"] == 1
    assert again["records"] == first["records"]
    snapshot = await session.get(SourceRecord, UUID(first["records"][0]))
    assert snapshot.payload["source_observation"]["raw"]["quantity"] == "50 ml"
    assert snapshot.payload["source_observation"]["collected_at"] == at.isoformat()
    changed = await stage_provider_page(
        session, "openbeautyfacts", page(last_modified_t=123), at, manifest
    )
    assert changed["records"] != first["records"]
    assert snapshot.redistribution_status == "pending_review"
    assert await session.scalar(select(func.count()).select_from(Fragrance)) == 0


async def test_variant_intent_cannot_target_an_unrelated_fragrance(client, session):
    from fraggy_api.collection.policy import CollectionError

    with pytest.raises(CollectionError, match="enrichment_variant_identity_mismatch"):
        await request_intent(
            session,
            "openbeautyfacts",
            "Original",
            datetime.now(UTC),
            fragrance_id=demo_id("fragrance:1"),
            variant_id=uuid4(),
        )
