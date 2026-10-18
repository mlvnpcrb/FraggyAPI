"""Durable collection control, separate from ingestion/publication decisions."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .common import Identity


class CollectionSource(Identity, Base):
    __tablename__ = "collection_sources"
    __table_args__ = (
        Index(
            "ix_collection_due",
            "next_due_at",
            postgresql_where=text("enabled AND schedule_enabled"),
        ),
        CheckConstraint(
            "interval_seconds >= 60 AND interval_seconds <= 31536000",
            name="ck_collection_interval",
        ),
        CheckConstraint("state IN ('approved','revoked')", name="ck_collection_state"),
    )
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), unique=True
    )
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB)
    configuration_digest: Mapped[str] = mapped_column(Text)
    review: Mapped[dict[str, Any]] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(Text, default="approved")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    interval_seconds: Mapped[int] = mapped_column(Integer, default=86400)
    next_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    current_run_id: Mapped[UUID | None]
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionRun(Identity, Base):
    __tablename__ = "collection_runs"
    __table_args__ = (
        Index(
            "uq_collection_running",
            "collection_id",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
        CheckConstraint(
            "status IN ('running','succeeded','partial','failed','cancelled','interrupted')",
            name="ck_collection_run_status",
        ),
        CheckConstraint(
            "pages >= 0 AND records_seen >= 0 AND records_staged >= 0 AND records_unchanged >= 0 AND attempts >= 0",
            name="ck_collection_run_counts",
        ),
    )
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("collection_sources.id", ondelete="RESTRICT"), index=True
    )
    configuration_digest: Mapped[str] = mapped_column(Text)
    ingestion_run_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    response_digests: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(Text, default="running")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    pages: Mapped[int] = mapped_column(Integer, default=0)
    records_seen: Mapped[int] = mapped_column(Integer, default=0)
    records_staged: Mapped[int] = mapped_column(Integer, default=0)
    records_unchanged: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    quality: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    checkpoint: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
