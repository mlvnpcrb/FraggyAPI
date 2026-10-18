"""Bounded source-specific field mapping over REST, feeds and structured HTML."""

import csv
import io
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from ..importing.formats import MAX_BYTES, Record, bounded, loads
from .policy import CollectionError, Endpoint


@dataclass(frozen=True)
class Page:
    records: list[Record]
    next_cursor: str | None = None
    watermark: str | None = None


class EmbeddedJSON(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.active = False
        self.parts: list[str] = []
        self.matches = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if (
            tag == "script"
            and attributes.get("id") == "fragrance-data"
            and attributes.get("type") == "application/json"
        ):
            self.active = True
            self.matches += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)


def token(value: Any) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 256
        or any(ord(c) < 33 or ord(c) > 126 for c in value)
    ):
        raise CollectionError("invalid_checkpoint_token")
    return value


def extract(
    body: bytes, endpoint: Endpoint, content_type: str, cursor: str | None = None
) -> Page:
    if endpoint.adapter == "wikidata_sparql":
        from .wikidata import records as wikidata_records

        if content_type.split(";", 1)[0].strip().lower() not in {
            "application/sparql-results+json",
            "application/json",
        }:
            raise CollectionError("unexpected_content_type")
        wikidata_rows, next_cursor = wikidata_records(body, endpoint, cursor)
        return Page(wikidata_rows, next_cursor)
    try:
        if len(body) > MAX_BYTES:
            raise CollectionError("response_too_large")
        text = body.decode("utf-8-sig")
        expected = {
            "rest_json": "application/json",
            "json_feed": "application/json",
            "csv_feed": "text/csv",
            "html_json": "text/html",
        }[endpoint.adapter]
        if content_type.split(";", 1)[0].strip().lower() != expected:
            raise CollectionError("unexpected_content_type")
        cursor = watermark = None
        if endpoint.adapter == "csv_feed":
            reader = csv.DictReader(io.StringIO(text), strict=True)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(
                reader.fieldnames
            ):
                raise CollectionError("invalid_csv_headers")
            rows: Any = []
            for raw in reader:
                if (
                    None in raw
                    or any(v is None for v in raw.values())
                    or len(rows) >= endpoint.max_records
                ):
                    raise CollectionError("invalid_csv_shape")
                rows.append({k: v for k, v in raw.items() if v != ""})
        else:
            if endpoint.adapter == "html_json":
                parser = EmbeddedJSON()
                parser.feed(text)
                if parser.matches != 1 or parser.active:
                    raise CollectionError("invalid_html_payload")
                text = "".join(parser.parts)
            document = loads(text)
            if isinstance(document, dict):
                if set(document) - {"records", "next_cursor", "watermark"}:
                    raise CollectionError("unexpected_page_fields")
                rows = document.get("records")
                cursor = token(document.get("next_cursor"))
                watermark = token(document.get("watermark"))
            else:
                rows = document
        bounded(rows)
        if not isinstance(rows, list) or len(rows) > endpoint.max_records:
            raise CollectionError("invalid_page_rows")
        records = []
        for row in rows:
            if not isinstance(row, dict):
                raise CollectionError("invalid_record")
            mapped = (
                {
                    dest: row.get(origin)
                    for dest, origin in endpoint.field_map.items()
                    if origin in row
                }
                if endpoint.field_map
                else dict(row)
            )
            if endpoint.adapter == "csv_feed":
                for name in (
                    "notes",
                    "accords",
                    "perfumers",
                    "bottle_sizes_ml",
                    "brand_aliases",
                ):
                    if name in mapped:
                        value = mapped[name]
                        if not isinstance(value, str):
                            raise CollectionError("invalid_csv_value")
                        mapped[name] = loads(value)
            records.append(Record.model_validate(mapped))
        identities = [r.source_record_id for r in records]
        if len(set(identities)) != len(identities):
            raise CollectionError("duplicate_page_identity")
        return Page(records, cursor, watermark)
    except (ValueError, TypeError, csv.Error, RecursionError) as exc:
        raise CollectionError("malformed_page") from exc
