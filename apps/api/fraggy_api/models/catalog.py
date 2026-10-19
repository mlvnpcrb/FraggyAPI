from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Computed,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .common import (
    Identity,
    Named,
    Slugged,
    confidence_column,
    fk,
    name_check,
    slug_check,
    year_check,
)


class Brand(Identity, Named, Slugged, Base):
    __tablename__ = "brands"
    __table_args__ = (
        UniqueConstraint("name_key", name="uq_brands_name_key"),
        name_check("brands"),
        slug_check("brands"),
        CheckConstraint(
            "country IS NULL OR country ~ '^[A-Z]{2}$'", name="ck_brands_country"
        ),
    )
    country: Mapped[str | None] = mapped_column(String(2))
    description: Mapped[str | None] = mapped_column(Text)
    fragrances: Mapped[list["Fragrance"]] = relationship(
        back_populates="brand", passive_deletes="all"
    )
    aliases: Mapped[list["BrandAlias"]] = relationship(passive_deletes="all")


class BrandAlias(Identity, Named, Base):
    __tablename__ = "brand_aliases"
    __table_args__ = (
        UniqueConstraint("brand_id", "name_key", name="uq_brand_aliases_key"),
        name_check("brand_aliases"),
        Index("ix_brand_aliases_name_key", "name_key"),
    )
    brand_id: Mapped[UUID] = fk("brands")


class FragranceAlias(Identity, Named, Base):
    __tablename__ = "fragrance_aliases"
    __table_args__ = (
        UniqueConstraint("fragrance_id", "name_key", name="uq_fragrance_aliases_key"),
        name_check("fragrance_aliases"),
    )
    fragrance_id: Mapped[UUID] = fk("fragrances")


class FragranceFamily(Identity, Named, Slugged, Base):
    __tablename__ = "fragrance_families"
    __table_args__ = (
        UniqueConstraint("name_key", name="uq_families_name_key"),
        name_check("fragrance_families"),
        slug_check("fragrance_families"),
    )
    description: Mapped[str | None] = mapped_column(Text)


class Fragrance(Identity, Named, Slugged, Base):
    __tablename__ = "fragrances"
    __table_args__ = (
        name_check("fragrances"),
        slug_check("fragrances"),
        year_check("fragrances"),
        Index("ix_fragrances_name_key", "name_key"),
        Index("ix_fragrances_search", "search_vector", postgresql_using="gin"),
        Index("ix_fragrances_brand_name", "brand_id", "name_key"),
    )
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple'::regconfig, coalesce(name, ''))", persisted=True
        ),
    )
    brand_id: Mapped[UUID] = fk("brands")
    family_id: Mapped[UUID | None] = fk("fragrance_families", nullable=True)
    release_year: Mapped[int | None] = mapped_column(index=True)
    gender_positioning: Mapped[str | None] = mapped_column(String(80))
    brand: Mapped[Brand] = relationship(back_populates="fragrances")
    family: Mapped[FragranceFamily | None] = relationship()
    releases: Mapped[list["FragranceRelease"]] = relationship(
        back_populates="fragrance",
        passive_deletes="all",
        foreign_keys="FragranceRelease.fragrance_id",
    )


class FragranceRelease(Identity, Base):
    __tablename__ = "fragrance_releases"
    __table_args__ = (
        year_check("fragrance_releases"),
        CheckConstraint(
            "concentration IS NULL OR concentration IN ('parfum','extrait_de_parfum','eau_de_parfum','eau_de_toilette','eau_de_cologne','eau_fraiche','oil','other')",
            name="ck_releases_concentration",
        ),
        UniqueConstraint("id", "fragrance_id", name="uq_releases_id_fragrance"),
        ForeignKeyConstraint(
            ["reformulation_of_id", "fragrance_id"],
            ["fragrance_releases.id", "fragrance_releases.fragrance_id"],
            ondelete="RESTRICT",
            name="fk_release_reformulation_identity",
        ),
        CheckConstraint(
            "reformulation_of_id IS NULL OR reformulation_of_id <> id",
            name="ck_releases_not_self",
        ),
    )
    fragrance_id: Mapped[UUID] = fk("fragrances")
    concentration: Mapped[str | None] = mapped_column(String(40), index=True)
    original_concentration: Mapped[str | None] = mapped_column(Text)
    release_year: Mapped[int | None] = mapped_column(index=True)
    version_label: Mapped[str | None] = mapped_column(Text)
    reformulation_of_id: Mapped[UUID | None] = mapped_column(index=True)
    version_metadata: Mapped[str | None] = mapped_column(Text)
    fragrance: Mapped[Fragrance] = relationship(
        back_populates="releases", foreign_keys=[fragrance_id]
    )
    variants: Mapped[list["FragranceVariant"]] = relationship(
        back_populates="release", passive_deletes="all"
    )
    notes: Mapped[list["ReleaseNote"]] = relationship(
        back_populates="release", passive_deletes="all"
    )
    accords: Mapped[list["ReleaseAccord"]] = relationship(passive_deletes="all")
    perfumers: Mapped[list["ReleasePerfumer"]] = relationship(passive_deletes="all")


