"""Original-only multi-source field review and durable planning regressions."""

from datetime import UTC, datetime, timedelta

import pytest
from fraggy_api.collection.pilot_planning import (
    Assessment,
    Observation,
    SearchSnapshot,
    compare_observations,
    enqueue_plan,
    plan_enrichment,
)
from fraggy_api.importing.formats import Record
from fraggy_api.models import EnrichmentIntent, Fragrance
from sqlalchemy import func, select

AT = datetime(2026, 10, 20, tzinfo=UTC)


def record(**changes):
    return Record.model_validate(
        {
            "source_record_id": "fictional-001",
            "brand_name": "Invented Atelier",
            "fragrance_name": "Original Glass",
            "concentration": "EDP",
            "release_year": 2020,
            "perfumers": ["Fictional Nose"],
            "notes": [{"name": "Cedar", "position": "base"}],
            **changes,
        }
    )


def observations(**changes):
    return [
        Observation(
            source="official_brand",
            reference="original-a",
            collected_at=AT,
            record=record(),
        ),
        Observation(
            source="openbeautyfacts",
            reference="original-b",
            collected_at=AT,
            record=record(**changes),
        ),
    ]


def test_multi_source_values_are_preserved_and_never_selected():
    rows = observations(concentration="eau_de_parfum", release_year=2021)
    rows[0].assessments = [
        Assessment(
            field="release_year",
            reliability="brand_authored",
            evidence_reference="original-local-evidence",
            reviewer="fixture-reviewer",
            verified_at=AT,
        )
    ]
    result = compare_observations(rows, AT)
    years = result["fields"]["release_year"]
    assert years["state"] == "conflict"
    assert [c["original_value"] for c in years["claims"]] == [2020, 2021]
    assert years["claims"][0]["reliability"] == "brand_authored"
    assert years["claims"][1]["reliability"] == "unknown"
    assert years["preferred_claim"] is None
    assert result["fields"]["concentration"]["state"] == "agrees"
    assert result["independent_source_count"] == 2
    assert not result["automatic_merge"] and not result["publication_authorized"]


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"notes": [{"name": "Cedar", "position": "top"}]}, "notes"),
        ({"concentration": "EDT"}, "concentration"),
        ({"fragrance_name": "Original Glass Night"}, "fragrance_name"),
        ({"version_label": "Original fictional reformulation 2"}, "version_label"),
    ],
)
def test_different_products_or_note_positions_never_merge(changes, field):
    report = compare_observations(observations(**changes), AT)
    assert report["fields"][field]["state"] in {"conflict", "partial"}
    assert report["fields"][field]["preferred_claim"] is None
    assert report["automatic_merge"] is False


def test_partial_fields_and_unverified_assessment_are_explicit():
    rows = observations(notes=[], release_year=None)
    rows[0].assessments = [
        Assessment(
            field="notes",
            reliability="corroborated",
            evidence_reference="fixture",
            reviewer="fixture",
            verified_at=AT + timedelta(days=1),
        )
    ]
    result = compare_observations(rows, AT)
    assert result["fields"]["notes"]["state"] == "partial"
    assert result["fields"]["notes"]["claims"][0]["reliability"] == "unknown"
    assert "images" in result["unsupported_fields"]


def test_duplicate_observation_and_unbounded_inputs_rejected():
    rows = observations()
    with pytest.raises(ValueError):
        compare_observations([rows[0], rows[0]], AT)
    with pytest.raises(ValueError):
        compare_observations(rows * 6, AT)
    with pytest.raises(ValueError):
        plan_enrichment(SearchSnapshot(query="Original", providers=["unknown"]), AT)
    with pytest.raises(ValueError):
        plan_enrichment(
            SearchSnapshot(query="Original", required_fields=["invented"]), AT
        )


def test_fresh_complete_snapshot_needs_no_enrichment():
    snapshot = SearchSnapshot(
        query="Original Glass",
        record=record(),
        verified_fields={
            field: AT for field in SearchSnapshot(query="x").required_fields
        },
    )
    assert not plan_enrichment(snapshot, AT)["needs_enrichment"]
    assert plan_enrichment(snapshot, AT + timedelta(days=91))["needs_enrichment"]
    snapshot.verified_fields["notes"] = AT + timedelta(days=1)
    assert "notes" in plan_enrichment(snapshot, AT)["stale_or_unverified_fields"]


async def test_plan_enqueue_dedup_rollback_replay_and_no_canonical_writes(session):
    before = await session.scalar(select(func.count()).select_from(Fragrance))
    snapshot = SearchSnapshot(
        query="Lattafa Khamrah", providers=["openbeautyfacts", "wikidata", "parfumo"]
    )
    async with session.begin_nested() as transaction:
        first = await enqueue_plan(session, snapshot, AT)
        again = await enqueue_plan(session, snapshot, AT)
        assert first["intents"] == again["intents"]
        assert len(first["intents"]) == 3
        assert all(not row["live_eligible"] for row in first["providers"])
        await transaction.rollback()
    assert await session.scalar(select(func.count()).select_from(EnrichmentIntent)) == 0
    replay = await enqueue_plan(session, snapshot, AT)
    assert len(replay["intents"]) == 3
    assert await session.scalar(select(func.count()).select_from(Fragrance)) == before
    complete = SearchSnapshot(
        query="Original",
        record=record(),
        verified_fields={field: AT for field in snapshot.required_fields},
    )
    assert (await enqueue_plan(session, complete, AT))["intents"] == []
