"""Separate image storage review, publication review and revocation."""

import hashlib
import re
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..attribution import Attribution, PublicAttribution, safe_public_url
from ..importing.authorization import actor, writer_lock
from ..importing.formats import Strict, digest
from ..models import (
    Brand,
    DataSource,
    Fragrance,
    FragranceRelease,
    FragranceVariant,
    MediaAsset,
    SourceEntityLink,
    SourceRecord,
)
from ..public_rights import FILE_TYPES, Access, reviewed_attribution
from .processing import (
    MAX_BYTES,
    MediaError,
    location,
    optimize,
    read_blob,
    read_local,
    store,
)


class ImageRights(Strict):
    source_key: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=100)
    source_url: str
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    attribution: Attribution
    copyright_holder: str = Field(min_length=1, max_length=500)
    download: Literal[True]
    storage: Literal[True]
    transformations: Literal[True]
    website_display: Literal[True]
    pwa_display: Literal[True]
    commercial_use: Literal[True]
    api_delivery: Literal[True]
    third_party_hosting: bool = False
    retention_after_access_ends: bool = False
    reviewed_at: datetime
    expires_at: datetime
    evidence: str = Field(min_length=1, max_length=4000)
    synthetic: bool = False

    @field_validator("source_url")
    @classmethod
    def url(cls, value: str) -> str:
        return safe_public_url(value)

    @model_validator(mode="after")
    def dates(self) -> "ImageRights":
        if (
            not self.reviewed_at.tzinfo
            or not self.expires_at.tzinfo
            or self.expires_at <= self.reviewed_at
            or not self.attribution.supported()
            or not self.evidence.strip()
        ):
            raise ValueError("Current complete image rights required")
        if self.attribution.copyright_holder != self.copyright_holder:
            raise ValueError("Copyright holder must match public credit")
        return self


class Rendition(Strict):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    width: int = Field(ge=1, le=1200)
    height: int = Field(ge=1, le=1200)


class Metadata(Strict):
    alt: str = Field(min_length=1, max_length=300)
    role: Literal["primary", "gallery"]
    position: int = Field(ge=0, le=1000)
    renditions: dict[Literal["display", "thumb"], Rendition]

    @model_validator(mode="after")
    def complete(self) -> "Metadata":
        if (
            set(self.renditions) != {"display", "thumb"}
            or not self.alt.strip()
            or any(ord(c) < 32 for c in self.alt)
        ):
            raise ValueError("Complete image metadata required")
        return self


class ImagePublic(Strict):
    id: UUID
    url: str
    thumbnail_url: str
    width: int
    height: int
    thumbnail_width: int
    thumbnail_height: int
    alt: str
    role: Literal["primary", "gallery"]
    source_id: str
    source_url: str
    attribution: PublicAttribution
    synthetic: bool


class VariantImages(Strict):
    variant_id: UUID
    primary_image: ImagePublic | None = None
    images: list[ImagePublic] = Field(default_factory=list)


def query() -> Any:
    # One bounded batch, including canonical identity snapshots. No per-card reads.
    return (
        select(
            MediaAsset,
            SourceEntityLink,
            SourceRecord,
            DataSource,
            Fragrance,
            FragranceRelease,
            FragranceVariant,
        )
        .join(SourceEntityLink, MediaAsset.entity_link_id == SourceEntityLink.id)
        .join(SourceRecord, SourceEntityLink.source_record_id == SourceRecord.id)
        .join(DataSource, SourceRecord.source_id == DataSource.id)
        .outerjoin(FragranceVariant, SourceEntityLink.variant_id == FragranceVariant.id)
        .outerjoin(
            FragranceRelease,
            or_(
                SourceEntityLink.release_id == FragranceRelease.id,
                FragranceVariant.release_id == FragranceRelease.id,
            ),
        )
        .join(
            Fragrance,
            Fragrance.id
            == func.coalesce(
                SourceEntityLink.fragrance_id, FragranceRelease.fragrance_id
            ),
        )
        .join(Brand, Fragrance.brand_id == Brand.id)
    )


