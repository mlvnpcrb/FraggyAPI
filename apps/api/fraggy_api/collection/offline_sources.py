"""Independent synthetic contracts, NOT reverse-engineered live website parsers."""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from ..importing.formats import MAX_BYTES, Record, Strict, bounded
from .adapters import extract
from .policy import CollectionError, Endpoint
from .wikidata import entity
from .wikidata import records as wikidata_records


class FixturePage(Strict):
    synthetic: Literal[True]
    source: Literal["fragrantica", "parfumo", "official_brand", "wikidata"]
    dataset: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    collected_at: datetime
    page: int = Field(default=0, ge=0, le=10000)
    next_page: int | None = Field(default=None, ge=1, le=10000)
    payload: dict[str, Any]

    @model_validator(mode="after")
    def validate_page(self) -> "FixturePage":
        if self.collected_at.tzinfo is None:
            raise ValueError("Timezone required")
        if self.next_page is not None and self.next_page != self.page + 1:
            raise ValueError("Sequential fixture pages required")
        bounded(self.payload)
        if len(self.model_dump_json().encode()) > MAX_BYTES:
            raise ValueError("Fixture page exceeds byte limit")
        return self


class OfflineSource(ABC):
    source: str
    version = "synthetic_contract_v1"

    def collect(self) -> None:
        raise CollectionError("offline_source_live_collection_disabled")

    @abstractmethod
    def parse(self, page: FixturePage) -> list[Record]: ...

    def check(self, page: FixturePage) -> None:
        if page.source != self.source:
            raise CollectionError("offline_source_mismatch")


def rows(page: FixturePage, key: str) -> list[dict[str, Any]]:
    if set(page.payload) != {key}:
        raise CollectionError("unsupported_fixture_payload")
    values = page.payload[key]
    if (
        not isinstance(values, list)
        or not 1 <= len(values) <= 50
        or not all(isinstance(value, dict) for value in values)
    ):
        raise CollectionError("invalid_fixture_rows")
    return values


def note_names(value: Any) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > 40
        or not all(isinstance(name, str) for name in value)
    ):
        raise CollectionError("invalid_fixture_notes")
    return value


class FragranticaFixture(OfflineSource):
    source = "fragrantica"

    def parse(self, page: FixturePage) -> list[Record]:
        self.check(page)
        result = []
        mapping = {
            "id": "source_record_id",
            "title": "fragrance_name",
            "house": "brand_name",
            "strength": "concentration",
            "launched": "release_year",
            "nose": "perfumers",
            "accords": "accords",
            "version": "version_label",
            "sizes": "bottle_sizes_ml",
            "family": "family",
            "collection": "collection",
            "gtin": "gtin",
        }
        for row in rows(page, "perfumes"):
            extras = {"gender_positioning", "longevity", "sillage"}
            if set(row) - (set(mapping) | {"top", "heart", "base"} | extras):
                raise CollectionError("unsupported_fixture_field")
            values = {dest: row[key] for key, dest in mapping.items() if key in row}
            values["source_metadata"] = {
                field: row[field] for field in extras if field in row
            }
            values["notes"] = [
                {"name": name, "position": position}
                for position in ("top", "heart", "base")
                for name in note_names(row.get(position, []))
            ]
            result.append(Record.model_validate(values))
        return result


class ParfumoFixture(OfflineSource):
    source = "parfumo"

    def parse(self, page: FixturePage) -> list[Record]:
        self.check(page)
        mapping = {
            "key": "source_record_id",
            "name": "fragrance_name",
            "brand": "brand_name",
            "concentration": "concentration",
            "year": "release_year",
            "perfumers": "perfumers",
            "accords": "accords",
            "edition": "version_label",
            "family": "family",
        }
        result = []
        for row in rows(page, "entries"):
            if set(row) - (set(mapping) | {"notes"}):
                raise CollectionError("unsupported_fixture_field")
            values = {dest: row[key] for key, dest in mapping.items() if key in row}
            values["notes"] = [
                {"name": name, "position": "unknown"}
                for name in note_names(row.get("notes", []))
            ]
            result.append(Record.model_validate(values))
        return result


class OfficialBrandFixture(OfflineSource):
    source = "official_brand"

    def parse(self, page: FixturePage) -> list[Record]:
        self.check(page)
        products = rows(page, "products")
        endpoint = Endpoint(
            url="http://127.0.0.1:1",
            adapter="json_feed",
            minimum_interval_seconds=1,
            max_records=50,
        )
        return extract(
            json.dumps({"records": products}).encode(), endpoint, "application/json"
        ).records


class WikidataFixture(OfflineSource):
    source = "wikidata"
    version = "wikidata_sparql_v1_fixture"

    def parse(self, page: FixturePage) -> list[Record]:
        self.check(page)
        bindings = page.payload.get("results", {}).get("bindings")
        if not isinstance(bindings, list) or not 1 <= len(bindings) <= 25:
            raise CollectionError("invalid_wikidata_fixture_rows")
        ids = [entity(row.get("item")) for row in bindings]
        endpoint = Endpoint(
            url="http://127.0.0.1:1",
            adapter="wikidata_sparql",
            minimum_interval_seconds=1,
            entity_ids=ids,
            max_records=25,
            max_pages=1,
            user_agent="FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; fixture@example.invalid)",
        )
        parsed = wikidata_records(json.dumps(page.payload).encode(), endpoint, None)[0]
        # Invented entity IDs must not become clickable references to real hosts.
        return [
            record.model_copy(
                update={
                    "source_url": "https://example.invalid/wikidata/"
                    + record.source_record_id
                }
            )
            for record in parsed
        ]


ADAPTERS: dict[str, OfflineSource] = {
    adapter.source: adapter
    for adapter in (
        FragranticaFixture(),
        ParfumoFixture(),
        OfficialBrandFixture(),
        WikidataFixture(),
    )
}
