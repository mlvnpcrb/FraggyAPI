"""Original fictional naming examples; no real perfume data."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from fraggy_api.collection.diagnostics import explain, inspect_response, source_health
from fraggy_api.collection.intelligence import indexed_review, match
from fraggy_api.collection.offline_sources import ADAPTERS, FixturePage
from fraggy_api.collection.policy import Endpoint
from fraggy_api.collection.priority import Budget, Task, backoff, plan
from fraggy_api.collection.transport import Response
from fraggy_api.importing.formats import Record, digest


def record(**changes):
    return Record.model_validate(
        {
            "source_record_id": "fictional-1",
            "brand_name": "Invented Atelier",
            "fragrance_name": "Lumiere Archive",
            "concentration": "EDP",
            "release_year": 2020,
            **changes,
        }
    )


def endpoint(adapter="json_feed"):
    return Endpoint(
        url="http://127.0.0.1:1", adapter=adapter, minimum_interval_seconds=1
    )


def test_exact_identity_is_explainable_but_not_accuracy_completeness_or_a_merge():
    result = match(record(), record(concentration="eau_de_parfum"))
    assert result["score"] == 90
    assert sum(item["points"] for item in result["reasons"]) == 90
    assert result["status"] == "ready_for_human_review"
    assert not result["automatic_merge"] and not result["publication_authorized"]
    assert "not factual accuracy" in result["meaning"]


@pytest.mark.parametrize(
    "changes,guard,ceiling",
    [
        ({"concentration": "EDT"}, "distinct_concentration", 20),
        ({"release_year": 2022}, "release_year_requires_separate_release_review", 49),
        (
            {"version_label": "Limited Edition"},
            "edition_or_reformulation_requires_review",
            49,
        ),
        (
            {"version_label": "Reformulation 2022"},
            "edition_or_reformulation_requires_review",
            49,
        ),
        (
            {"fragrance_name": "Lumiere Archive Intense"},
            "related_name_may_be_flanker",
            49,
        ),
        (
            {"fragrance_name": "Lumière-Archive"},
            "orthographic_variant_requires_review",
            79,
        ),
        ({"brand_name": "Invented-Atelier"}, "orthographic_brand_requires_review", 79),
        (
            {"source_metadata": {"strength_label": "Elixir"}},
            "strength_descriptor_differs_or_unknown",
            49,
        ),
    ],
)
def test_difficult_names_and_release_guards(changes, guard, ceiling):
    result = match(record(), record(**changes))
    assert guard in result["guards"] and result["score"] <= ceiling
    assert result["status"] != "ready_for_human_review"


def test_manufacturer_is_not_a_brand_and_aliases_are_claims():
    result = match(
        record(source_metadata={"manufacturer": "Invented Parent"}),
        record(brand_name="Invented Parent"),
    )
    assert "manufacturer_is_not_brand" in result["guards"]
    result = match(
        record(),
        record(
            fragrance_name="光のアーカイブ",
            source_metadata={"name_alias": "Lumiere Archive"},
        ),
    )
    assert "alias_identity_not_independently_verified" in result["guards"]
    assert result["score"] <= 79


def test_conflicts_missing_data_and_packaging_are_separate_review_evidence():
    result = match(
        record(
            perfumers=["Fictional A"],
            notes=[{"name": "Invented Leaf", "position": "top"}],
            accords=["Invented Green"],
            bottle_sizes_ml=[30],
        ),
        record(
            perfumers=["Fictional B"],
            notes=[{"name": "Invented Wood", "position": "base"}],
            accords=["Invented Woody"],
            bottle_sizes_ml=[50],
        ),
    )
    assert {"perfumers", "notes", "accords"} <= set(result["conflicting_fields"])
    assert result["variant_review"]
    missing = match(record(), record(concentration=None, release_year=None))
    assert missing["score"] <= 69 and {"concentration", "release_year"} <= set(
        missing["missing_fields"]
    )


def test_bounded_index_emits_provenance_without_comparing_same_stream():
    result = indexed_review(
        [
            ("a", "feed-a", record()),
            ("b", "feed-b", record()),
            ("c", "feed-a", record()),
        ]
    )
    assert result["pairs_evaluated"] == 2
    assert result["pairs"][0]["field_provenance"]["notes"] == {
        "left": "a",
        "right": "b",
    }
    limited = indexed_review(
        [(str(i), str(i), record()) for i in range(10)], max_pairs=2, bucket_limit=2
    )
    assert (
        limited["pairs_evaluated"] == 2
        and not limited["complete_within_candidate_rules"]
    )
    with pytest.raises(ValueError):
        indexed_review([("same", "a", record()), ("same", "b", record())])


@pytest.mark.parametrize(
    "adapter,body,mime",
    [
        (
            "rest_json",
            json.dumps({"records": [record().model_dump(mode="json")]}).encode(),
            "application/json",
        ),
        (
            "csv_feed",
            b"source_record_id,brand_name,fragrance_name,concentration,release_year\nf1,Invented Atelier,Lumiere Archive,EDP,2020\n",
            "text/csv",
        ),
        (
            "html_json",
            (
                '<html><script id="fragrance-data" type="application/json">'
                + json.dumps({"records": [record().model_dump(mode="json")]})
                + "</script></html>"
            ).encode(),
            "text/html",
        ),
    ],
)
def test_local_structured_api_feed_and_permitted_html_contracts(adapter, body, mime):
    result = inspect_response(Response(200, body, mime), endpoint(adapter))
    assert result["ok"] and result["records"] == 1
    repeated = inspect_response(
        Response(200, body, mime),
        endpoint(adapter),
        seen_pages={result["page_fingerprint"]},
    )
    assert (
        not repeated["ok"]
        and repeated["diagnostic"]["category"] == "pagination_or_duplicate_failure"
    )


@pytest.mark.parametrize(
    "status,category",
    [
        (401, "access_restricted"),
        (403, "access_restricted"),
        (429, "rate_limited"),
        (503, "upstream_unavailable"),
    ],
)
def test_http_failure_diagnostics_never_expose_upstream_content(status, category):
    result = inspect_response(
        Response(status, b"private upstream token and CAPTCHA body", "text/html"),
        endpoint(),
    )
    assert result["diagnostic"]["category"] == category
    assert (
        "private" not in json.dumps(result)
        and not result["diagnostic"]["automatic_bypass"]
    )


def test_schema_missing_fields_incomplete_pagination_and_health():
    invalid = inspect_response(
        Response(
            200,
            b'{"records":[{"source_record_id":"f1","secret-token":"PRIVATE"}]}',
            "application/json",
        ),
        endpoint(),
    )
    assert not invalid["ok"]
    assert "PRIVATE" not in json.dumps(invalid) and "secret-token" not in json.dumps(
        invalid
    )
    assert ["brand_name"] in invalid["diagnostic"]["field_paths"]
    assert source_health([invalid["diagnostic"]])["health"] == "blocked"
    short = inspect_response(
        Response(200, b'{"records":[]}', "application/json"),
        endpoint(),
        expected_final_records=2,
    )
    assert short["diagnostic"]["category"] == "pagination_or_duplicate_failure"
    assert explain("network_timeout")["category"] == "network_timeout_or_failure"
    assert source_health([explain("network_timeout")])["health"] == "degraded"
    assert (
        explain("collection_not_authorized", 429)["category"] == "authorization_blocked"
    )


def test_elixir_preserves_descriptor_and_never_invents_parfum_strength():
    fixture = FixturePage.model_validate(
        {
            "synthetic": True,
            "source": "official_brand",
            "dataset": "original",
            "collected_at": "2026-01-01T00:00:00Z",
            "payload": {
                "products": [
                    record().model_dump(mode="json") | {"concentration": "Elixir"}
                ]
            },
        }
    )
    result = ADAPTERS[fixture.source].parse(fixture)[0]
    assert (
        result.concentration is None
        and result.source_metadata["strength_label"] == "Elixir"
    )


def test_offline_queue_priorities_duplicates_budgets_health_and_due_times():
    now = datetime(2026, 1, 1, tzinfo=UTC)

    def task(identifier, source="a", priority=1, **extra):
        return Task(
            id=identifier,
            source=source,
            fingerprint=digest([source, extra.pop("request", "same")]),
            priority=priority,
            due_at=now,
            **extra,
        )

    tasks = [
        task("low"),
        task("high", priority=9),
        task("blocked", source="b"),
        task("exhausted", source="c"),
        task("retry", source="d", attempt=2, retry_limit=1),
    ]
    budgets = {
        source: Budget(
            remaining=0 if source == "c" else 2,
            next_request_at=now,
            health="blocked" if source == "b" else "healthy",
        )
        for source in "abcd"
    }
    result = plan(tasks, budgets, now)
    assert result["would_dispatch"] == ["high"] and not result["dispatch_allowed"]
    assert {item["reason"] for item in result["deferred"]} == {
        "duplicate_request",
        "source_unavailable",
        "source_budget_exhausted",
        "retry_budget_exhausted",
    }
    budgets["a"].next_request_at = now + timedelta(seconds=10)
    assert not plan([task("delayed")], budgets, now)["would_dispatch"]
    assert backoff(3, 20) == 20
    with pytest.raises(ValueError):
        backoff(1, 301)


def test_shared_identifier_never_overrides_different_concentration():
    # Original synthetic EAN with a calculated check digit, not a perfume lookup.
    prefix = "999000000001"
    total = sum(
        int(v) * (3 if i % 2 == 0 else 1) for i, v in enumerate(reversed(prefix))
    )
    gtin = prefix + str((-total) % 10)
    result = match(record(gtin=gtin), record(gtin=gtin, concentration="EDT"))
    assert result["score"] <= 20
    assert "distinct_concentration" in result["guards"]


def test_unusable_labels_require_correction_and_cannot_score_high():
    result = match(record(fragrance_name="---"), record(fragrance_name="---"))
    assert result["score"] == 0 and result["status"] == "requires_correction"
    indexed = indexed_review([("bad", "a", record(fragrance_name="---"))])
    assert indexed["records_requiring_correction"] == ["bad"]


def test_explicit_alias_candidate_and_alias_overflow_are_visible():
    left = record()
    right = record(
        brand_name="Fictional Translated Atelier",
        brand_aliases=["Invented Atelier"],
        fragrance_name="光のアーカイブ",
        source_metadata={"name_alias": "Lumiere Archive"},
    )
    result = indexed_review([("a", "one", left), ("b", "two", right)])
    assert result["pairs_evaluated"] == 1 and result["pairs"][0]["score"] <= 79
    limited = indexed_review(
        [
            (
                "many",
                "one",
                record(brand_aliases=[f"Original Alias {i}" for i in range(6)]),
            )
        ]
    )
    assert (
        limited["alias_truncations"] == 1
        and not limited["complete_within_candidate_rules"]
    )


def test_packaging_variants_and_one_inflight_rule_remain_distinct():
    assert match(
        record(source_metadata={"packaging": "gift set"}),
        record(source_metadata={"packaging": "single bottle"}),
    )["variant_review"]
    now = datetime(2026, 1, 1, tzinfo=UTC)
    tasks = [
        Task(id=f"job-{i}", source="original", fingerprint=digest(i), due_at=now)
        for i in range(2)
    ]
    result = plan(tasks, {"original": Budget(remaining=2, next_request_at=now)}, now)
    assert len(result["would_dispatch"]) == 1
    assert result["deferred"][0]["reason"] == "one_inflight_per_source"


def test_middle_notes_normalize_to_heart_with_explicit_transformation():
    page = FixturePage.model_validate(
        {
            "synthetic": True,
            "source": "fragrantica",
            "dataset": "original",
            "collected_at": "2026-01-01T00:00:00Z",
            "payload": {
                "perfumes": [
                    {
                        "id": "f1",
                        "title": "Original Middle Note",
                        "house": "Invented Atelier",
                        "middle": ["Invented Petal"],
                    }
                ]
            },
        }
    )
    parsed = ADAPTERS[page.source].parse(page)[0]
    assert parsed.notes[0].position == "heart"
    assert parsed.source_metadata["note_position_mapping"] == "middle_to_heart"


def test_multiple_identical_candidates_reduce_confidence_without_merging():
    result = indexed_review(
        [("a", "first", record()), ("b", "first", record()), ("c", "second", record())]
    )
    assert len(result["pairs"]) == 2
    assert all(
        pair["score"] <= 69 and "multiple_candidates_require_review" in pair["guards"]
        for pair in result["pairs"]
    )
