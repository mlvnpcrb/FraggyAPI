"""Bounded, non-executable UTF-8 file formats. No remote reads or file writes."""

import csv
import hashlib
import io
import json
import unicodedata
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from ..attribution import Attribution

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
Name = Annotated[str, StringConstraints(min_length=1, max_length=200)]


class ImportErrorSafe(ValueError):
    """Safe diagnostic contains locations/categories only, never imported values."""


def key(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).lower().split())


def concentration(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    token = key(value).replace("_", " ").replace("î", "i")
    synonyms = {
        "edt": "eau_de_toilette",
        "edp": "eau_de_parfum",
        "edc": "eau_de_cologne",
        "extrait": "extrait_de_parfum",
        "perfume": "parfum",
    }
    normalized = synonyms.get(token, token.replace(" ", "_"))
    if normalized not in {
        "parfum",
        "extrait_de_parfum",
        "eau_de_parfum",
        "eau_de_toilette",
        "eau_de_cologne",
        "eau_fraiche",
        "oil",
        "other",
    }:
        raise ValueError("Unsupported concentration")
    return normalized


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoteInput(Strict):
    name: Name
    aliases: list[Name] = Field(default_factory=list, max_length=20)
    position: Literal["top", "heart", "base", "unknown"] = "unknown"


class Record(Strict):
    # Source-specific references stay in the private snapshot, never canonical
    # columns or public DTOs; require explicit source manifest storage permission.
    source_metadata: dict[Name, Name] = Field(
        default_factory=dict, max_length=10, exclude_if=lambda v: not v
    )
    source_record_id: Annotated[str, StringConstraints(min_length=1, max_length=160)]
    source_url: str | None = Field(default=None, max_length=2048)
    brand_name: Name
    brand_aliases: list[Name] = Field(default_factory=list, max_length=20)
    fragrance_name: Name
    family: Name | None = None
    collection: Name | None = None
    concentration: str | None = Field(default=None, max_length=80)
    release_year: int | None = Field(default=None, ge=1000, le=2999)
    version_label: Name | None = None
    perfumers: list[Name] = Field(default_factory=list, max_length=10)
    notes: list[NoteInput] = Field(default_factory=list, max_length=40)
    accords: list[Name] = Field(default_factory=list, max_length=20)
    bottle_sizes_ml: list[
        Annotated[float, Field(gt=0, le=999999, allow_inf_nan=False)]
    ] = Field(default_factory=list, max_length=20)
    gtin: str | None = Field(
        default=None, pattern=r"^(?:[0-9]{8}|[0-9]{12}|[0-9]{13}|[0-9]{14})$"
    )

    @field_validator("source_url")
    @classmethod
    def safe_url(cls, value: str | None) -> str | None:
        if value:
            parsed = urlsplit(value)
            if (
                parsed.scheme not in {"https", "http"}
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Invalid source URL")
        return value

    @model_validator(mode="after")
    def valid_record(self) -> "Record":
        # Do not assign the same GTIN to several sizes; preserve unknowns.
        if self.gtin and len(self.bottle_sizes_ml) > 1:
            raise ValueError("GTIN requires at most one bottle size")
        if any(round(size, 3) != size for size in self.bottle_sizes_ml):
            raise ValueError("Bottle sizes support at most three decimals")
        if self.gtin:
            weighted = sum(
                int(d) * (3 if i % 2 == 0 else 1)
                for i, d in enumerate(reversed(self.gtin[:-1]))
            )
            if (10 - weighted % 10) % 10 != int(self.gtin[-1]):
                raise ValueError("Invalid GTIN check digit")
        concentration(self.concentration)
        for value in [
            self.brand_name,
            self.fragrance_name,
            self.source_record_id,
            *(n.name for n in self.notes),
            *self.accords,
            *self.perfumers,
            *self.brand_aliases,
            *(alias for note in self.notes for alias in note.aliases),
            *(
                v
                for v in (self.family, self.collection, self.version_label)
                if v is not None
            ),
        ]:
            if not key(value):
                raise ValueError("Blank identity")
        return self


class Manifest(Strict):
    source_id: Annotated[
        str, StringConstraints(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    ]
    synthetic: bool = False
    source_name: Name
    dataset_origin: Annotated[str, StringConstraints(min_length=1, max_length=500)]
    provider: Name
    authorization_status: Literal[
        "pending_review", "approved", "restricted", "synthetic"
    ] = "pending_review"
    storage_permissions: bool = False
    redistribution_permissions: bool = False
    permitted_fields: list[Name] = Field(default_factory=list, max_length=40)
    attribution_requirements: list[Name] = Field(default_factory=list, max_length=20)
    license_evidence_references: list[Name] = Field(min_length=1, max_length=20)
    attribution: Attribution | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    redistribution_conditions: list[Name] = Field(
        default_factory=list, max_length=20, exclude_if=lambda v: not v
    )
    review_date: str | None = Field(default=None, max_length=40)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def bounded(value: Any, depth: int = 0) -> None:
    if depth > 6:
        raise ImportErrorSafe("Maximum nesting exceeded")
    if isinstance(value, str):
        if len(value) > 4096 or any(ord(c) < 32 and c not in "\t\n\r" for c in value):
            raise ImportErrorSafe("Invalid or oversized text field")
    elif isinstance(value, dict):
        if len(value) > 50:
            raise ImportErrorSafe("Too many object fields")
        for k, item in value.items():
            bounded(k, depth + 1)
            bounded(item, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_ROWS:
            raise ImportErrorSafe("Row or array limit exceeded")
        for item in value:
            bounded(item, depth + 1)


def read_text(path: Path) -> str:
    try:
        # Bound actual read as well as stat: no symlink/racing-size bypass.
        if not path.is_file():
            raise ImportErrorSafe("A regular local file is required")
        with path.open("rb") as handle:
            data = handle.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ImportErrorSafe("File exceeds 2 MiB")
        return data.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ImportErrorSafe("Unable to read UTF-8 file") from exc


def loads(text: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in items:
            if name in result:
                raise ImportErrorSafe("Duplicate JSON key")
            result[name] = value
        return result

    try:
        return json.loads(
            text,
            object_pairs_hook=pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ImportErrorSafe("Non-finite JSON number")
            ),
        )
    except (ValueError, RecursionError) as exc:
        raise ImportErrorSafe("Malformed JSON") from exc


def manifest_file(path: Path) -> Manifest:
    try:
        data = loads(read_text(path))
        bounded(data)
        return Manifest.model_validate(data)
    except ValueError as exc:
        raise ImportErrorSafe("Invalid source manifest") from exc


def parse_file(path: Path) -> list[Record]:
    try:
        text = read_text(path)
        suffix = path.suffix.lower()
        if suffix == ".json":
            rows = loads(text)
        elif suffix == ".jsonl":
            rows = []
            for line in text.splitlines():
                if line.strip():
                    if len(rows) >= MAX_ROWS:
                        raise ImportErrorSafe("Row limit exceeded")
                    rows.append(loads(line))
        elif suffix == ".csv":
            reader = csv.DictReader(io.StringIO(text), strict=True)
            if not reader.fieldnames or len(reader.fieldnames) != len(
                set(reader.fieldnames)
            ):
                raise ImportErrorSafe("Missing or duplicate CSV headers")
            rows = []
            for raw in reader:
                if (
                    len(rows) >= MAX_ROWS
                    or None in raw
                    or any(v is None for v in raw.values())
                ):
                    raise ImportErrorSafe("CSV shape or row limit invalid")
                row: dict[str, Any] = {}
                for name, value in raw.items():
                    if value == "":
                        continue
                    row[name] = (
                        loads(value)
                        if name
                        in {
                            "brand_aliases",
                            "perfumers",
                            "notes",
                            "accords",
                            "bottle_sizes_ml",
                        }
                        else value
                    )
                rows.append(row)
        else:
            raise ImportErrorSafe("Supported formats: CSV, JSON, JSONL")
        bounded(rows)
        if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
            raise ImportErrorSafe("Expected 1–1000 records")
        records = []
        seen: set[str] = set()
        for number, row in enumerate(rows, 1):
            try:
                record = Record.model_validate(row)
            except ValueError as exc:
                raise ImportErrorSafe(f"Invalid record at row {number}") from exc
            if record.source_record_id in seen:
                raise ImportErrorSafe(f"Duplicate source identity at row {number}")
            seen.add(record.source_record_id)
            records.append(record)
        return records
    except (ValueError, csv.Error, RecursionError) as exc:
        if isinstance(exc, ImportErrorSafe):
            raise
        raise ImportErrorSafe("Malformed import file") from exc
