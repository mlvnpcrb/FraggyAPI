"""Bounded read-only PostgreSQL catalog queries and allowlisted responses."""

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from .database import get_session
from .models import (
    Accord,
    Brand,
    Fragrance,
    FragranceRelease,
    Note,
    ReleaseAccord,
    ReleaseNote,
)
from .public_catalog import (
    FragrancePublic,
    Item,
    NamedPublic,
    Page,
    Pagination,
    ReleasePublic,
    grant,
    visible,
)


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorDetail


router = APIRouter(
    prefix="/api/v1",
    tags=["public catalog"],
    responses={
        400: {"model": ErrorEnvelope, "description": "Invalid search request"},
        404: {"model": ErrorEnvelope, "description": "Public resource not found"},
        422: {"model": ErrorEnvelope, "description": "Invalid query or identifier"},
        500: {"model": ErrorEnvelope, "description": "Sanitized server error"},
    },
)
Session = Annotated[AsyncSession, Depends(get_session)]
Concentration = Literal[
    "parfum",
    "extrait_de_parfum",
    "eau_de_parfum",
    "eau_de_toilette",
    "eau_de_cologne",
    "eau_fraiche",
    "oil",
    "other",
]


class CatalogQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str = Field(default="", max_length=120)
    brand: str | None = Field(
        default=None, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=160
    )
    concentration: Concentration | None = None
    year: int | None = Field(default=None, ge=1000, le=2999)
    notes: list[UUID] = Field(default_factory=list, max_length=10)
    accords: list[UUID] = Field(default_factory=list, max_length=10)
    sort: Literal["relevance", "name", "name_desc"] = "relevance"

    @field_validator("q")
    @classmethod
    def clean_query(cls, value: str) -> str:
        return " ".join(value.split())


class LookupQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=10000)
    q: str = Field(default="", max_length=120)


def demo_enabled(request: Request) -> bool:
    config = request.app.state.settings
    return bool(config.catalog_include_synthetic and config.app_env != "production")


def named(model: Any, synthetic: bool) -> NamedPublic:
    return NamedPublic(
        id=model.id, name=model.name, slug=model.slug, synthetic=synthetic
    )


def synthetic_flag(model: Any, target: str, demo: bool) -> ColumnElement[bool]:
    flags = [
        grant(target, model.id, field, getattr(model, field), demo, synthetic_only=True)
        for field in ("name", "slug")
    ]
    if target == "fragrance_id":
        flags.append(
            grant(
                target, model.id, "brand_id", model.brand_id, demo, synthetic_only=True
            )
        )
    return or_(*flags)


def release_visible(demo: bool) -> ColumnElement[bool]:
    return grant(
        "release_id",
        FragranceRelease.id,
        "fragrance_id",
        FragranceRelease.fragrance_id,
        demo,
    )


def fragrance_visible(demo: bool) -> ColumnElement[bool]:
    return and_(
        visible(Fragrance, "fragrance_id", demo),
        visible(Brand, "brand_id", demo),
        grant("fragrance_id", Fragrance.id, "brand_id", Fragrance.brand_id, demo),
    )


