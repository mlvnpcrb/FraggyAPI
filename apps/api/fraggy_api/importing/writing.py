"""Canonical writes occur only after an explicit operator review decision."""

import re
import unicodedata
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Accord,
    Brand,
    BrandAlias,
    FieldProvenance,
    Fragrance,
    FragranceFamily,
    FragranceRelease,
    FragranceVariant,
    Note,
    NoteAlias,
    Perfumer,
    ReleaseAccord,
    ReleaseNote,
    ReleasePerfumer,
    SourceEntityLink,
    SourceRecord,
)
from .formats import ImportErrorSafe, Record, concentration, key
from .matching import brands


def clean(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).split())


def slug(name: str, identity: UUID) -> str:
    ascii_name = (
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    )
    prefix = (
        re.sub(r"[^a-z0-9]+", "-", ascii_name).strip("-")[:110].rstrip("-") or "record"
    )
    return f"{prefix}-{identity.hex}"


async def create(session: AsyncSession, model: Any, **values: Any) -> Any:
    entity = model(id=uuid4(), **values)
    session.add(entity)
    await session.flush()
    return entity


async def named_entity(session: AsyncSession, model: Any, name: str) -> Any:
    entity = await session.scalar(select(model).where(model.name_key == key(name)))
    if entity is None:
        identity = uuid4()
        entity = model(id=identity, name=clean(name), slug=slug(name, identity))
        session.add(entity)
        await session.flush()
    return entity


async def claims(
    session: AsyncSession,
    snapshot: SourceRecord,
    target: str,
    entity: Any,
    fields: dict[str, Any],
    *,
    originals: dict[str, Any] | None = None,
) -> None:
    link = await create(
        session,
        SourceEntityLink,
        source_record_id=snapshot.id,
        review_status="approved",
        **{target: entity.id},
    )
    for field, value in fields.items():
        actual = (
            getattr(entity, field) if field in entity.__mapper__.column_attrs else value
        )
        if isinstance(actual, UUID):
            actual = str(actual)
        matches = actual == (
            Decimal(str(value))
            if isinstance(actual, Decimal) and isinstance(value, (int, float))
            else value
        )
        session.add(
            FieldProvenance(
                entity_link_id=link.id,
                field_path=field,
                value=value,
                value_state="unknown"
                if value is None
                else "known"
                if matches
                else "conflicting",
                selection_status="selected"
                if matches and not field.startswith("incoming_")
                else "candidate",
                collected_at=snapshot.collected_at,
                usage_rights_status="pending_review",
                transformations=[
                    {
                        "name": "nfkc_whitespace_concentration_operator_link",
                        "version": "1",
                        "original_field": (originals or {}).get(field, field),
                    }
                ],
            )
        )
    await session.flush()


