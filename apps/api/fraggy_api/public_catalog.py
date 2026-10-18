"""Fail-closed public projection. Internal ORM objects never cross this boundary."""

from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from .models import DataSource, FieldProvenance, SourceEntityLink, SourceRecord


class PublicModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NamedPublic(PublicModel):
    id: UUID
    name: str
    slug: str
    synthetic: bool


class ReleasePublic(PublicModel):
    id: UUID
    concentration: str | None
    release_year: int | None
    notes: list[NamedPublic]
    accords: list[NamedPublic]
    synthetic: bool


class FragrancePublic(NamedPublic):
    brand: NamedPublic
    releases: list[ReleasePublic]
    releases_truncated: bool


class Pagination(PublicModel):
    limit: int
    offset: int
    total: int


T = TypeVar("T")


class Page(PublicModel, Generic[T]):
    data: list[T]
    pagination: Pagination


class Item(PublicModel, Generic[T]):
    data: T


def grant(
    target: str,
    identity: Any,
    field: str,
    value: Any,
    demo: bool,
    *,
    contains: bool = False,
    synthetic_only: bool = False,
) -> ColumnElement[bool]:
    """Compare approved claim to current value; stale grants cannot publish edits.

    A selected claim alone is insufficient. Real publication additionally requires
    reviewed source policy, record redistribution evidence and field evidence.
    Synthetic grants have a distinct, non-production-only branch.
    """
    source, record, link, claim = (
        DataSource,
        SourceRecord,
        SourceEntityLink,
        FieldProvenance,
    )
    approved = and_(
        source.source_type.not_in(["synthetic", "synthetic_file_import"]),
        source.authorization_status == "approved",
        source.licensing_status == "approved",
        source.reviewed_at.is_not(None),
        func.jsonb_array_length(source.evidence) > 0,
        source.permitted_fields.contains([field]),
        func.jsonb_array_length(source.reuse_restrictions) == 0,
        record.storage_status == "approved",
        record.redistribution_status == "approved",
        claim.usage_rights_status == "approved",
    )
    synthetic = and_(
        source.source_type.in_(["synthetic", "synthetic_file_import"]),
        source.authorization_status == "synthetic",
        source.licensing_status == "synthetic",
        record.storage_status == "synthetic",
        record.redistribution_status == "synthetic",
        claim.usage_rights_status == "synthetic",
    )
    rights = (
        synthetic if synthetic_only else or_(approved, synthetic) if demo else approved
    )
    if synthetic_only and not demo:
        rights = false()
    comparison = (
        claim.value.contains(func.jsonb_build_array(value))
        if contains
        else claim.value == func.to_jsonb(value)
    )
    return exists(
        select(1)
        .select_from(claim)
        .join(link, claim.entity_link_id == link.id)
        .join(record, link.source_record_id == record.id)
        .join(source, record.source_id == source.id)
        .where(
            getattr(link, target) == identity,
            link.review_status == "approved",
            record.processing_state == "linked",
            claim.selection_status == "selected",
            claim.value_state == "known",
            claim.field_path == field,
            comparison,
            rights,
        )
    )


def visible(model: Any, target: str, demo: bool) -> ColumnElement[bool]:
    return and_(
        grant(target, model.id, "name", model.name, demo),
        grant(target, model.id, "slug", model.slug, demo),
    )
