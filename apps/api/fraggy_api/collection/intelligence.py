"""Explainable review heuristics. Scores are evidence points, never probabilities."""

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable
from difflib import SequenceMatcher
from typing import Any

from ..importing.formats import Record, concentration, key


def spelling(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(
        re.sub(
            r"[_\W]+", " ", "".join(c for c in value if not unicodedata.combining(c))
        ).split()
    )


def claim(value: Any) -> Any:
    if isinstance(value, list):
        return sorted(
            (item.position, key(item.name))
            if hasattr(item, "position")
            else ("", key(str(item)))
            for item in value
        )
    return key(str(value))


def match(left: Record, right: Record) -> dict[str, Any]:
    points = 0
    reasons: list[dict[str, Any]] = []
    guards: list[str] = []
    conflicts = []
    missing = []
    unusable = any(
        not spelling(value)
        for value in (
            left.brand_name,
            right.brand_name,
            left.fragrance_name,
            right.fragrance_name,
        )
    )

    def add(field: str, score: int, reason: str) -> None:
        nonlocal points
        points += score
        reasons.append({"field": field, "points": score, "reason": reason})

    a, b = spelling(left.brand_name), spelling(right.brand_name)
    if key(left.brand_name) == key(right.brand_name):
        add("brand_name", 30, "normalized_brand_labels_agree")
    elif a == b:
        add("brand_name", 25, "orthographic_brand_variant")
        guards.append("orthographic_brand_requires_review")
    elif a in {spelling(v) for v in right.brand_aliases} or b in {
        spelling(v) for v in left.brand_aliases
    }:
        add("brand_name", 20, "source_claimed_brand_alias_requires_review")
        guards.append("alias_identity_not_independently_verified")
    else:
        guards.append("different_brand")
    if (
        left.source_metadata.get("manufacturer")
        and spelling(left.source_metadata["manufacturer"]) == b
        and a != b
    ) or (
        right.source_metadata.get("manufacturer")
        and spelling(right.source_metadata["manufacturer"]) == a
        and a != b
    ):
        guards.append("manufacturer_is_not_brand")

    a, b = spelling(left.fragrance_name), spelling(right.fragrance_name)
    if key(left.fragrance_name) == key(right.fragrance_name):
        add("fragrance_name", 30, "name_labels_agree")
    elif a == b:
        add("fragrance_name", 25, "orthographic_variant")
        guards.append("orthographic_variant_requires_review")
    elif a == spelling(right.source_metadata.get("name_alias", "")) or b == spelling(
        left.source_metadata.get("name_alias", "")
    ):
        add("fragrance_name", 20, "source_claimed_name_alias")
        guards.append("alias_identity_not_independently_verified")
    elif SequenceMatcher(None, a, b, autojunk=False).ratio() >= 0.85 or set(
        a.split()
    ) & set(b.split()):
        add("fragrance_name", 10, "related_spelling_or_name_tokens")
        guards.append("related_name_may_be_flanker")
    else:
        guards.append("different_name")

    c, d = concentration(left.concentration), concentration(right.concentration)
    if c and d:
        if c == d:
            add("concentration", 20, "concentration_aliases_agree")
        else:
            guards.append("distinct_concentration")
    else:
        missing.append("concentration")
    if left.release_year is not None and right.release_year is not None:
        if left.release_year == right.release_year:
            add("release_year", 10, "explicit_years_agree")
        else:
            guards.append("release_year_requires_separate_release_review")
            conflicts.append("release_year")
    else:
        missing.append("release_year")
    if left.gtin and right.gtin:
        if left.gtin == right.gtin:
            add(
                "gtin",
                10,
                "product_identifier_agrees_but_does_not_override_release_guards",
            )
        else:
            conflicts.append("gtin")
    else:
        missing.append("gtin")
    version_a, version_b = key(left.version_label or ""), key(right.version_label or "")
    if version_a != version_b:
        guards.append("edition_or_reformulation_requires_review")
    strength_a, strength_b = (
        key(left.source_metadata.get("strength_label", "")),
        key(right.source_metadata.get("strength_label", "")),
    )
    if strength_a != strength_b:
        guards.append("strength_descriptor_differs_or_unknown")
    if left.source_metadata.get("related_fragrance") or right.source_metadata.get(
        "related_fragrance"
    ):
        guards.append("related_product_reference_requires_review")
    for field in ("perfumers", "notes", "accords", "family"):
        x, y = getattr(left, field), getattr(right, field)
        if x and y and claim(x) != claim(y):
            conflicts.append(field)
        if not x or not y:
            missing.append(field)
    variant = bool(
        (
            left.bottle_sizes_ml
            and right.bottle_sizes_ml
            and set(left.bottle_sizes_ml) != set(right.bottle_sizes_ml)
        )
        or (
            left.source_metadata.get("packaging")
            and right.source_metadata.get("packaging")
            and key(left.source_metadata["packaging"])
            != key(right.source_metadata["packaging"])
        )
        or (left.gtin and right.gtin and left.gtin != right.gtin)
    )
    cap = 100
    if guards:
        cap = 79
    if missing and (
        not c or not d or left.release_year is None or right.release_year is None
    ):
        cap = min(cap, 69)
    if any(
        g in guards
        for g in (
            "related_name_may_be_flanker",
            "edition_or_reformulation_requires_review",
            "release_year_requires_separate_release_review",
            "strength_descriptor_differs_or_unknown",
        )
    ):
        cap = min(cap, 49)
    if any(
        g in guards
        for g in (
            "different_brand",
            "different_name",
            "distinct_concentration",
            "manufacturer_is_not_brand",
        )
    ):
        cap = 20
    score = min(points, cap)
    if unusable:
        score = 0
        guards.append("unusable_identity_label")
    return {
        "score": score,
        "raw_points": points,
        "cap": cap,
        "meaning": "deterministic identity-evidence points; not factual accuracy, completeness or a calibrated probability",
        "reasons": reasons,
        "guards": sorted(set(guards)),
        "conflicting_fields": sorted(set(conflicts)),
        "missing_fields": sorted(set(missing)),
        "variant_review": variant,
        "status": "requires_correction"
        if unusable
        else "ready_for_human_review"
        if score >= 80 and not conflicts and not variant
        else "identity_or_conflict_review_required",
        "automatic_merge": False,
        "publication_authorized": False,
    }


def indexed_review(
    entries: Iterable[tuple[str, str, Record]],
    *,
    max_pairs: int = 1000,
    max_records: int = 50000,
    bucket_limit: int = 64,
) -> dict[str, Any]:
    if (
        not 1 <= max_pairs <= 100000
        or not 1 <= max_records <= 50000
        or not 1 <= bucket_limit <= 128
    ):
        raise ValueError("Invalid matching budget")
    exact: dict[tuple[str, str], list[int]] = defaultdict(list)
    tokens: dict[tuple[str, str], list[int]] = defaultdict(list)
    stored: list[tuple[str, str, Record]] = []
    seen_ids: set[str] = set()
    pairs: list[dict[str, Any]] = []
    complete = True
    overflow_buckets = 0
    alias_truncations = 0
    correction_required = []
    for identifier, stream, record in entries:
        if identifier in seen_ids or len(stored) >= max_records:
            raise ValueError("Duplicate identity or matching record budget exceeded")
        seen_ids.add(identifier)
        if len(record.brand_aliases) > 5:
            alias_truncations += 1
            complete = False
        if not spelling(record.brand_name) or not spelling(record.fragrance_name):
            correction_required.append(identifier)
        brands = {
            spelling(record.brand_name),
            *(spelling(v) for v in record.brand_aliases[:5]),
        }
        names = {spelling(record.fragrance_name)}
        if record.source_metadata.get("name_alias"):
            names.add(spelling(record.source_metadata["name_alias"]))
        brands.discard("")
        names.discard("")
        candidates: dict[int, None] = {}
        for brand in sorted(brands):
            for name in sorted(names):
                for index in exact.get((brand, name), []):
                    candidates[index] = None
            # Prefer the rarest available token after exact/explicit alias matches.
            options = [
                tokens[(brand, token)]
                for name in names
                for token in name.split()[:10]
                if (brand, token) in tokens
            ]
            if options:
                for index in min(options, key=len):
                    candidates[index] = None
        for index in candidates:
            other_id, other_stream, other = stored[index]
            if other_stream == stream:
                continue
            if len(pairs) >= max_pairs:
                complete = False
                break
            result = match(other, record)
            pairs.append(
                {
                    "left": other_id,
                    "right": identifier,
                    **result,
                    "field_provenance": {
                        field: {"left": other_id, "right": identifier}
                        for field in (
                            "brand_name",
                            "fragrance_name",
                            "concentration",
                            "release_year",
                            "perfumers",
                            "notes",
                            "accords",
                            "gtin",
                        )
                    },
                }
            )
        index = len(stored)
        stored.append((identifier, stream, record))
        for brand in brands:
            for name in names:
                for mapping, item in [
                    (exact, (brand, name)),
                    *((tokens, (brand, token)) for token in set(name.split()[:10])),
                ]:
                    if len(mapping[item]) < bucket_limit:
                        mapping[item].append(index)
                    else:
                        overflow_buckets += 1
                        complete = False
    degree = Counter(
        identifier for pair in pairs for identifier in (pair["left"], pair["right"])
    )
    for pair in pairs:
        if degree[pair["left"]] > 1 or degree[pair["right"]] > 1:
            pair["guards"] = sorted(
                set(pair["guards"]) | {"multiple_candidates_require_review"}
            )
            pair["cap"] = min(pair["cap"], 69)
            pair["score"] = min(pair["score"], 69)
            pair["status"] = "identity_or_conflict_review_required"
    return {
        "records": len(stored),
        "pairs": pairs,
        "pairs_evaluated": len(pairs),
        "complete_within_candidate_rules": complete,
        "bucket_overflows": overflow_buckets,
        "alias_truncations": alias_truncations,
        "records_requiring_correction": correction_required,
        "pair_limit": max_pairs,
        "candidate_rule": "normalized brand/claimed aliases plus exact names/claimed alias or rare shared token; not exhaustive entity resolution",
    }