def binding(row: Any) -> str:
    asset, link, record, source, fragrance, release, variant = row
    return digest(
        {
            "asset": str(asset.id),
            "link": str(link.id),
            "record": str(record.id),
            "source": str(source.id),
            "fragrance": [
                str(fragrance.id),
                str(fragrance.brand_id),
                fragrance.name,
                fragrance.slug,
            ],
            "target": [
                str(link.fragrance_id),
                str(link.release_id),
                str(link.variant_id),
            ],
            "release": [
                str(release.id),
                str(release.fragrance_id),
                release.concentration,
                release.release_year,
                release.version_label,
            ]
            if release
            else None,
            "variant": [
                str(variant.id),
                str(variant.release_id),
                str(variant.bottle_size_ml),
                variant.gtin,
                variant.packaging_label,
            ]
            if variant
            else None,
            "content": asset.content_sha256,
            "metadata": asset.media_metadata,
        }
    )


def permitted(
    row: Any, *, demo: bool, publication: bool = True
) -> tuple[ImageRights, Metadata]:
    asset, link, record, source, *_ = row
    try:
        rights = ImageRights.model_validate(asset.image_policy["rights"])
        metadata = Metadata.model_validate(asset.media_metadata)
        now = datetime.now(UTC)
        expected = "synthetic" if rights.synthetic else "approved"
        if (
            (rights.synthetic and not demo)
            or asset.storage_status != "approved"
            or (publication and asset.usage_status != "approved")
            or asset.content_sha256 != rights.content_sha256
            or asset.image_policy.get("binding") != binding(row)
            or asset.image_policy.get("review_digest")
            != digest(
                {"rights": rights.model_dump(mode="json"), "binding": binding(row)}
            )
            or not asset.image_policy.get("storage_reviewer")
            or not asset.image_policy.get("storage_reason")
            or (publication and not asset.image_policy.get("publication_reviewer"))
            or (publication and not asset.image_policy.get("publication_reason"))
            or rights.reviewed_at > now
            or rights.expires_at <= now
            or rights.source_key != source.key
            or source.authorization_status != expected
            or source.licensing_status != expected
            or not source.reviewed_at
            or not source.evidence
            or (
                rights.synthetic
                != (source.source_type in {"synthetic", "synthetic_file_import"})
            )
            or (
                source.source_type in FILE_TYPES and not reviewed_attribution(source)[0]
            )
            or record.storage_status != expected
            or record.processing_state != "linked"
            or link.review_status != "approved"
        ):
            raise MediaError("image_not_authorized")
        return rights, metadata
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise MediaError("image_not_authorized") from exc


async def ingest(
    session: AsyncSession,
    root: Path,
    link_id: UUID,
    path: Path,
    mime: str,
    rights: ImageRights,
    *,
    reviewer: str,
    reason: str,
    alt: str,
    role: Literal["primary", "gallery"] = "gallery",
    position: int = 0,
) -> MediaAsset:
    actor(reviewer, reason)
    await writer_lock(session)
    link = await session.get(SourceEntityLink, link_id)
    if link is None or not any((link.fragrance_id, link.release_id, link.variant_id)):
        raise MediaError("image_target_required")
    # Rights must be reviewed before reading even a local image file.
    now = datetime.now(UTC)
    if rights.reviewed_at > now or rights.expires_at <= now:
        raise MediaError("expired_image_rights")
    data = read_local(path)

    if hashlib.sha256(data).hexdigest() != rights.content_sha256:
        raise MediaError("image_review_hash_mismatch")
    content_hash, outputs, sizes = optimize(data, mime)
    # Preserve independent assets/rights even when identical pixel blobs deduplicate.
    existing = await session.scalar(
        select(MediaAsset).where(
            MediaAsset.entity_link_id == link_id,
            MediaAsset.content_sha256 == content_hash,
            MediaAsset.storage_status == "approved",
        )
    )
    if existing is not None:
        raise MediaError("duplicate_target_image")
    asset = MediaAsset(
        id=uuid4(),
        entity_link_id=link_id,
        source_url=rights.source_url,
        attribution=rights.attribution.text,
        license_identifier=rights.attribution.license_name,
        license_url=rights.attribution.license_url,
        rights_evidence=rights.evidence,
        storage_status="approved",
        usage_status="pending_review",
        content_sha256=content_hash,
        media_metadata=Metadata(
            alt=alt,
            role=role,
            position=position,
            renditions={
                name: Rendition(
                    sha256=hashlib.sha256(value).hexdigest(),
                    width=sizes[name][0],
                    height=sizes[name][1],
                )
                for name, value in outputs.items()
            },
        ).model_dump(mode="json"),
        image_policy={
            "rights": rights.model_dump(mode="json"),
            "storage_reviewer": reviewer,
            "storage_reason": reason,
        },
    )
    session.add(asset)
    await session.flush()
    row = (await session.execute(query().where(MediaAsset.id == asset.id))).one()
    asset.image_policy = {
        **asset.image_policy,
        "binding": binding(row),
        "review_digest": digest(
            {"rights": rights.model_dump(mode="json"), "binding": binding(row)}
        ),
    }
    permitted(row, demo=rights.synthetic, publication=False)
    # Validated and reviewed assets only. A DB rollback may leave private orphan
    # blobs, never public URLs; garbage collection removes unreferenced files.
    for value in outputs.values():
        store(root, value)
    await session.flush()
    return asset


