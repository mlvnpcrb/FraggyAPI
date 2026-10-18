from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .common import RIGHTS_SQL, Identity, confidence_column, fk


def rights_check(table: str, column: str) -> CheckConstraint:
    return CheckConstraint(f"{column} IN {RIGHTS_SQL}", name=f"ck_{table}_{column}")


def json_array() -> Any:
    return mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))


class DataSource(Identity, Base):
    __tablename__ = "data_sources"
    __table_args__ = (
        rights_check("sources", "authorization_status"),
        rights_check("sources", "licensing_status"),
        CheckConstraint(
            "NOT enabled OR (authorization_status = 'approved' AND licensing_status = 'approved' AND reviewed_at IS NOT NULL AND jsonb_array_length(evidence) > 0 AND jsonb_array_length(allowed_collection_methods) > 0 AND jsonb_array_length(permitted_fields) > 0)",
            name="ck_sources_enable_requires_review",
        ),
        CheckConstraint(
            "jsonb_typeof(allowed_collection_methods) = 'array' AND jsonb_typeof(permitted_fields) = 'array' AND jsonb_typeof(evidence) = 'array' AND jsonb_typeof(reuse_restrictions) = 'array' AND jsonb_typeof(error_history) = 'array'",
            name="ck_sources_policy_arrays",
        ),
        CheckConstraint(
            "jsonb_typeof(rate_limit) = 'object'", name="ck_sources_rate_limit"
        ),
    )
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(Text)
    website: Mapped[str] = mapped_column(Text)
    adapter_identifier: Mapped[str | None] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(40))
    authorization_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    licensing_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false")
    )
    allowed_collection_methods: Mapped[list[str]] = json_array()
    permitted_fields: Mapped[list[str]] = json_array()
    reuse_restrictions: Mapped[list[str]] = json_array()
    evidence: Mapped[list[dict[str, Any]]] = json_array()
    error_history: Mapped[list[dict[str, Any]]] = json_array()
    rate_limit: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_successful_sync: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    adapter_status: Mapped[str] = mapped_column(
        String(32), default="skeleton", server_default="skeleton"
    )
    records: Mapped[list["SourceRecord"]] = relationship(
        back_populates="source", passive_deletes="all"
    )


class IngestionRun(Identity, Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        UniqueConstraint("id", "source_id", name="uq_runs_id_source"),
        CheckConstraint(
            "status IN ('queued','running','succeeded','failed','cancelled','synthetic')",
            name="ck_runs_status",
        ),
        CheckConstraint(
            "records_seen >= 0 AND records_accepted >= 0 AND records_accepted <= records_seen",
            name="ck_runs_counts",
        ),
        CheckConstraint(
            "completed_at IS NULL OR (started_at IS NOT NULL AND completed_at >= started_at)",
            name="ck_runs_times",
        ),
    )
    source_id: Mapped[UUID] = fk("data_sources")
    status: Mapped[str] = mapped_column(
        String(24), default="queued", server_default="queued", index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_seen: Mapped[int] = mapped_column(default=0, server_default="0")
    records_accepted: Mapped[int] = mapped_column(default=0, server_default="0")
    sanitized_errors: Mapped[list[dict[str, Any]]] = json_array()


class SourceRecord(Identity, Base):
    __tablename__ = "source_records"
    __table_args__ = (
        Index("ix_records_source_collected", "source_id", "collected_at"),
        UniqueConstraint(
            "source_id",
            "source_record_id",
            "revision",
            name="uq_records_source_revision",
        ),
        ForeignKeyConstraint(
            ["ingestion_run_id", "source_id"],
            ["ingestion_runs.id", "ingestion_runs.source_id"],
            ondelete="RESTRICT",
            name="fk_records_run_source",
        ),
        CheckConstraint(
            "length(btrim(source_record_id)) > 0 AND schema_version > 0 AND revision > 0",
            name="ck_records_identity_version",
        ),
        rights_check("records", "storage_status"),
        rights_check("records", "redistribution_status"),
        CheckConstraint(
            "redistribution_status <> 'approved' OR (redistribution_evidence IS NOT NULL AND length(btrim(redistribution_evidence)) > 0)",
            name="ck_records_redistribution_evidence",
        ),
        CheckConstraint(
            "payload IS NULL OR (storage_status IN ('approved','synthetic') AND jsonb_typeof(payload) = 'object')",
            name="ck_records_payload_rights",
        ),
        CheckConstraint(
            "storage_status <> 'approved' OR length(btrim(storage_evidence)) > 0 AND storage_evidence IS NOT NULL",
            name="ck_records_storage_evidence",
        ),
        CheckConstraint(
            "processing_state IN ('pending_review','validated','rejected','linked')",
            name="ck_records_processing_state",
        ),
    )
    source_id: Mapped[UUID] = fk("data_sources")
    ingestion_run_id: Mapped[UUID | None] = mapped_column(index=True)
    source_record_id: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    revision: Mapped[int] = mapped_column(default=1, server_default="1")
    schema_version: Mapped[int] = mapped_column(default=1, server_default="1")
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    storage_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    redistribution_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    storage_evidence: Mapped[str | None] = mapped_column(Text)
    redistribution_evidence: Mapped[str | None] = mapped_column(Text)
    processing_state: Mapped[str] = mapped_column(
        String(24),
        default="pending_review",
        server_default="pending_review",
        index=True,
    )
    source: Mapped[DataSource] = relationship(
        back_populates="records", foreign_keys=[source_id]
    )
    links: Mapped[list["SourceEntityLink"]] = relationship(
        back_populates="record", passive_deletes="all"
    )


class SourceEntityLink(Identity, Base):
    __tablename__ = "source_entity_links"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(brand_id,fragrance_id,release_id,variant_id,note_id,accord_id,perfumer_id,family_id) = 1",
            name="ck_links_one_target",
        ),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_links_confidence",
        ),
        CheckConstraint(
            "review_status IN ('pending_review','approved','rejected')",
            name="ck_links_review_status",
        ),
        *(
            Index(
                f"uq_links_record_{column}",
                "source_record_id",
                column,
                unique=True,
                postgresql_where=text(f"{column} IS NOT NULL"),
            )
            for column in (
                "brand_id",
                "fragrance_id",
                "release_id",
                "variant_id",
                "note_id",
                "accord_id",
                "perfumer_id",
                "family_id",
            )
        ),
    )
    source_record_id: Mapped[UUID] = fk("source_records")
    brand_id: Mapped[UUID | None] = fk("brands", nullable=True)
    fragrance_id: Mapped[UUID | None] = fk("fragrances", nullable=True)
    release_id: Mapped[UUID | None] = fk("fragrance_releases", nullable=True)
    variant_id: Mapped[UUID | None] = fk("fragrance_variants", nullable=True)
    note_id: Mapped[UUID | None] = fk("notes", nullable=True)
    accord_id: Mapped[UUID | None] = fk("accords", nullable=True)
    perfumer_id: Mapped[UUID | None] = fk("perfumers", nullable=True)
    family_id: Mapped[UUID | None] = fk("fragrance_families", nullable=True)
    confidence: Mapped[Decimal | None] = confidence_column()
    review_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    record: Mapped[SourceRecord] = relationship(back_populates="links")
    claims: Mapped[list["FieldProvenance"]] = relationship(passive_deletes="all")


