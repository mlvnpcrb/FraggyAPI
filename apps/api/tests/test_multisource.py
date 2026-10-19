"""Original fixtures only; no website, image or database collection."""

import json
import socket
from pathlib import Path

import pytest
from fraggy_api.collection import multisource
from fraggy_api.collection.multisource import Checkpoint, rehearse
from fraggy_api.collection.offline_sources import ADAPTERS, FixturePage
from fraggy_api.collection.policy import CollectionError
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]


def pages():
    return [
        FixturePage.model_validate_json(path.read_text())
        for path in sorted((ROOT / "data/examples/multisource").glob("*.json"))
    ]


def test_independent_adapters_keep_provenance_unknowns_and_never_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Network forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    report = rehearse(pages())
    assert report["counts"] == {"new": 7, "changed": 0, "unchanged": 0, "pages": 4}
    assert (
        report["database_writes"]
        == report["external_requests"]
        == report["published"]
        == 0
    )
    assert not report["schedule_enabled"]
    state = Checkpoint.model_validate(report["checkpoint"])
    assert {item.source for item in state.records.values()} == set(ADAPTERS)
    assert all(
        item.rights == "fixture_only" and item.collected_at.tzinfo
        for item in state.records.values()
    )
    wikidata = next(
        item for item in state.records.values() if item.source == "wikidata"
    )
    assert (
        wikidata.record.release_year is None and wikidata.record.concentration is None
    )
    assert not wikidata.record.notes and not wikidata.record.perfumers


@pytest.mark.parametrize("source", list(ADAPTERS))
def test_each_adapter_unconditionally_denies_live_collection(source):
    with pytest.raises(CollectionError, match="live_collection_disabled"):
        ADAPTERS[source].collect()


def test_note_positions_are_preserved_without_inference():
    page = next(p for p in pages() if p.source == "fragrantica")
    assert (
        ADAPTERS[page.source].parse(page)[0].source_metadata["gender_positioning"]
        == "Fictional unisex positioning"
    )
    assert [n.position for n in ADAPTERS[page.source].parse(page)[0].notes] == [
        "top",
        "heart",
        "base",
    ]
    page = next(p for p in pages() if p.source == "parfumo")
    assert ADAPTERS[page.source].parse(page)[0].notes[0].position == "unknown"


def test_cross_source_conflicts_and_product_distinctions_never_merge():
    report = rehearse(pages())
    pairs = report["comparison"]["pairs"]
    labels = {pair["classification"] for pair in pairs}
    assert {
        "possible_duplicate",
        "distinct_concentration",
        "related_name_review",
        "distinct_version_review",
        "incomplete_identity",
    } <= labels
    assert any(
        {"perfumers", "notes", "accords"} <= set(pair["conflicting_fields"])
        for pair in pairs
    )
    assert all(
        pair["review_required"] and not pair["automatic_merge"] for pair in pairs
    )
    assert all(
        "not accuracy" in score["meaning"] for score in report["quality"].values()
    )


def test_resume_is_idempotent_and_changed_payload_requires_review():
    first = rehearse(pages())
    state = Checkpoint.model_validate(first["checkpoint"])
    again = rehearse(pages(), state)
    assert again["counts"]["unchanged"] == 7 and not again["changes"]
    page = next(p for p in pages() if p.source == "parfumo").model_copy(deep=True)
    page.payload["entries"][0]["perfumers"] = ["Changed Fictional Credit"]
    changed = rehearse([page], state)
    assert changed["counts"]["changed"] == 1
    assert changed["changes"][0]["before"] != changed["changes"][0]["after"]
    assert state.model_dump(mode="json") == first["checkpoint"]


def test_interrupted_page_continuation_and_failure_are_transactional():
    page = next(p for p in pages() if p.source == "official_brand").model_copy(
        deep=True
    )
    page.next_page = 1
    first = rehearse([page])
    state = Checkpoint.model_validate(first["checkpoint"])
    second = page.model_copy(deep=True)
    second.page, second.next_page = 1, None
    assert rehearse([second], state)["counts"]["unchanged"] == 2
    with pytest.raises(CollectionError, match="checkpoint_mismatch"):
        rehearse([page], state)
    bad = second.model_copy(deep=True)
    bad.payload["products"].append({"source_record_id": "invalid"})
    with pytest.raises(CollectionError, match="malformed_page"):
        rehearse([bad], state)
    assert state.model_dump(mode="json") == first["checkpoint"]


