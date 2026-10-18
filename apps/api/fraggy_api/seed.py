"""Opt-in invented fixtures only. No HTTP client, file downloads or implicit commits."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .database import Base, create_engine
from .models import (
    Accord,
    Brand,
    BrandAlias,
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    Fragrance,
    FragranceFamily,
    FragranceRelease,
    FragranceVariant,
    IngestionRun,
    MediaAsset,
    Note,
    NoteAlias,
    Perfumer,
    ReleaseAccord,
    ReleaseNote,
    ReleasePerfumer,
    SourceEntityLink,
    SourceRecord,
)
from .settings import Settings

NAMESPACE = UUID("34c055e7-f091-45e9-88cc-10db7c5368e8")
COLLECTED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def demo_id(key: str) -> UUID:
    """Stable fixture keys are independent of mutable display names and slugs."""
    return uuid5(NAMESPACE, key)


async def seed_demo(
    session: AsyncSession,
    *,
    allow_demo_data: bool = False,
    publish_demo_catalog: bool = False,
) -> dict[str, UUID]:
    if not allow_demo_data:
        raise ValueError("Synthetic seed requires explicit allow_demo_data=True")
    rows: list[tuple[type[Base], dict[str, Any]]] = []
    ids: dict[str, UUID] = {}

    def row(model: type[Base], fixture_key: str, **values: Any) -> None:
        ids[fixture_key] = demo_id(fixture_key)
        rows.append((model, {"id": ids[fixture_key], **values}))

    row(
        Brand,
        "brand:1",
        name="Nacre Workshop",
        slug="nacre-workshop",
        country=None,
        description="Invented demonstration house; no real source description.",
    )
    row(Brand, "brand:2", name="Morrow Grove", slug="morrow-grove")
    row(BrandAlias, "brand-alias:1", brand_id=demo_id("brand:1"), name="Nacre Studio")
    row(FragranceFamily, "family:1", name="Woody", slug="woody")
    for i, (name, slug, brand) in enumerate(
        [
            ("Paper Horizon", "paper-horizon", 1),
            ("Quiet Tides", "quiet-tides", 1),
            ("Amber Geometry", "amber-geometry", 2),
            ("Glass Orchard", "glass-orchard", 2),
        ],
        1,
    ):
        row(
            Fragrance,
            f"fragrance:{i}",
            name=name,
            slug=slug,
            brand_id=demo_id(f"brand:{brand}"),
            family_id=demo_id("family:1") if i == 1 else None,
        )
    row(
        FragranceRelease,
        "release:edt",
        fragrance_id=demo_id("fragrance:1"),
        concentration="eau_de_toilette",
        release_year=2020,
    )
    row(
        FragranceRelease,
        "release:edp",
        fragrance_id=demo_id("fragrance:1"),
        concentration="eau_de_parfum",
        release_year=None,
    )
    row(
        FragranceRelease,
        "release:reformulation",
        fragrance_id=demo_id("fragrance:1"),
        concentration="eau_de_parfum",
        release_year=2025,
        version_label="Synthetic edition B",
        reformulation_of_id=demo_id("release:edp"),
    )
    for i in (2, 3, 4):
        row(
            FragranceRelease,
            f"release:{i}",
            fragrance_id=demo_id(f"fragrance:{i}"),
            concentration=None,
            release_year=None,
        )
    for key, release, size, packaging in [
        ("variant:1", "edp", 50, "Standard"),
        ("variant:2", "edp", 100, "Standard"),
        ("variant:3", "edt", 50, "Standard"),
        ("variant:4", "edp", 50, "Refill"),
    ]:
        row(
            FragranceVariant,
            key,
            release_id=demo_id("release:" + release),
            bottle_size_ml=size,
            original_size=size,
            original_unit="mL",
            packaging_label=packaging,
        )
    for i, name in enumerate(["Cedar", "Iris", "Bergamot", "Salt"], 1):
        row(Note, f"note:{i}", name=name, slug=name.lower())
    row(NoteAlias, "note-alias:1", note_id=demo_id("note:1"), name="Cedar wood")
    for i, position in enumerate(["base", "heart", "top", "unknown"], 1):
        row(
            ReleaseNote,
            f"release-note:{i}",
            release_id=demo_id("release:edp"),
            note_id=demo_id(f"note:{i}"),
            position=position,
            display_order=i - 1,
        )
    row(Accord, "accord:1", name="Woody", slug="woody")
    row(
        ReleaseAccord,
        "release-accord:1",
        release_id=demo_id("release:edp"),
        accord_id=demo_id("accord:1"),
    )
    for i, name in enumerate(["Lina Vale", "Oren Reed"], 1):
        row(Perfumer, f"perfumer:{i}", name=name, slug=f"fictional-perfumer-{i}")
        row(
            ReleasePerfumer,
            f"release-perfumer:{i}",
            release_id=demo_id("release:edp"),
            perfumer_id=demo_id(f"perfumer:{i}"),
        )
    registry_path = Path(__file__).resolve().parents[3] / "config/sources.json"
    for source in json.loads(registry_path.read_text())["sources"]:
        row(
            DataSource,
            "source:" + source["id"],
            key=source["id"],
            name=source["name"],
            website=source["website"],
            adapter_identifier=source["adapter"],
            source_type="website",
            enabled=False,
            authorization_status="pending_review",
            licensing_status="pending_review",
            rate_limit=source["rate_limit"],
            reuse_restrictions=source["reuse_restrictions"],
        )
    for i, year in [(1, 2020), (2, 2021)]:
        row(
            DataSource,
            f"demo-source:{i}",
            key=f"synthetic-demo-{i}",
            name=f"Fictional Archive {i}",
            website=f"https://example.invalid/archive-{i}",
            source_type="synthetic",
            enabled=False,
            authorization_status="synthetic",
            licensing_status="synthetic",
        )
        row(
            IngestionRun,
            f"run:{i}",
            source_id=demo_id(f"demo-source:{i}"),
            status="synthetic",
            started_at=COLLECTED_AT,
            completed_at=COLLECTED_AT,
            records_seen=1,
            records_accepted=1,
        )
        row(
            SourceRecord,
            f"record:{i}",
            source_id=demo_id(f"demo-source:{i}"),
            ingestion_run_id=demo_id(f"run:{i}"),
            source_record_id=f"synthetic-release-{i}",
            source_url=f"https://example.invalid/record-{i}",
            collected_at=COLLECTED_AT,
            payload={"synthetic": True, "release_year": year},
            storage_status="synthetic",
            redistribution_status="synthetic",
        )
        row(
            SourceEntityLink,
            f"link:{i}",
            source_record_id=demo_id(f"record:{i}"),
            release_id=demo_id("release:edp"),
            confidence="0.8",
        )
        row(
            FieldProvenance,
            f"claim:{i}",
            entity_link_id=demo_id(f"link:{i}"),
            field_path="release_year",
            value=year,
            value_state="conflicting",
            collected_at=COLLECTED_AT,
            usage_rights_status="synthetic",
            confidence="0.8",
            transformations=[{"name": "synthetic_fixture", "version": "1"}],
        )
    row(
        DataReviewQueue,
        "review:1",
        source_record_id=demo_id("record:2"),
        field_provenance_id=demo_id("claim:2"),
        release_id=demo_id("release:edp"),
        reason="Conflicting fictional release years: 2020 versus 2021",
        context={"claim_ids": [str(demo_id("claim:1")), str(demo_id("claim:2"))]},
    )
    row(
        MediaAsset,
        "media:1",
        entity_link_id=demo_id("link:1"),
        source_url="https://example.invalid/reference-only.svg",
        attribution="Invented reference only; no file exists or was downloaded.",
    )
    if publish_demo_catalog:
        # Only original fixture values receive grants; edited DB rows are never
        # granted new rights by this operation. All inserts preserve existing rows.
        original_rows = list(rows)
        row(
            DataSource,
            "public-source",
            key="synthetic-public-demo",
            name="Invented public catalog",
            website="https://example.invalid/demo",
            source_type="synthetic",
            authorization_status="synthetic",
            licensing_status="synthetic",
            enabled=False,
        )
        row(
            SourceRecord,
            "public-record",
            source_id=demo_id("public-source"),
            source_record_id="invented-catalog-v1",
            collected_at=COLLECTED_AT,
            storage_status="synthetic",
            redistribution_status="synthetic",
            processing_state="linked",
        )
        targets = {
            Brand: "brand_id",
            Fragrance: "fragrance_id",
            FragranceRelease: "release_id",
            Note: "note_id",
            Accord: "accord_id",
        }
        for model, values in original_rows:
            if model not in targets:
                continue
            identity = str(values["id"])
            link_key = "public-link:" + identity
            row(
                SourceEntityLink,
                link_key,
                source_record_id=demo_id("public-record"),
                review_status="approved",
                **{targets[model]: values["id"]},
            )
            fields = {
                key: value
                for key, value in values.items()
                if key
                in {
                    "name",
                    "slug",
                    "brand_id",
                    "fragrance_id",
                    "concentration",
                    "release_year",
                }
                and value is not None
            }
            if model is FragranceRelease:
                for field, association, key in [
                    ("notes", ReleaseNote, "note_id"),
                    ("accords", ReleaseAccord, "accord_id"),
                ]:
                    fields[field] = [
                        str(v[key])
                        for m, v in original_rows
                        if m is association and v["release_id"] == values["id"]
                    ]
            for field, value in fields.items():
                row(
                    FieldProvenance,
                    f"public-claim:{identity}:{field}",
                    entity_link_id=demo_id(link_key),
                    field_path=field,
                    value=str(value) if isinstance(value, UUID) else value,
                    value_state="known",
                    selection_status="selected",
                    usage_rights_status="synthetic",
                    collected_at=COLLECTED_AT,
                )
    for model, values in rows:
        await session.execute(
            insert(model).values(**values).on_conflict_do_nothing(index_elements=["id"])
        )
    return ids


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Opt-in local synthetic catalog; never production data"
    )
    parser.add_argument("--allow-demo-data", action="store_true")
    parser.add_argument(
        "--publish-demo-catalog",
        action="store_true",
        help="Add explicit synthetic public projection grants",
    )
    args = parser.parse_args()
    settings = Settings()
    if not args.allow_demo_data or settings.app_env == "production":
        raise SystemExit(
            "Refusing seed: explicit --allow-demo-data and non-production APP_ENV required"
        )
    from sqlalchemy.engine import make_url

    if make_url(settings.database_url.get_secret_value()).host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise SystemExit("Demo CLI is restricted to a loopback database")
    engine = create_engine(settings)
    try:
        async with async_sessionmaker(engine)() as session, session.begin():
            ids = await seed_demo(
                session,
                allow_demo_data=True,
                publish_demo_catalog=args.publish_demo_catalog,
            )
        print(
            f"Synthetic fixtures prepared ({len(ids)} stable IDs); existing rows preserved"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
