"""Shared persistent identity and constraints; no extension is required."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

NAME_KEY_SQL = (
    "lower(btrim(regexp_replace(normalize(name, NFKC), '[[:space:]]+', ' ', 'g')))"
)
RIGHTS_SQL = "('pending_review', 'approved', 'restricted', 'synthetic')"


class Identity:
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Named:
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_key: Mapped[str] = mapped_column(Text, Computed(NAME_KEY_SQL, persisted=True))


class Slugged:
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)


def fk(table: str, *, nullable: bool = False, index: bool = True) -> Any:
    return mapped_column(
        ForeignKey(f"{table}.id", ondelete="RESTRICT"), nullable=nullable, index=index
    )


def name_check(table: str) -> CheckConstraint:
    return CheckConstraint(
        "length(btrim(name)) > 0 AND length(name_key) > 0", name=f"ck_{table}_name"
    )


def slug_check(table: str) -> CheckConstraint:
    return CheckConstraint("slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'", name=f"ck_{table}_slug")


def year_check(table: str, column: str = "release_year") -> CheckConstraint:
    return CheckConstraint(
        f"{column} IS NULL OR {column} BETWEEN 1000 AND 2999", name=f"ck_{table}_year"
    )


def confidence_column() -> Any:
    return mapped_column(Numeric(5, 4), nullable=True)


Confidence = Decimal | None
