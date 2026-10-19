"""Explicit synthetic load fixtures, refused outside owned disposable databases."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..importing.authorization import review_source
from ..importing.formats import digest, manifest_file
from ..models import (
    Accord,
    Brand,
    FieldProvenance,
    Fragrance,
    FragranceAlias,
    FragranceFamily,
    FragranceRelease,
    FragranceVariant,
    Note,
    Perfumer,
    ReleaseAccord,
    ReleaseNote,
    ReleasePerfumer,
    SourceEntityLink,
    SourceRecord,
)

NAMESPACE = UUID("91ef1ff1-5c2f-421d-ab31-caf9db49b1a3")


def identity(key: str) -> UUID:
    return uuid5(NAMESPACE, key)


async def generate(
    session: AsyncSession, size: int, *, search_aliases: bool = False
) -> dict[str, Any]:
    name = await session.scalar(text("SELECT current_database()"))
    if (
        not isinstance(name, str)
        or not name.startswith(("fraggy_bench_", "fraggy_test_", "fraggy_preview_"))
        or not 1 <= size <= 10000
    ):
        raise ValueError(
            "Synthetic fixtures require an owned disposable test/benchmark/preview database and 1–10000 fragrances"
        )
    if await session.scalar(select(Brand.id).limit(1)) is not None:
        raise ValueError("Benchmark database must be empty; never overwrite data")
    manifest = manifest_file(
        Path(__file__).resolve().parents[4]
        / "data/examples/attributed-source-manifest.json"
    )
    attribution = manifest.attribution
    assert attribution is not None
    # Explicit original fictional benchmark policy, never a license auto-approval
    # for external data. This command only runs in owned disposable databases.
    manifest = manifest.model_copy(
        update={
            "source_id": "fictional-benchmark",
            "attribution": attribution.model_copy(
                update={"last_verified": datetime.now(UTC).date()}
            ),
        }
    )
    source = await review_source(
        session,
        manifest,
        "synthetic-benchmark",
        "Original invented benchmark fixtures only",
        allow_storage=True,
        publish_fields=[
            "name",
            "slug",
            "brand_id",
            "fragrance_id",
            "concentration",
            "release_year",
            "notes",
            "accords",
            *(["aliases"] if search_aliases else []),
        ],
        accept_attribution=True,
    )
    now = datetime.now(UTC)
    store: dict[Any, list[dict[str, Any]]] = {}

    def add(model: Any, **row: Any) -> None:
        store.setdefault(model, []).append(row)

    def claim(record: UUID, target: str, entity: UUID, values: dict[str, Any]) -> None:
        link = identity(f"link:{record}:{target}:{entity}")
        add(
            SourceEntityLink,
            id=link,
            source_record_id=record,
            review_status="approved",
            **{target: entity},
        )
        for field, value in values.items():
            add(
                FieldProvenance,
                id=identity(f"claim:{link}:{field}"),
                entity_link_id=link,
                field_path=field,
                value=value,
                value_state="unknown" if value is None else "known",
                selection_status="candidate" if value is None else "selected",
                collected_at=now,
                transformations=[
                    {"operation": "original_synthetic_benchmark", "version": 1}
                ],
                usage_rights_status="synthetic",
            )

    houses = max(10, min(100, size // 10))
    for i in range(houses):
        add(
            Brand,
            id=identity(f"brand:{i}"),
            name=f"Invented House {i:03}",
            slug=f"invented-house-{i:03}",
        )
    for i in range(4):
        add(
            FragranceFamily,
            id=identity(f"family:{i}"),
            name=f"Fictional Family {i}",
            slug=f"fictional-family-{i}",
        )
    for i in range(24):
        add(
            Note,
            id=identity(f"note:{i}"),
            name=f"Imagined Note {i:02}",
            slug=f"imagined-note-{i:02}",
        )
    for i in range(8):
        add(
            Accord,
            id=identity(f"accord:{i}"),
            name=f"Imagined Accord {i}",
            slug=f"imagined-accord-{i}",
        )
    for i in range(20):
        add(
            Perfumer,
            id=identity(f"perfumer:{i}"),
            name=f"Fictional Perfumer {i}",
            slug=f"fictional-perfumer-{i}",
        )
    releases = 0
    for i in range(size):
        record = identity(f"record:{i}")
        fragrance = identity(f"fragrance:{i}")
        brand = identity(f"brand:{i % houses}")
        title = f"Fable {'Cedar' if i % 2 else 'Iris'} {i:05}" + (
            " Night" if i % 7 == 0 else ""
        )
        slug = f"fable-{i:05}"
        alias = f"Original Archive {i:05}"
        if search_aliases and i % 100 == 0:
            add(
                FragranceAlias,
                id=identity(f"alias:{i}"),
                fragrance_id=fragrance,
                name=alias,
            )
        add(
            SourceRecord,
            id=record,
            source_id=source.id,
            source_record_id=f"invented-{i}",
            collected_at=now,
            storage_status="synthetic",
            redistribution_status="synthetic",
            processing_state="linked",
            payload={
                "original": {"fictional_benchmark": True},
                "manifest_digest": digest(manifest.model_dump(mode="json")),
            },
        )
        add(
            Fragrance,
            id=fragrance,
            brand_id=brand,
            family_id=identity(f"family:{i % 4}"),
            name=title,
            slug=slug,
        )
        claim(
            record,
            "brand_id",
            brand,
            {
                "name": f"Invented House {i % houses:03}",
                "slug": f"invented-house-{i % houses:03}",
            },
        )
        claim(
            record,
            "fragrance_id",
            fragrance,
            {
                "name": title,
                "slug": slug,
                "brand_id": str(brand),
                **({"aliases": [alias]} if search_aliases and i % 100 == 0 else {}),
            },
        )
        variants: list[tuple[str, str, int | None, UUID | None]] = [
            ("edp", "eau_de_parfum", 2020, None),
            ("edt", "eau_de_toilette", 2021, None),
        ]
        if i % 10 == 0:
            variants.append(
                ("reform", "eau_de_parfum", 2025, identity(f"release:{i}:edp"))
            )
        for kind, concentration, year, prior in variants:
            release = identity(f"release:{i}:{kind}")
            releases += 1
            year = year if i % 13 else None
            add(
                FragranceRelease,
                id=release,
                fragrance_id=fragrance,
                concentration=concentration,
                release_year=year,
                version_label="Fictional reformulation" if prior else None,
                reformulation_of_id=prior,
            )
            noteids = []
            for j, position in enumerate(("top", "heart", "base")):
                k = (i + j) % 24
                note = identity(f"note:{k}")
                noteids.append(str(note))
                add(
                    ReleaseNote,
                    id=identity(f"release-note:{release}:{j}"),
                    release_id=release,
                    note_id=note,
                    position=position,
                )
                claim(
                    record,
                    "note_id",
                    note,
                    {"name": f"Imagined Note {k:02}", "slug": f"imagined-note-{k:02}"},
                ) if kind == "edp" else None
            accord = identity(f"accord:{i % 8}")
            add(
                ReleaseAccord,
                id=identity(f"release-accord:{release}"),
                release_id=release,
                accord_id=accord,
            )
            if kind == "edp":
                claim(
                    record,
                    "accord_id",
                    accord,
                    {
                        "name": f"Imagined Accord {i % 8}",
                        "slug": f"imagined-accord-{i % 8}",
                    },
                )
            add(
                ReleasePerfumer,
                id=identity(f"release-perfumer:{release}"),
                release_id=release,
                perfumer_id=identity(f"perfumer:{i % 20}"),
            )
            for ml in (50, 100):
                add(
                    FragranceVariant,
                    id=identity(f"bottle:{release}:{ml}"),
                    release_id=release,
                    bottle_size_ml=ml,
                    original_size=ml,
                    original_unit="mL",
                )
            claim(
                record,
                "release_id",
                release,
                {
                    "fragrance_id": str(fragrance),
                    "concentration": concentration,
                    "release_year": year,
                    "notes": sorted(noteids),
                    "accords": [str(accord)],
                },
            )
    # Topological insert order; bounded executemany avoids parameter limits.
    order = [
        Brand,
        FragranceFamily,
        Note,
        Accord,
        Perfumer,
        SourceRecord,
        Fragrance,
        FragranceAlias,
        FragranceRelease,
        FragranceVariant,
        ReleaseNote,
        ReleaseAccord,
        ReleasePerfumer,
        SourceEntityLink,
        FieldProvenance,
    ]
    for model in order:
        rows = store.get(model, [])
        if model is SourceEntityLink:
            rows.sort(
                key=lambda row: next(
                    k for k in row if k.endswith("_id") and k != "source_record_id"
                )
            )
        for offset in range(0, len(rows), 500):
            await session.execute(
                insert(model).execution_options(render_nulls=True),
                rows[offset : offset + 500],
            )
    await session.flush()
    return {
        "fragrances": size,
        "brands": houses,
        "releases": releases,
        "notes": 24,
        "accords": 8,
        "variants": releases * 2,
        "claims": len(store[FieldProvenance]),
        "source_id": str(source.id),
        "note_id": str(identity("note:0")),
        "brand_slug": "invented-house-000",
    }