async def approve(
    session: AsyncSession, root: Path, identity: UUID, reviewer: str, reason: str
) -> None:
    actor(reviewer, reason)
    await writer_lock(session)
    row = (
        await session.execute(query().where(MediaAsset.id == identity))
    ).one_or_none()
    if row is None:
        raise MediaError("image_not_found")
    rights, metadata = permitted(row, demo=True, publication=False)
    for rendition in metadata.renditions.values():
        read_blob(root, rendition.sha256)
    asset = row[0]
    if metadata.role == "primary":
        link = row[1]
        target = (
            "fragrance_id"
            if link.fragrance_id
            else "release_id"
            if link.release_id
            else "variant_id"
        )
        previous = (
            await session.execute(
                query().where(
                    getattr(SourceEntityLink, target) == getattr(link, target),
                    MediaAsset.id != asset.id,
                    MediaAsset.usage_status == "approved",
                )
            )
        ).all()
        for old_row in previous:
            old = old_row[0]
            if old.media_metadata.get("role") != "primary":
                continue
            # This explicit operator action changes only selection priority.
            # Verify the previous proof before rebinding; never repair stale rights.
            try:
                old_rights, _ = permitted(old_row, demo=True)
            except MediaError:
                continue
            old.media_metadata = {**old.media_metadata, "role": "gallery"}
            old.image_policy = {
                **old.image_policy,
                "binding": binding(old_row),
                "review_digest": digest(
                    {
                        "rights": old_rights.model_dump(mode="json"),
                        "binding": binding(old_row),
                    }
                ),
                "primary_replaced_by": str(asset.id),
                "primary_replaced_by_reviewer": reviewer,
                "primary_replacement_reason": reason,
            }
    asset.image_policy = {
        **asset.image_policy,
        "publication_reviewer": reviewer,
        "publication_reason": reason,
        "publication_at": datetime.now(UTC).isoformat(),
    }
    asset.usage_status = "approved"
    await session.flush()


async def revoke(
    session: AsyncSession,
    identity: UUID,
    reviewer: str,
    reason: str,
    *,
    storage: bool = True,
) -> None:
    actor(reviewer, reason)
    await writer_lock(session)
    asset = await session.get(MediaAsset, identity)
    if asset is None:
        raise MediaError("image_not_found")
    asset.usage_status = "restricted"
    if storage:
        asset.storage_status = "restricted"
        asset.storage_path = None
        asset.media_metadata = {}
    asset.image_policy = {
        **asset.image_policy,
        "revoked_by": reviewer,
        "revocation_reason": reason,
        "revoked_at": datetime.now(UTC).isoformat(),
    }
    await session.flush()


async def revoke_source(
    session: AsyncSession, source_id: UUID, reviewer: str, reason: str
) -> int:
    actor(reviewer, reason)
    await writer_lock(session)
    assets = (
        await session.scalars(
            select(MediaAsset)
            .join(SourceEntityLink)
            .join(SourceRecord)
            .where(SourceRecord.source_id == source_id)
        )
    ).all()
    for asset in assets:
        await revoke(session, asset.id, reviewer, reason)
    return len(assets)