async def project(
    session: AsyncSession, rows: Any, demo: bool
) -> list[FragrancePublic]:
    """Five fixed queries per page, independent of the number of fragrances.

    Each fragrance has at most 20 releases; each release has at most 50 notes and
    accords. Window bounds apply in SQL, including to unexpectedly large catalogs.
    """
    if not rows:
        return []
    ids = [row[0].id for row in rows]
    release = FragranceRelease
    ranked = (
        select(
            release.id,
            func.row_number()
            .over(partition_by=release.fragrance_id, order_by=release.id)
            .label("rn"),
            func.count().over(partition_by=release.fragrance_id).label("total"),
        )
        .where(release.fragrance_id.in_(ids), release_visible(demo))
        .subquery()
    )
    release_rows = (
        await session.execute(
            select(
                release,
                ranked.c.total,
                grant(
                    "release_id",
                    release.id,
                    "concentration",
                    release.concentration,
                    demo,
                ),
                grant(
                    "release_id", release.id, "release_year", release.release_year, demo
                ),
                or_(
                    *(
                        grant(
                            "release_id",
                            release.id,
                            field,
                            getattr(release, field),
                            demo,
                            synthetic_only=True,
                        )
                        for field in ("fragrance_id", "concentration", "release_year")
                    )
                ),
            )
            .join(ranked, release.id == ranked.c.id)
            .where(ranked.c.rn <= 20)
            .order_by(release.id)
        )
    ).all()
    release_ids = [row[0].id for row in release_rows]
    associations: dict[str, dict[UUID, list[NamedPublic]]] = {
        "notes": {},
        "accords": {},
    }
    association_specs: list[tuple[str, Any, Any, str, str]] = [
        ("notes", ReleaseNote, Note, "note_id", "note_id"),
        ("accords", ReleaseAccord, Accord, "accord_id", "accord_id"),
    ]
    for field, association, model, key, target in association_specs:
        allowed = (
            select(
                association.release_id.label("release_id"),
                model.id.label("entity_id"),
                func.row_number()
                .over(partition_by=association.release_id, order_by=model.id)
                .label("rn"),
            )
            .join(model, getattr(association, key) == model.id)
            .where(
                association.release_id.in_(release_ids),
                visible(model, target, demo),
                grant(
                    "release_id",
                    association.release_id,
                    field,
                    model.id,
                    demo,
                    contains=True,
                ),
            )
            .distinct()
            .subquery()
        )
        items = (
            await session.execute(
                select(
                    allowed.c.release_id,
                    model,
                    or_(
                        synthetic_flag(model, target, demo),
                        grant(
                            "release_id",
                            allowed.c.release_id,
                            field,
                            model.id,
                            demo,
                            contains=True,
                            synthetic_only=True,
                        ),
                    ),
                )
                .join(model, model.id == allowed.c.entity_id)
                .where(allowed.c.rn <= 50)
            )
        ).all()
        for release_id, entity, synthetic in items:
            bucket = associations[field].setdefault(release_id, [])
            if all(item.id != entity.id for item in bucket):
                bucket.append(named(entity, synthetic))
    by_fragrance: dict[UUID, list[ReleasePublic]] = {}
    truncated: set[UUID] = set()
    for entity, total, concentration_ok, year_ok, synthetic in release_rows:
        if total > 20:
            truncated.add(entity.fragrance_id)
        by_fragrance.setdefault(entity.fragrance_id, []).append(
            ReleasePublic(
                id=entity.id,
                concentration=entity.concentration if concentration_ok else None,
                release_year=entity.release_year if year_ok else None,
                notes=associations["notes"].get(entity.id, []),
                accords=associations["accords"].get(entity.id, []),
                synthetic=synthetic
                or any(
                    item.synthetic
                    for field in ("notes", "accords")
                    for item in associations[field].get(entity.id, [])
                ),
            )
        )
    return [
        FragrancePublic(
            **named(
                fragrance,
                synthetic
                or brand_synthetic
                or any(
                    release.synthetic for release in by_fragrance.get(fragrance.id, [])
                ),
            ).model_dump(),
            brand=named(brand, brand_synthetic),
            releases=by_fragrance.get(fragrance.id, []),
            releases_truncated=fragrance.id in truncated,
        )
        for fragrance, brand, synthetic, brand_synthetic in rows
    ]