@pytest.mark.parametrize(
    "fault", ["real_flag", "image", "note_string", "duplicate", "missing_name"]
)
def test_malformed_or_unapproved_fixture_shapes_fail(fault):
    page = next(p for p in pages() if p.source == "fragrantica").model_dump(mode="json")
    row = page["payload"]["perfumes"][0]
    if fault == "real_flag":
        page["synthetic"] = False
    elif fault == "image":
        row["image"] = "https://example.invalid/never-download.jpg"
    elif fault == "note_string":
        row["top"] = "not a note list"
    elif fault == "duplicate":
        page["payload"]["perfumes"].append(dict(row))
    else:
        del row["title"]
    with pytest.raises((ValidationError, CollectionError)):
        rehearse([FixturePage.model_validate(page)])


def test_checkpoint_tampering_and_unknown_sources_fail():
    report = rehearse(pages())
    state = report["checkpoint"]
    identifier = next(iter(state["records"]))
    state["records"][identifier]["rights"] = "approved"
    with pytest.raises(ValidationError):
        Checkpoint.model_validate(state)
    state["records"][identifier]["rights"] = "fixture_only"
    state["records"]["wrong-key"] = state["records"].pop(identifier)
    with pytest.raises(ValidationError):
        Checkpoint.model_validate(state)


def test_comparison_overflow_is_explicit(monkeypatch):
    monkeypatch.setattr(multisource, "MAX_PAIRS", 1)
    report = rehearse(pages())
    assert not report["comparison"]["complete"]
    assert len(report["comparison"]["pairs"]) == 1


def test_batch_record_and_page_limits_do_not_return_partial_state(monkeypatch):
    monkeypatch.setattr(multisource, "MAX_RECORDS", 1)
    with pytest.raises(CollectionError, match="record_limit"):
        rehearse(pages())
    monkeypatch.setattr(multisource, "MAX_RECORDS", 5000)
    monkeypatch.setattr(multisource, "MAX_PAGES", 1)
    with pytest.raises(CollectionError, match="page_limit"):
        rehearse(pages())


def thousand_pages():
    for page in range(20):
        yield FixturePage.model_validate(
            {
                "synthetic": True,
                "source": "official_brand",
                "dataset": "scale-fictional",
                "collected_at": "2026-01-01T00:00:00Z",
                "page": page,
                "next_page": page + 1 if page < 19 else None,
                "payload": {
                    "products": [
                        {
                            "source_record_id": f"fixture-{i}",
                            "brand_name": "Invented Scale House",
                            "fragrance_name": f"Invented{i:04d} Fixture",
                            "concentration": "EDP",
                            "release_year": 2020,
                        }
                        for i in range(page * 50, page * 50 + 50)
                    ]
                },
            }
        )


def test_thousand_record_stream_and_roundtrip():
    report = rehearse(thousand_pages())
    assert report["record_count"] == report["counts"]["new"] == 1000
    assert report["counts"]["pages"] == 20
    assert report["comparison"]["complete"]
    state = Checkpoint.model_validate(json.loads(json.dumps(report["checkpoint"])))
    assert rehearse(thousand_pages(), state)["counts"]["unchanged"] == 1000


def test_variant_sizes_stay_separate_while_normalized_credits_agree():
    first = next(p for p in pages() if p.source == "parfumo").model_copy(deep=True)
    first.payload["entries"] = first.payload["entries"][:1]
    first.payload["entries"][0]["perfumers"] = ["Fictional Perfumer A"]
    second = next(p for p in pages() if p.source == "official_brand").model_copy(
        deep=True
    )
    second.payload["products"] = second.payload["products"][:1]
    row = second.payload["products"][0]
    row.pop("version_label")
    row["release_year"] = 2020
    row["perfumers"] = ["  FICTIONAL perfumer a "]
    row["bottle_sizes_ml"] = [30]
    first.payload["entries"][0].pop("notes")
    first.payload["entries"][0].pop("accords")
    # Parfumo's fixture contract has no bottle size field, so compare two
    # independently identified authorized-brand fixture datasets for variants.
    third = second.model_copy(deep=True)
    third.dataset = "other-fictional-feed"
    third.payload["products"][0]["bottle_sizes_ml"] = [50]
    report = rehearse([first, second, third])
    assert any(pair["variant_review"] for pair in report["comparison"]["pairs"])
    assert all(
        "perfumers" not in pair["conflicting_fields"]
        for pair in report["comparison"]["pairs"]
    )


def test_byte_limit_fails_before_returning_a_checkpoint(monkeypatch):
    monkeypatch.setattr(multisource, "MAX_STATE_BYTES", 1)
    with pytest.raises(CollectionError, match="byte_limit"):
        rehearse(pages())