async def materialize(
    session: AsyncSession,
    snapshot: SourceRecord,
    record: Record,
    decision: str,
    target: UUID | None,
) -> FragranceRelease:
    owners = await brands(session, record.brand_name)
    if len(owners) > 1:
        raise ImportErrorSafe(
            "Ambiguous brand identity requires alias correction before review"
        )
    owner = owners[0] if owners else None
    existing = await session.get(FragranceRelease, target) if target else None
    if decision in {"link_existing", "separate_release"} and existing is None:
        raise ImportErrorSafe("An existing release UUID is required")
    line = await session.get(Fragrance, existing.fragrance_id) if existing else None
    if line is not None:
        if (
            owner is None
            or line.brand_id != owner.id
            or key(line.name) != key(record.fragrance_name)
        ):
            raise ImportErrorSafe(
                "Target brand/fragrance identity conflicts; do not merge flankers"
            )
    if decision == "link_existing":
        assert existing is not None and line is not None and owner is not None
        for field, incoming in [
            ("concentration", concentration(record.concentration)),
            ("release_year", record.release_year),
            ("version_label", record.version_label),
        ]:
            actual = getattr(existing, field)
            if (
                incoming is not None
                and incoming != actual
                and (actual is not None or field == "version_label")
            ):
                raise ImportErrorSafe(
                    "Concentration/year/version conflict requires a separate release"
                )
        if record.gtin and await session.scalar(
            select(FragranceVariant.id)
            .where(
                FragranceVariant.gtin == record.gtin,
                FragranceVariant.release_id != existing.id,
            )
            .limit(1)
        ):
            raise ImportErrorSafe("Product identifier conflicts with another release")
        release = existing
    else:
        if owner is None:
            owner = await named_entity(session, Brand, record.brand_name)
        if decision != "separate_release":
            family = (
                await named_entity(session, FragranceFamily, record.family)
                if record.family
                else None
            )
            identity = uuid4()
            line = Fragrance(
                id=identity,
                name=clean(record.fragrance_name),
                slug=slug(record.fragrance_name, identity),
                brand_id=owner.id,
                family_id=family.id if family else None,
            )
            session.add(line)
            await session.flush()
        assert line is not None
        release = await create(
            session,
            FragranceRelease,
            fragrance_id=line.id,
            concentration=concentration(record.concentration),
            original_concentration=record.concentration,
            release_year=record.release_year,
            version_label=record.version_label,
        )
        for alias in record.brand_aliases:
            if not await session.scalar(
                select(BrandAlias.id).where(
                    BrandAlias.brand_id == owner.id, BrandAlias.name_key == key(alias)
                )
            ):
                await create(session, BrandAlias, brand_id=owner.id, name=clean(alias))
        note_ids = []
        for order, note in enumerate(record.notes):
            aliases = select(NoteAlias.note_id).where(
                NoteAlias.name_key == key(note.name)
            )
            options = list(
                (
                    await session.scalars(
                        select(Note)
                        .where((Note.name_key == key(note.name)) | Note.id.in_(aliases))
                        .order_by(Note.id)
                        .limit(2)
                    )
                ).all()
            )
            if len(options) > 1:
                raise ImportErrorSafe(
                    "Ambiguous note alias requires correction before review"
                )
            entity = (
                options[0] if options else await named_entity(session, Note, note.name)
            )
            note_ids.append(str(entity.id))
            if not await session.scalar(
                select(ReleaseNote.id).where(
                    ReleaseNote.release_id == release.id,
                    ReleaseNote.note_id == entity.id,
                    ReleaseNote.position == note.position,
                )
            ):
                await create(
                    session,
                    ReleaseNote,
                    release_id=release.id,
                    note_id=entity.id,
                    position=note.position,
                    display_order=order,
                )
            for alias in note.aliases:
                if not await session.scalar(
                    select(NoteAlias.id).where(
                        NoteAlias.note_id == entity.id, NoteAlias.name_key == key(alias)
                    )
                ):
                    await create(
                        session, NoteAlias, note_id=entity.id, name=clean(alias)
                    )
            # One link per source snapshot/entity, even for repeated note positions.
            if note_ids.count(str(entity.id)) == 1:
                await claims(
                    session,
                    snapshot,
                    "note_id",
                    entity,
                    {
                        "name": clean(note.name),
                        "slug": entity.slug,
                        "aliases": note.aliases,
                    },
                )
        accord_ids = []
        for order, name in enumerate(dict.fromkeys(record.accords)):
            entity = await named_entity(session, Accord, name)
            if str(entity.id) in accord_ids:
                continue
            accord_ids.append(str(entity.id))
            await create(
                session,
                ReleaseAccord,
                release_id=release.id,
                accord_id=entity.id,
                display_order=order,
            )
            await claims(
                session,
                snapshot,
                "accord_id",
                entity,
                {"name": clean(name), "slug": entity.slug},
            )
        for name in record.perfumers:
            # Names alone never prove that two people are the same person.
            identity = uuid4()
            entity = Perfumer(id=identity, name=clean(name), slug=slug(name, identity))
            session.add(entity)
            await session.flush()
            await create(
                session, ReleasePerfumer, release_id=release.id, perfumer_id=entity.id
            )
            await claims(
                session,
                snapshot,
                "perfumer_id",
                entity,
                {"name": clean(name), "slug": entity.slug},
            )
        sizes: list[float | None] = list(dict.fromkeys(record.bottle_sizes_ml))
        for size in sizes or ([None] if record.gtin else []):
            variant = await create(
                session,
                FragranceVariant,
                release_id=release.id,
                bottle_size_ml=size,
                original_size=size,
                original_unit="mL" if size is not None else None,
                gtin=record.gtin,
            )
            await claims(
                session,
                snapshot,
                "variant_id",
                variant,
                {"bottle_size_ml": size, "gtin": record.gtin},
                originals={"bottle_size_ml": "bottle_sizes_ml"},
            )
    assert owner is not None and line is not None
    await claims(
        session,
        snapshot,
        "brand_id",
        owner,
        {
            "name": clean(record.brand_name),
            "slug": owner.slug,
            "aliases": record.brand_aliases,
        },
        originals={"name": "brand_name"},
    )
    await claims(
        session,
        snapshot,
        "fragrance_id",
        line,
        {
            "name": clean(record.fragrance_name),
            "slug": line.slug,
            "brand_id": str(owner.id),
            "family": record.family,
            "collection": record.collection,
        },
        originals={"name": "fragrance_name"},
    )
    release_fields: dict[str, Any] = {
        "fragrance_id": str(line.id),
        "concentration": concentration(record.concentration),
        "release_year": record.release_year,
        "version_label": record.version_label,
    }
    if decision != "link_existing":
        release_fields.update(
            notes=sorted(set(note_ids)), accords=sorted(set(accord_ids))
        )
    else:
        # Preserve all incoming composition/variant claims without changing canonical
        # associations or incorrectly granting rights to existing UUID lists.
        release_fields.update(
            incoming_notes=[n.model_dump() for n in record.notes],
            incoming_accords=record.accords,
            incoming_perfumers=record.perfumers,
            incoming_sizes=record.bottle_sizes_ml,
            incoming_gtin=record.gtin,
        )
    if decision != "link_existing":
        release_fields["note_positions"] = [
            {"note_id": identity, "position": note.position}
            for identity, note in zip(note_ids, record.notes, strict=True)
        ]
    await claims(
        session,
        snapshot,
        "release_id",
        release,
        release_fields,
        originals={
            "incoming_notes": "notes",
            "incoming_accords": "accords",
            "incoming_perfumers": "perfumers",
            "incoming_sizes": "bottle_sizes_ml",
            "incoming_gtin": "gtin",
        },
    )
    snapshot.processing_state = "linked"
    return release