async def catalog(
    session: AsyncSession, params: CatalogQuery, demo: bool
) -> Page[FragrancePublic]:
    f, b, r = Fragrance, Brand, FragranceRelease
    conditions = [fragrance_visible(demo)]
    if params.brand:
        conditions.append(b.slug == params.brand)
    if params.concentration or params.year or params.notes or params.accords:
        release_conditions = [r.fragrance_id == f.id, release_visible(demo)]
        for field, value in [
            ("concentration", params.concentration),
            ("release_year", params.year),
        ]:
            if value is not None:
                release_conditions.extend(
                    [
                        getattr(r, field) == value,
                        grant("release_id", r.id, field, getattr(r, field), demo),
                    ]
                )
        filter_specs: list[tuple[str, list[UUID], Any, Any, str, str]] = [
            ("notes", params.notes, ReleaseNote, Note, "note_id", "note_id"),
            (
                "accords",
                params.accords,
                ReleaseAccord,
                Accord,
                "accord_id",
                "accord_id",
            ),
        ]
        for field, values, association, model, key, target in filter_specs:
            for identity in values:
                release_conditions.append(
                    select(1)
                    .select_from(association)
                    .join(model, model.id == getattr(association, key))
                    .where(
                        association.release_id == r.id,
                        model.id == identity,
                        visible(model, target, demo),
                        grant("release_id", r.id, field, model.id, demo, contains=True),
                    )
                    .exists()
                )
        conditions.append(select(1).select_from(r).where(*release_conditions).exists())
    order: list[Any] = []
    if params.q:
        query = func.plainto_tsquery("simple", params.q)
        exact = or_(
            func.lower(f.name) == params.q.lower(),
            func.lower(b.name) == params.q.lower(),
        )
        # Escape wildcard characters: user text is never a LIKE pattern or SQL.
        escaped = params.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(
            or_(
                f.search_vector.op("@@")(query),
                b.name.ilike(f"%{escaped}%", escape="\\"),
                exact,
            )
        )
        if params.sort == "relevance":
            order.extend(
                [
                    case((exact, 1), else_=0).desc(),
                    func.ts_rank_cd(f.search_vector, query).desc(),
                ]
            )
    order.extend(
        [f.name_key.desc() if params.sort == "name_desc" else f.name_key, f.id]
    )
    base = (
        select(
            f,
            b,
            synthetic_flag(f, "fragrance_id", demo),
            synthetic_flag(b, "brand_id", demo),
        )
        .join(b)
        .where(*conditions)
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = (
        await session.execute(
            base.order_by(*order).limit(params.limit).offset(params.offset)
        )
    ).all()
    return Page(
        data=await project(session, rows, demo),
        pagination=Pagination(
            limit=params.limit, offset=params.offset, total=total or 0
        ),
    )


@router.get("/fragrances", response_model=Page[FragrancePublic])
async def fragrances(
    request: Request, session: Session, params: Annotated[CatalogQuery, Query()]
) -> Page[FragrancePublic]:
    return await catalog(session, params, demo_enabled(request))


# Register before the UUID route so 'search' is never parsed as a UUID.
@router.get("/fragrances/search", response_model=Page[FragrancePublic])
async def search(
    request: Request, session: Session, params: Annotated[CatalogQuery, Query()]
) -> Page[FragrancePublic]:
    if not params.q:
        raise HTTPException(400, "Search requires a nonblank q")
    return await catalog(session, params, demo_enabled(request))


@router.get("/fragrances/{id}", response_model=Item[FragrancePublic])
async def fragrance(
    id: UUID, request: Request, session: Session
) -> Item[FragrancePublic]:
    demo = demo_enabled(request)
    rows = (
        await session.execute(
            select(
                Fragrance,
                Brand,
                synthetic_flag(Fragrance, "fragrance_id", demo),
                synthetic_flag(Brand, "brand_id", demo),
            )
            .join(Brand)
            .where(Fragrance.id == id, fragrance_visible(demo))
        )
    ).all()
    data = await project(session, rows, demo)
    if not data:
        raise HTTPException(404, "Fragrance not found")
    return Item(data=data[0])


async def lookup(
    model: Any, target: str, params: LookupQuery, session: AsyncSession, demo: bool
) -> Page[NamedPublic]:
    base = select(model, synthetic_flag(model, target, demo)).where(
        visible(model, target, demo)
    )
    if params.q.strip():
        escaped = (
            params.q.strip()
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        base = base.where(model.name.ilike(f"%{escaped}%", escape="\\"))
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = (
        await session.execute(
            base.order_by(model.name_key, model.id)
            .limit(params.limit)
            .offset(params.offset)
        )
    ).all()
    return Page(
        data=[named(entity, synthetic) for entity, synthetic in rows],
        pagination=Pagination(
            limit=params.limit, offset=params.offset, total=total or 0
        ),
    )


@router.get("/brands", response_model=Page[NamedPublic])
async def brands(
    request: Request, session: Session, params: Annotated[LookupQuery, Query()]
) -> Page[NamedPublic]:
    return await lookup(Brand, "brand_id", params, session, demo_enabled(request))


@router.get("/brands/{slug}", response_model=Item[NamedPublic])
async def brand(slug: str, request: Request, session: Session) -> Item[NamedPublic]:
    demo = demo_enabled(request)
    row = (
        await session.execute(
            select(Brand, synthetic_flag(Brand, "brand_id", demo)).where(
                Brand.slug == slug, visible(Brand, "brand_id", demo)
            )
        )
    ).first()
    if not row:
        raise HTTPException(404, "Brand not found")
    return Item(data=named(row[0], row[1]))


@router.get("/notes", response_model=Page[NamedPublic])
async def notes(
    request: Request, session: Session, params: Annotated[LookupQuery, Query()]
) -> Page[NamedPublic]:
    return await lookup(Note, "note_id", params, session, demo_enabled(request))


@router.get("/accords", response_model=Page[NamedPublic])
async def accords(
    request: Request, session: Session, params: Annotated[LookupQuery, Query()]
) -> Page[NamedPublic]:
    return await lookup(Accord, "accord_id", params, session, demo_enabled(request))