async def garbage_collect(session: AsyncSession, root: Path) -> int:
    """Private local operator only, serialized with image writers; no image fetch."""
    await writer_lock(session)
    now = datetime.now(UTC)
    stored = (
        await session.execute(
            query().where(MediaAsset.storage_status == "approved").limit(10001)
        )
    ).all()
    if len(stored) > 10000:
        raise MediaError("media_cleanup_requires_smaller_batch")
    for row in stored:
        asset, _, _, source, *_ = row
        try:
            rights = ImageRights.model_validate(asset.image_policy["rights"])
        except (ValueError, KeyError):
            raise MediaError("invalid_stored_image_policy") from None
        source_lost = (
            source.authorization_status not in {"approved", "synthetic"}
            or source.licensing_status not in {"approved", "synthetic"}
            or (
                source.source_type in FILE_TYPES and not reviewed_attribution(source)[0]
            )
        )
        if rights.expires_at <= now or (
            source_lost and not rights.retention_after_access_ends
        ):
            await revoke(
                session,
                asset.id,
                "media-retention-policy",
                "Expired image rights or source withdrawal; enforce reviewed retention terms",
            )
    retained: set[str] = set()
    for metadata in (
        await session.scalars(
            select(MediaAsset.media_metadata).where(
                MediaAsset.storage_status == "approved"
            )
        )
    ).all():
        try:
            retained.update(
                r.sha256 for r in Metadata.model_validate(metadata).renditions.values()
            )
        except ValueError:
            # Corrupt storage metadata must be investigated; never delete broadly.
            raise MediaError("invalid_stored_image_metadata") from None
    removed = 0
    for path in root.glob("*.webp"):
        if re.fullmatch(r"[a-f0-9]{64}", path.stem) and path.stem not in retained:
            path.unlink()
            removed += 1
    return removed


def public(row: Any, root: Path, demo: Access) -> ImagePublic:
    rights, metadata = permitted(row, demo=demo.demo)
    asset, _, _, source, *_ = row
    for rendition in metadata.renditions.values():
        try:
            info = location(root, rendition.sha256).lstat()
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_BYTES:
                raise MediaError("missing_image_blob")
        except OSError as exc:
            raise MediaError("missing_image_blob") from exc
    return ImagePublic(
        id=asset.id,
        url=f"/api/v1/media/{asset.id}/display",
        thumbnail_url=f"/api/v1/media/{asset.id}/thumb",
        width=metadata.renditions["display"].width,
        height=metadata.renditions["display"].height,
        thumbnail_width=metadata.renditions["thumb"].width,
        thumbnail_height=metadata.renditions["thumb"].height,
        alt=metadata.alt,
        role=metadata.role,
        source_id=source.key,
        source_url=rights.source_url,
        attribution=PublicAttribution(
            **rights.attribution.model_dump(),
            id="image-" + str(asset.id),
            fields=["image"],
        ),
        synthetic=rights.synthetic,
    )


async def attach_media(
    session: AsyncSession, records: list[Any], demo: Access, root: Path
) -> None:
    ids = [record.id for record in records]
    rows = (
        await session.execute(
            query()
            .where(Fragrance.id.in_(ids), MediaAsset.usage_status == "approved")
            .order_by(MediaAsset.id)
            .limit(1001)
        )
    ).all()
    if len(rows) > 1000:
        return  # Bounded, fail closed; operator must reduce oversized galleries.
    buckets: dict[tuple[str, UUID], list[tuple[int, ImagePublic]]] = {}
    variant_release: dict[UUID, UUID] = {}
    for row in rows:
        try:
            image = public(row, root, demo)
            link = row[1]
            target = (
                "fragrance"
                if link.fragrance_id
                else "release"
                if link.release_id
                else "variant"
            )
            identity = link.fragrance_id or link.release_id or link.variant_id
            buckets.setdefault((target, identity), []).append(
                (row[0].media_metadata["position"], image)
            )
            if target == "variant":
                variant_release[identity] = row[6].release_id
        except MediaError:
            continue

    def images(kind: str, identity: UUID) -> list[ImagePublic]:
        return [
            image
            for _, image in sorted(
                buckets.get((kind, identity), []),
                key=lambda pair: (pair[1].role != "primary", pair[0], str(pair[1].id)),
            )[:12]
        ]

    for record in records:
        record.images.extend(images("fragrance", record.id))
        object.__setattr__(
            record,
            "primary_image",
            next((i for i in record.images if i.role == "primary"), None),
        )
        for release in record.releases:
            release.images.extend(images("release", release.id))
            object.__setattr__(
                release,
                "primary_image",
                next((i for i in release.images if i.role == "primary"), None),
            )
            for identity, release_id in variant_release.items():
                if release_id == release.id:
                    gallery = images("variant", identity)
                    release.variant_images.append(
                        VariantImages(
                            variant_id=identity,
                            images=gallery,
                            primary_image=next(
                                (i for i in gallery if i.role == "primary"), None
                            ),
                        )
                    )