class FragranceVariant(Identity, Base):
    __tablename__ = "fragrance_variants"
    __table_args__ = (
        CheckConstraint(
            "bottle_size_ml IS NULL OR bottle_size_ml > 0", name="ck_variants_size"
        ),
        CheckConstraint(
            "original_size IS NULL OR original_size > 0",
            name="ck_variants_original_size",
        ),
        CheckConstraint(
            "original_size IS NULL OR (original_unit IS NOT NULL AND length(btrim(original_unit)) > 0)",
            name="ck_variants_original_unit",
        ),
        CheckConstraint(
            "gtin IS NULL OR gtin ~ '^([0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$'",
            name="ck_variants_gtin",
        ),
    )
    release_id: Mapped[UUID] = fk("fragrance_releases")
    bottle_size_ml: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    original_size: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    original_unit: Mapped[str | None] = mapped_column(String(24))
    gtin: Mapped[str | None] = mapped_column(String(14), index=True)
    packaging_label: Mapped[str | None] = mapped_column(Text)
    release: Mapped[FragranceRelease] = relationship(back_populates="variants")


class Note(Identity, Named, Slugged, Base):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint("name_key", name="uq_notes_name_key"),
        name_check("notes"),
        slug_check("notes"),
    )
    aliases: Mapped[list["NoteAlias"]] = relationship(passive_deletes="all")


class NoteAlias(Identity, Named, Base):
    __tablename__ = "note_aliases"
    __table_args__ = (
        UniqueConstraint("note_id", "name_key", name="uq_note_aliases_key"),
        name_check("note_aliases"),
        Index("ix_note_aliases_name_key", "name_key"),
    )
    note_id: Mapped[UUID] = fk("notes")


class ReleaseNote(Identity, Base):
    __tablename__ = "release_notes"
    __table_args__ = (
        UniqueConstraint(
            "release_id", "note_id", "position", name="uq_release_notes_position"
        ),
        CheckConstraint(
            "position IN ('top','heart','base','unknown')",
            name="ck_release_notes_position",
        ),
        CheckConstraint(
            "display_order IS NULL OR display_order >= 0", name="ck_release_notes_order"
        ),
    )
    release_id: Mapped[UUID] = fk("fragrance_releases")
    note_id: Mapped[UUID] = fk("notes")
    position: Mapped[str] = mapped_column(
        String(16), default="unknown", server_default="unknown"
    )
    display_order: Mapped[int | None]
    release: Mapped[FragranceRelease] = relationship(back_populates="notes")
    note: Mapped[Note] = relationship()


class Accord(Identity, Named, Slugged, Base):
    __tablename__ = "accords"
    __table_args__ = (
        UniqueConstraint("name_key", name="uq_accords_name_key"),
        name_check("accords"),
        slug_check("accords"),
    )


class ReleaseAccord(Identity, Base):
    __tablename__ = "release_accords"
    __table_args__ = (
        UniqueConstraint("release_id", "accord_id", name="uq_release_accords"),
        CheckConstraint(
            "strength IS NULL OR strength BETWEEN 0 AND 1",
            name="ck_release_accords_strength",
        ),
        CheckConstraint(
            "display_order IS NULL OR display_order >= 0",
            name="ck_release_accords_order",
        ),
    )
    release_id: Mapped[UUID] = fk("fragrance_releases")
    accord_id: Mapped[UUID] = fk("accords")
    strength: Mapped[Decimal | None] = confidence_column()
    display_order: Mapped[int | None]
    accord: Mapped[Accord] = relationship()


class Perfumer(Identity, Named, Slugged, Base):
    __tablename__ = "perfumers"
    __table_args__ = (
        name_check("perfumers"),
        slug_check("perfumers"),
        Index("ix_perfumers_name_key", "name_key"),
    )
    # Names are not unique: different people can have identical names.


class ReleasePerfumer(Identity, Base):
    __tablename__ = "release_perfumers"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "perfumer_id",
            "credited_role",
            name="uq_release_perfumers_role",
            postgresql_nulls_not_distinct=True,
        ),
    )
    release_id: Mapped[UUID] = fk("fragrance_releases")
    perfumer_id: Mapped[UUID] = fk("perfumers")
    credited_role: Mapped[str | None] = mapped_column(String(80))
    perfumer: Mapped[Perfumer] = relationship()


# Same immutable normalized key as comparisons; avoid expression/schema drift.
for _search_model in (Fragrance, Brand, BrandAlias, FragranceAlias):
    Index(
        f"ix_{_search_model.__tablename__}_trigram",
        _search_model.name_key,
        postgresql_using="gin",
        postgresql_ops={"name_key": "gin_trgm_ops"},
    )
