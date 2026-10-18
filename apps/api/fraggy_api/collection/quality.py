"""Pre-staging diagnostics reuse Phase 2E identity rules; never merge or fill data."""

from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any

from ..importing.formats import Record, concentration, key
from ..quality.duplicates import classify_pair


def assess(records: list[Record]) -> dict[str, Any]:
    blocks: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    result: dict[str, Any] = {
        "records": len(records),
        "missing_notes": sum(not r.notes for r in records),
        "unknown_years": sum(r.release_year is None for r in records),
        "implausible_years": sum(
            r.release_year is not None
            and not 1700 <= r.release_year <= datetime.now(UTC).year + 2
            for r in records
        ),
        "candidate_pairs_examined": 0,
        "complete": True,
    }
    labels: Counter[str] = Counter()
    for record in records:
        identity = (key(record.brand_name), key(record.fragrance_name).split()[0])
        row = {
            "brand": record.brand_name,
            "name": record.fragrance_name,
            "concentration": concentration(record.concentration),
            "year": record.release_year,
            "version": record.version_label,
        }
        for previous in blocks[identity]:
            if result["candidate_pairs_examined"] >= 1000:
                result["complete"] = False
                break
            labels[classify_pair(previous, row)] += 1
            result["candidate_pairs_examined"] += 1
        blocks[identity].append(row)
    result["pair_classifications"] = dict(labels)
    return result


def combine(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    result = {
        name: previous.get(name, 0) + current[name]
        for name in (
            "records",
            "missing_notes",
            "unknown_years",
            "implausible_years",
            "candidate_pairs_examined",
        )
    }
    labels = Counter(previous.get("pair_classifications", {}))
    labels.update(current["pair_classifications"])
    result["pair_classifications"] = dict(labels)
    result["complete"] = previous.get("complete", True) and current["complete"]
    return result
