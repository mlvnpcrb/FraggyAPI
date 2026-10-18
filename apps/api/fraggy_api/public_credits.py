"""One bounded credit query for a projected page, with relative JSON pointers."""

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import any_, bindparam, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from .attribution import PublicAttribution
from .importing.formats import digest
from .models import DataSource, FieldProvenance, SourceEntityLink, SourceRecord
from .public_catalog import (
    FragrancePublic,
    NamedPublic,
    ReleasePublic,
    rights_condition,
)
from .public_rights import Access

# target, entity UUID, claim field, displayed value, array membership,
# scopes receiving the credit and relative JSON pointers in each scope.
MAX_CREDIT_CLAIMS = 20000

Reference = tuple[str, UUID, str, Any, bool, list[tuple[Any, str]]]


async def attach_credits(
    session: AsyncSession,
    roots: list[Any],
    access: Access,
    *,
    target: str = "fragrance_id",
) -> None:
    credit_sources = [identity for identity, credit in access.sources.items() if credit]
    if not roots or not credit_sources:
        return
    refs: list[Reference] = []

    def ref(
        kind: str,
        entity: Any,
        field: str,
        value: Any,
        scopes: list[tuple[Any, str]],
        *,
        contains: bool = False,
    ) -> None:
        refs.append((kind, entity.id, field, value, contains, scopes))

    def named(entity: NamedPublic, kind: str, ancestors: list[tuple[Any, str]]) -> None:
        scopes = [(entity, ""), *ancestors]
        for field in ("name", "slug"):
            ref(
                kind,
                entity,
                field,
                getattr(entity, field),
                [(s, p + "/" + field) for s, p in scopes],
            )

    for root in roots:
        named(root, target, [])
        if not isinstance(root, FragrancePublic):
            continue
        named(root.brand, "brand_id", [(root, "/brand")])
        ref("fragrance_id", root, "brand_id", str(root.brand.id), [(root, "/brand/id")])
        for i, release in enumerate(root.releases):
            prefix = f"/releases/{i}"
            scopes: list[tuple[Any, str]] = [(release, ""), (root, prefix)]
            ref(
                "release_id",
                release,
                "fragrance_id",
                str(root.id),
                [(s, p + "/id") for s, p in scopes],
            )
            for field in ("concentration", "release_year"):
                value = getattr(release, field)
                if value is not None:
                    ref(
                        "release_id",
                        release,
                        field,
                        value,
                        [(s, p + "/" + field) for s, p in scopes],
                    )
            for field, kind in (("notes", "note_id"), ("accords", "accord_id")):
                for j, item in enumerate(getattr(release, field)):
                    path = f"/{field}/{j}"
                    named(item, kind, [(release, path), (root, prefix + path)])
                    ref(
                        "release_id",
                        release,
                        field,
                        str(item.id),
                        [(s, p + path + "/id") for s, p in scopes],
                        contains=True,
                    )
    ids: dict[str, set[UUID]] = defaultdict(set)
    indexed: dict[tuple[str, UUID, str], list[Reference]] = defaultdict(list)
    for entry in refs:
        ids[entry[0]].add(entry[1])
        indexed[entry[:3]].append(entry)
    c, link, record, source = (
        FieldProvenance,
        SourceEntityLink,
        SourceRecord,
        DataSource,
    )
    targets = tuple(ids)
    rows = (
        await session.execute(
            select(
                source.id,
                c.field_path,
                c.value,
                *(getattr(link, kind) for kind in targets),
            )
            .join(link, c.entity_link_id == link.id)
            .join(record, link.source_record_id == record.id)
            .join(source, record.source_id == source.id)
            .where(
                source.id.in_(credit_sources),
                or_(
                    *(
                        getattr(link, kind)
                        == any_(
                            bindparam(
                                f"credit_{kind}",
                                list(values),
                                type_=ARRAY(PGUUID(as_uuid=True)),
                            )
                        )
                        for kind, values in ids.items()
                    )
                ),
                link.review_status == "approved",
                record.processing_state == "linked",
                c.selection_status == "selected",
                c.value_state == "known",
                rights_condition(access),
            )
            .distinct()
            .order_by(source.id, c.field_path, c.value)
            .limit(MAX_CREDIT_CLAIMS + 1)
        )
    ).all()
    if len(rows) > MAX_CREDIT_CLAIMS:
        # Never return a truncated set of required credits with published values.
        raise HTTPException(503, "Attribution projection limit exceeded")
    grouped: dict[int, dict[str, set[str]]] = defaultdict(dict)
    objects: dict[int, NamedPublic | ReleasePublic] = {}
    metadata: dict[str, dict[str, Any]] = {}
    source_credits: dict[UUID, str] = {}
    for source_id in credit_sources:
        attribution = access.sources[source_id]
        assert attribution is not None
        public = attribution.model_dump(mode="json")
        credit_id = digest(public)
        source_credits[source_id] = credit_id
        metadata[credit_id] = public
    for row in rows:
        source_id, field, claim_value, *entities = row
        credit_id = source_credits[source_id]
        for kind, identity in zip(targets, entities, strict=True):
            if identity is None:
                continue
            for _, _, _, value, contains, scopes in indexed.get(
                (kind, identity, field), []
            ):
                matches = (
                    isinstance(claim_value, list) and value in claim_value
                    if contains
                    else value == claim_value
                )
                if not matches:
                    continue
                for obj, path in scopes:
                    obj_key = id(obj)
                    objects[obj_key] = obj
                    grouped[obj_key].setdefault(credit_id, set()).add(path)
    for obj_key, entries in grouped.items():
        # DTOs are frozen; populate their mutable list before serialization only.
        objects[obj_key].attributions.extend(
            PublicAttribution(**metadata[k], id=k, fields=sorted(entries[k]))
            for k in sorted(entries)
        )
