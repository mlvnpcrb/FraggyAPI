"""Bounded offline reconciliation. No transport, canonical writes or rights grants."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from ..importing.formats import Record, Strict, concentration, digest, key
from ..quality.duplicates import classify_pair
from .intelligence import indexed_review
from .offline_sources import ADAPTERS, FixturePage
from .policy import CollectionError

MAX_RECORDS = 5000
MAX_PAGES = 100
MAX_PAIRS = 1000
MAX_STATE_BYTES = 8 * 1024 * 1024


class Observation(Strict):
    source: Literal["fragrantica", "parfumo", "official_brand", "wikidata"]
    dataset: str = Field(pattern=r"^[a-z0-9-]{1,60}$")
    collected_at: datetime
    source_url: str = Field(max_length=2048)
    mapping: str
    rights: Literal["fixture_only"] = "fixture_only"
    record: Record
    transformations: list[str] = Field(
        default_factory=lambda: [
            "nfkc_lowercase_comparison_keys",
            "concentration_alias_comparison",
        ],
        max_length=2,
    )

    @model_validator(mode="after")
    def fixture_provenance(self) -> "Observation":
        if (
            self.collected_at.tzinfo is None
            or self.mapping != ADAPTERS[self.source].version
            or not self.source_url.startswith("https://example.invalid/")
            or (
                self.record.source_url
                and not self.record.source_url.startswith("https://example.invalid/")
            )
        ):
            raise ValueError("Invalid offline provenance")
        return self


class Checkpoint(Strict):
    version: Literal[1] = 1
    synthetic: Literal[True] = True
    records: dict[str, Observation] = Field(
        default_factory=dict, max_length=MAX_RECORDS
    )
    next_pages: dict[str, int | None] = Field(default_factory=dict, max_length=100)

    @model_validator(mode="after")
    def validate_checkpoint(self) -> "Checkpoint":
        for identifier, observation in self.records.items():
            if identifier != identity(
                observation.source,
                observation.dataset,
                observation.record.source_record_id,
            ):
                raise ValueError("Checkpoint identity mismatch")
        for stream, cursor in self.next_pages.items():
            if (
                len(stream) != 64
                or any(c not in "0123456789abcdef" for c in stream)
                or (cursor is not None and not 1 <= cursor <= 10000)
            ):
                raise ValueError("Invalid checkpoint cursor")
        return self


def identity(source: str, dataset: str, record_id: str) -> str:
    return digest([source, dataset, record_id])


def completeness(record: Record) -> dict[str, Any]:
    fields = (
        "brand_name",
        "fragrance_name",
        "concentration",
        "release_year",
        "perfumers",
        "notes",
        "accords",
        "family",
        "bottle_sizes_ml",
        "gtin",
    )
    known = [field for field in fields if getattr(record, field) not in (None, [], "")]
    return {
        "score": len(known) * 100 // len(fields),
        "known": known,
        "unknown": [field for field in fields if field not in known],
        "meaning": "attribute completeness, not accuracy, rights or merge confidence",
    }


def compare(observations: list[Observation]) -> dict[str, Any]:
    blocks: dict[tuple[str, str], list[Observation]] = defaultdict(list)
    pairs: list[dict[str, Any]] = []
    complete = True
    for observation in observations:
        record = observation.record
        block = (key(record.brand_name), key(record.fragrance_name).split()[0])
        for previous in blocks[block]:
            if (
                previous.source == observation.source
                and previous.dataset == observation.dataset
            ):
                continue
            if len(pairs) >= MAX_PAIRS:
                complete = False
                break

            def row(value: Record) -> dict[str, Any]:
                return {
                    "brand": value.brand_name,
                    "name": value.fragrance_name,
                    "concentration": concentration(value.concentration),
                    "year": value.release_year,
                    "version": value.version_label,
                }

            classification = classify_pair(row(previous.record), row(record))
            conflicts = []
            # Concentration, launch year and version differences describe separate
            # release candidates, never attributes to overwrite on a shared row.
            if classification in {"possible_duplicate", "incomplete_identity"}:
                for field in ("perfumers", "notes", "accords", "family", "gtin"):
                    left, right = (
                        getattr(previous.record, field),
                        getattr(record, field),
                    )

                    def normalized(value: Any) -> Any:
                        if isinstance(value, list):
                            return sorted(
                                (item.position, key(item.name))
                                if hasattr(item, "position")
                                else ("", key(str(item)))
                                for item in value
                            )
                        return key(str(value))

                    if left and right and normalized(left) != normalized(right):
                        conflicts.append(field)
            pairs.append(
                {
                    "left": identity(
                        previous.source,
                        previous.dataset,
                        previous.record.source_record_id,
                    ),
                    "right": identity(
                        observation.source, observation.dataset, record.source_record_id
                    ),
                    "classification": classification,
                    "variant_review": bool(
                        (
                            previous.record.gtin
                            and record.gtin
                            and previous.record.gtin != record.gtin
                        )
                        or (
                            previous.record.bottle_sizes_ml
                            and record.bottle_sizes_ml
                            and set(previous.record.bottle_sizes_ml)
                            != set(record.bottle_sizes_ml)
                        )
                    ),
                    "conflicting_fields": conflicts,
                    "automatic_merge": False,
                    "review_required": True,
                }
            )
        blocks[block].append(observation)
    return {
        "pairs": pairs,
        "complete": complete,
        "pair_limit": MAX_PAIRS,
        "candidate_rule": "normalized brand and first name token; a bounded heuristic, not exhaustive matching",
    }


def rehearse(
    pages: Iterable[FixturePage], checkpoint: Checkpoint | None = None
) -> dict[str, Any]:
    state = (checkpoint or Checkpoint()).model_copy(deep=True)
    counts = {"new": 0, "changed": 0, "unchanged": 0, "pages": 0}
    changes = []
    batch_bytes = 0
    for page in pages:
        batch_bytes += len(page.model_dump_json().encode())
        if batch_bytes > MAX_STATE_BYTES:
            raise CollectionError("offline_batch_byte_limit")
        counts["pages"] += 1
        if counts["pages"] > MAX_PAGES:
            raise CollectionError("offline_page_limit")
        stream = digest([page.source, page.dataset])
        expected = state.next_pages.get(stream)
        if page.page != (0 if expected is None else expected):
            raise CollectionError("offline_checkpoint_mismatch")
        parsed = ADAPTERS[page.source].parse(page)
        ids = [record.source_record_id for record in parsed]
        if len(set(ids)) != len(ids):
            raise CollectionError("offline_duplicate_page_identity")
        for record in parsed:
            identifier = identity(page.source, page.dataset, record.source_record_id)
            previous = state.records.get(identifier)
            current_hash = digest(record.model_dump(mode="json"))
            previous_hash = (
                digest(previous.record.model_dump(mode="json")) if previous else None
            )
            status = (
                "new"
                if previous is None
                else "unchanged"
                if current_hash == previous_hash
                else "changed"
            )
            counts[status] += 1
            if status != "unchanged":
                changes.append(
                    {
                        "identity": identifier,
                        "status": status,
                        "before": previous_hash,
                        "after": current_hash,
                    }
                )
            if previous is None and len(state.records) >= MAX_RECORDS:
                raise CollectionError("offline_record_limit")
            source_url = (
                record.source_url
                or f"https://example.invalid/{page.source}/{identifier}"
            )
            if not source_url.startswith("https://example.invalid/"):
                raise CollectionError("offline_fixture_url_required")
            state.records[identifier] = Observation(
                source=page.source,
                dataset=page.dataset,
                collected_at=page.collected_at,
                source_url=source_url,
                mapping=ADAPTERS[page.source].version,
                record=record,
            )
        state.next_pages[stream] = page.next_page
        if len(state.next_pages) > 100:
            raise CollectionError("offline_stream_limit")
    if len(state.model_dump_json().encode()) > MAX_STATE_BYTES:
        raise CollectionError("offline_checkpoint_byte_limit")
    observations = list(state.records.values())
    return {
        "offline_only": True,
        "external_requests": 0,
        "database_writes": 0,
        "published": 0,
        "schedule_enabled": False,
        "counts": counts,
        "record_count": len(observations),
        "changes": changes,
        "comparison": compare(observations),
        "intelligence": indexed_review(
            (
                (identifier, digest([value.source, value.dataset]), value.record)
                for identifier, value in state.records.items()
            ),
            max_pairs=MAX_PAIRS,
        ),
        "quality": {
            identifier: completeness(value.record)
            for identifier, value in state.records.items()
        },
        "checkpoint": state.model_dump(mode="json"),
    }