class FieldProvenance(Identity, Base):
    __tablename__ = "field_provenance"
    __table_args__ = (
        rights_check("provenance", "usage_rights_status"),
        CheckConstraint(
            "confidence IS NULL OR confidence BETWEEN 0 AND 1",
            name="ck_provenance_confidence",
        ),
        CheckConstraint(
            "value_state IN ('known','unknown','conflicting') AND selection_status IN ('candidate','selected','rejected')",
            name="ck_provenance_states",
        ),
        CheckConstraint(
            "(value_state = 'unknown' AND value IS NULL) OR (value_state <> 'unknown' AND value IS NOT NULL)",
            name="ck_provenance_value",
        ),
        CheckConstraint(
            "length(btrim(field_path)) > 0 AND jsonb_typeof(transformations) = 'array'",
            name="ck_provenance_shape",
        ),
        CheckConstraint(
            "usage_rights_status <> 'approved' OR (rights_evidence IS NOT NULL AND length(btrim(rights_evidence)) > 0)",
            name="ck_provenance_rights_evidence",
        ),
        Index("ix_provenance_link_field", "entity_link_id", "field_path"),
    )
    entity_link_id: Mapped[UUID] = fk("source_entity_links")
    field_path: Mapped[str] = mapped_column(Text)
    value: Mapped[Any | None] = mapped_column(JSONB(none_as_null=True))
    value_state: Mapped[str] = mapped_column(String(24))
    selection_status: Mapped[str] = mapped_column(
        String(24), default="candidate", server_default="candidate"
    )
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    transformations: Mapped[list[dict[str, Any]]] = json_array()
    usage_rights_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    rights_evidence: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[Decimal | None] = confidence_column()


class DataReviewQueue(Identity, Base):
    __tablename__ = "data_review_queue"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','resolved','dismissed')", name="ck_review_status"
        ),
        CheckConstraint(
            "status = 'pending' OR (resolved_at IS NOT NULL AND reviewer IS NOT NULL AND length(btrim(resolution)) > 0 AND resolution IS NOT NULL)",
            name="ck_review_resolution",
        ),
    )
    source_record_id: Mapped[UUID] = fk("source_records")
    field_provenance_id: Mapped[UUID | None] = fk("field_provenance", nullable=True)
    release_id: Mapped[UUID | None] = fk("fragrance_releases", nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(24), default="pending", server_default="pending", index=True
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    reviewer: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MediaAsset(Identity, Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        rights_check("media", "usage_status"),
        rights_check("media", "storage_status"),
        CheckConstraint(
            "content_sha256 IS NULL OR content_sha256 ~ '^[a-f0-9]{64}$'",
            name="ck_media_content_hash",
        ),
        CheckConstraint(
            "jsonb_typeof(media_metadata) = 'object' AND jsonb_typeof(image_policy) = 'object'",
            name="ck_media_policy_objects",
        ),
        Index(
            "uq_media_link_content_active",
            "entity_link_id",
            "content_sha256",
            unique=True,
            postgresql_where=text(
                "content_sha256 IS NOT NULL AND storage_status = 'approved'"
            ),
        ),
        CheckConstraint(
            "storage_path IS NULL OR (storage_status = 'approved' AND rights_evidence IS NOT NULL AND length(btrim(rights_evidence)) > 0)",
            name="ck_media_storage_rights",
        ),
        CheckConstraint(
            "usage_status <> 'approved' OR (rights_evidence IS NOT NULL AND length(btrim(rights_evidence)) > 0)",
            name="ck_media_usage_evidence",
        ),
    )
    entity_link_id: Mapped[UUID] = fk("source_entity_links")
    source_url: Mapped[str] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    license_identifier: Mapped[str | None] = mapped_column(Text)
    license_url: Mapped[str | None] = mapped_column(Text)
    rights_evidence: Mapped[str | None] = mapped_column(Text)
    usage_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    storage_status: Mapped[str] = mapped_column(
        String(24), default="pending_review", server_default="pending_review"
    )
    storage_path: Mapped[str | None] = mapped_column(Text)

    content_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    media_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
    image_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )
