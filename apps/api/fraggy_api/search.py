"""Indexed local search only. No imports, providers, intents or transport calls."""

import re
from typing import Any

from sqlalchemy import case, false, func, or_, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from .importing.formats import key
from .models import Brand, BrandAlias, Fragrance, FragranceAlias
from .public_catalog import grant
from .public_rights import Access

STRENGTHS = {
    "edp": "eau_de_parfum",
    "edt": "eau_de_toilette",
    "edc": "eau_de_cologne",
    "parfum": "parfum",
    "extrait": "extrait_de_parfum",
}


def terms(query: str) -> tuple[list[str], str | None]:
    normalized = key(query)
    if len(normalized) > 120 or any(ord(char) < 32 for char in normalized):
        raise ValueError("Normalized query exceeds limit")
    for phrase, alias in (
        ("extrait de parfum", "extrait"),
        ("eau de parfum", "edp"),
        ("eau de toilette", "edt"),
        ("eau de cologne", "edc"),
    ):
        normalized = re.sub(r"\b" + phrase + r"\b", alias, normalized)
    words = re.findall(r"[^\W_]+", normalized)
    strengths = {STRENGTHS[word] for word in words if word in STRENGTHS}
    # Conflicting descriptors remain literal terms; do not invent a concentration.
    strength = next(iter(strengths)) if len(strengths) == 1 else None
    tokens = [word for word in words if not strength or word not in STRENGTHS]
    if len(tokens) > 16:
        raise ValueError("Search supports at most sixteen terms")
    return list(dict.fromkeys(tokens)), strength


def fuzzy(column: Any, word: str) -> Any:
    # Terms contain no SQL wildcards. Very short terms use literal exact matching.
    if word.isdigit() or len(word) < 4:
        return column.op("~")(
            r"(^|[^[:alnum:]])" + re.escape(word) + r"([^[:alnum:]]|$)"
        )
    return (
        or_(
            column.contains(word, autoescape=True),
            (column.op("%>")(word) & func.fraggy_typo_match(word, column)),
        )
        if len(word) >= 4
        else column == word
    )


async def candidates(
    session: AsyncSession, query: str, access: Access
) -> tuple[Any, list[Any]]:
    tokens, strength = terms(query)
    await session.execute(
        select(func.set_config("pg_trgm.word_similarity_threshold", "0.2", True))
    )
    f, b = Fragrance, Brand
    scope: Any = None
    for number, word in enumerate(
        sorted(tokens, key=lambda word: (not word.isdigit(), -len(word), word))
    ):
        direct = select(f.id).where(fuzzy(f.name_key, word))
        brands = select(f.id).where(
            f.brand_id.in_(select(b.id).where(fuzzy(b.name_key, word)))
        )
        aliases = select(FragranceAlias.fragrance_id).where(
            fuzzy(FragranceAlias.name_key, word),
            grant(
                "fragrance_id",
                FragranceAlias.fragrance_id,
                "aliases",
                FragranceAlias.name,
                access,
                contains=True,
            ),
        )
        brand_aliases = select(f.id).where(
            f.brand_id.in_(
                select(BrandAlias.brand_id).where(
                    fuzzy(BrandAlias.name_key, word),
                    grant(
                        "brand_id",
                        BrandAlias.brand_id,
                        "aliases",
                        BrandAlias.name,
                        access,
                        contains=True,
                    ),
                )
            )
        )
        if scope is not None:
            prior = select(scope.c.id)
            direct = direct.where(f.id.in_(prior))
            brands = brands.where(f.id.in_(prior))
            aliases = aliases.where(FragranceAlias.fragrance_id.in_(prior))
            brand_aliases = brand_aliases.where(f.id.in_(prior))
        scope = (
            direct.union(brands, aliases, brand_aliases)
            .cte(f"search_term_{number}")
            .prefix_with("MATERIALIZED")
        )
    if scope is None:
        ids = select(f.id).where(false() if not strength else true())
    else:
        ids = select(scope.c.id)
    exact = or_(
        f.name_key == key(query),
        b.name_key == key(query),
        func.concat(b.name_key, " ", f.name_key) == key(query),
    )
    relevance = [case((exact, 1), else_=0).desc()]
    if tokens:
        score: Any = 0
        for word in tokens:
            score = score + func.greatest(
                func.word_similarity(word, f.name_key),
                func.word_similarity(word, b.name_key),
            )
        relevance.append(score.desc())
    return f.id.in_(ids), relevance
