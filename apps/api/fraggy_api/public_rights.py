"""Request-scoped reviewed file policies, shared by SQL grants and credits."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .attribution import Attribution
from .models import DataSource

FILE_TYPES = ("file_import", "synthetic_file_import")


@dataclass(frozen=True)
class Access:
    demo: bool
    sources: dict[UUID, Attribution | None] = field(default_factory=dict)


def reviewed_attribution(source: DataSource) -> tuple[bool, Attribution | None]:
    # Private evidence stays here. Only the explicit public DTO is projected.
    from .importing.formats import Manifest, digest

    try:
        events = [
            e for e in source.evidence if e.get("kind") == "operator_source_review"
        ]
        event: dict[str, Any] = events[-1]
        manifest = Manifest.model_validate(event["manifest"])
        if (
            event.get("manifest_digest") != digest(manifest.model_dump(mode="json"))
            or not event.get("storage")
            or not manifest.storage_permissions
            or not manifest.redistribution_permissions
            or manifest.redistribution_conditions
            or set(source.permitted_fields) != set(event["publication_fields"])
            or not set(source.permitted_fields) <= set(manifest.permitted_fields)
            or list(source.reuse_restrictions) != manifest.attribution_requirements
            or manifest.source_id != source.key
            or (manifest.synthetic != (source.source_type == "synthetic_file_import"))
        ):
            return False, None
        attribution = manifest.attribution
        if attribution is None:
            return not bool(manifest.attribution_requirements), None
        if (
            event.get("attribution_accepted") is not True
            or attribution.provider != manifest.provider
            or not attribution.supported()
        ):
            return False, None
        return True, attribution
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return False, None


async def read_access(session: AsyncSession, demo: bool) -> Access:
    sources = (
        await session.scalars(
            select(DataSource)
            .where(
                DataSource.source_type.in_(FILE_TYPES),
                DataSource.authorization_status.in_(["approved", "synthetic"]),
                DataSource.licensing_status.in_(["approved", "synthetic"]),
            )
            .order_by(DataSource.id)
            .limit(1001)
        )
    ).all()
    # Bounded policy read. Overflow hides file grants until an operator reduces
    # active policies; it never falls back to granting unreviewed publication.
    if len(sources) > 1000:
        return Access(demo)
    policies: dict[UUID, Attribution | None] = {}
    for source in sources:
        valid, attribution = reviewed_attribution(source)
        if valid:
            policies[source.id] = attribution
    return Access(demo, policies)
