"""Wikidata CC0 metadata mapping. No discovery, image fetching or rights approval."""

import re
from typing import Any

from ..importing.formats import MAX_BYTES, Record, loads
from .policy import CollectionError, Endpoint

ENTITY = re.compile(r"Q[1-9][0-9]{0,15}\Z")
URI = re.compile(r"https?://www\.wikidata\.org/entity/(Q[1-9][0-9]{0,15})\Z")
PAGE_SIZE = 25


def page_ids(endpoint: Endpoint, cursor: str | None) -> tuple[list[str], str | None]:
    offset = 0 if cursor is None else int(cursor) if cursor.isdecimal() else -1
    if offset < 0 or offset % PAGE_SIZE or offset >= len(endpoint.entity_ids):
        raise CollectionError("invalid_wikidata_checkpoint")
    end = offset + PAGE_SIZE
    return endpoint.entity_ids[offset:end], str(end) if end < len(
        endpoint.entity_ids
    ) else None


def query(endpoint: Endpoint, cursor: str | None) -> str:
    ids, _ = page_ids(endpoint, cursor)
    # IDs are operator-reviewed, bounded Q identifiers; no downloaded query text.
    values = " ".join("wd:" + identity for identity in ids)
    return (
        "PREFIX wd: <http://www.wikidata.org/entity/> "
        "PREFIX wdt: <http://www.wikidata.org/prop/direct/> "
        "PREFIX wikibase: <http://wikiba.se/ontology#> "
        "PREFIX bd: <http://www.bigdata.com/rdf#> "
        "SELECT ?item ?itemLabel ?brand ?brandLabel WHERE { VALUES ?item { "
        + values
        + ' } ?item wdt:P1716 ?brand . SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } } ORDER BY ?item ?brand'
    )


def entity(binding: Any) -> str:
    if not isinstance(binding, dict) or binding.get("type") != "uri":
        raise CollectionError("invalid_wikidata_entity")
    match = URI.fullmatch(str(binding.get("value", "")))
    if not match:
        raise CollectionError("invalid_wikidata_entity")
    return match[1]


def label(binding: Any) -> str:
    if (
        not isinstance(binding, dict)
        or binding.get("type") != "literal"
        or binding.get("xml:lang") != "en"
        or not isinstance(binding.get("value"), str)
        or ENTITY.fullmatch(binding["value"])
    ):
        raise CollectionError("wikidata_english_label_required")
    return str(binding["value"])


def records(
    body: bytes, endpoint: Endpoint, cursor: str | None
) -> tuple[list[Record], str | None]:
    if len(body) > MAX_BYTES:
        raise CollectionError("response_too_large")
    ids, next_cursor = page_ids(endpoint, cursor)
    try:
        document = loads(body.decode("utf-8"))
        rows = document["results"]["bindings"]
        if (
            not isinstance(rows, list)
            or len(rows) > PAGE_SIZE
            or len(rows) > endpoint.max_records
        ):
            raise CollectionError("wikidata_ambiguous_or_oversized_page")
        result: list[Record] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {
                "item",
                "itemLabel",
                "brand",
                "brandLabel",
            }:
                raise CollectionError("invalid_wikidata_binding")
            identity, brand = entity(row["item"]), entity(row["brand"])
            if identity not in ids or identity in seen:
                raise CollectionError("wikidata_unrequested_or_ambiguous_entity")
            seen.add(identity)
            result.append(
                Record(
                    source_metadata={
                        "item": identity,
                        "brand": brand,
                        "brand_property": "P1716",
                        "mapping_version": "wikidata_sparql_v1",
                    },
                    source_record_id=identity,
                    source_url="https://www.wikidata.org/wiki/" + identity,
                    fragrance_name=label(row["itemLabel"]),
                    brand_name=label(row["brandLabel"]),
                )
            )
        # Don't checkpoint past omitted IDs: missing brands or qualifiers must
        # be resolved in the reviewed pilot list instead of silently losing items.
        if seen != set(ids):
            raise CollectionError("wikidata_incomplete_page")
        return result, next_cursor
    except CollectionError:
        raise
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError) as exc:
        raise CollectionError("malformed_wikidata_page") from exc
