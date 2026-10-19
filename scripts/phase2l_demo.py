"""Original-only matching/diagnostic demo and indexed CPU/memory benchmark."""

import argparse
import json
import time
import tracemalloc
from datetime import UTC, datetime
from typing import Any

from fraggy_api.collection.diagnostics import explain, inspect_response
from fraggy_api.collection.intelligence import indexed_review, match
from fraggy_api.collection.policy import Endpoint
from fraggy_api.collection.priority import Budget, Task, plan
from fraggy_api.collection.transport import Response
from fraggy_api.importing.formats import Record, digest


def fictional(**extra: Any) -> Record:
    return Record.model_validate(
        {
            "source_record_id": "original-demo",
            "brand_name": "Invented Atelier",
            "fragrance_name": "Lumiere Archive",
            "concentration": "EDP",
            "release_year": 2020,
            **extra,
        }
    )


def demo() -> dict[str, Any]:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    endpoint = Endpoint(
        url="http://127.0.0.1:1", adapter="json_feed", minimum_interval_seconds=1
    )
    tasks = [
        Task(
            id="low", source="fictional", fingerprint=digest("same-request"), due_at=now
        ),
        Task(
            id="high",
            source="fictional",
            fingerprint=digest("same-request"),
            due_at=now,
            priority=9,
        ),
    ]
    return {
        "offline_only": True,
        "external_requests": 0,
        "published": 0,
        "matches": {
            name: match(fictional(), fictional(**values))
            for name, values in {
                "exact_alias_concentration": {"concentration": "eau_de_parfum"},
                "orthographic_name": {"fragrance_name": "Lumière-Archive"},
                "flanker": {"fragrance_name": "Lumiere Archive Intense"},
                "different_concentration": {"concentration": "EDT"},
                "reformulation": {
                    "release_year": 2022,
                    "version_label": "Fictional reformulation",
                },
                "elixir_descriptor": {
                    "concentration": None,
                    "source_metadata": {"strength_label": "Elixir"},
                },
            }.items()
        },
        "diagnostics": {
            "access": inspect_response(
                Response(403, b"never expose upstream content", "text/html"), endpoint
            ),
            "missing_fields": inspect_response(
                Response(
                    200,
                    b'{"records":[{"source_record_id":"original"}]}',
                    "application/json",
                ),
                endpoint,
            ),
            "wrong_format": inspect_response(
                Response(200, b"<html>original changed layout</html>", "text/html"),
                endpoint,
            ),
            "timeout": explain("network_timeout"),
            "rate_limit": explain("retry_exhausted", 429),
        },
        "priority_plan": plan(
            tasks, {"fictional": Budget(remaining=2, next_request_at=now)}, now
        ),
    }


def benchmark(size: int, *, hotspot: bool = False) -> dict[str, Any]:
    if size not in {10000, 50000}:
        raise ValueError("Benchmark sizes are 10000 or 50000 original observations")

    def entries():
        for side in range(2):
            for number in range(size // 2):
                yield (
                    f"{side}-{number}",
                    f"fictional-feed-{side}",
                    fictional(
                        source_record_id=f"original-{number}",
                        brand_name=f"Invented House {number % 100}"
                        if not hotspot
                        else "Invented Hotspot",
                        fragrance_name=(
                            "Fable" if side == 0 or number % 10 else "Fâble"
                        )
                        + f" {number:06d}"
                        if not hotspot
                        else "Original Shared Name",
                    ),
                )

    tracemalloc.start()
    started = time.perf_counter()
    result = indexed_review(entries(), max_pairs=10000 if hotspot else 100000)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    positives = sum(
        pair["left"].split("-", 1)[1] == pair["right"].split("-", 1)[1]
        for pair in result["pairs"]
    )
    return {
        "observations": size,
        "workload": "hotspot/all names identical"
        if hotspot
        else "two sources with labelled counterpart pairs and 10% diacritic variants",
        "elapsed_seconds": round(elapsed, 3),
        "traced_peak_mib": round(peak / 1024 / 1024, 2),
        "pairs_evaluated": result["pairs_evaluated"],
        "complete_within_candidate_rules": result["complete_within_candidate_rules"],
        "bucket_overflows": result["bucket_overflows"],
        "labelled_positive_pairs_retrieved": positives,
        "expected_counterparts": None if hotspot else size // 2,
        "scope": "single local Python process including generated inputs/index/scoring under tracemalloc; no network, database, disk persistence or production throughput claim",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--size", type=int, choices=(10000, 50000), default=10000)
    parser.add_argument("--hotspot", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            benchmark(args.size, hotspot=args.hotspot) if args.benchmark else demo(),
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
