"""Invented local identities only; nothing here is a real-source authorization."""

import json
import socket

import pytest
from fraggy_api.collection.policy import CollectionError
from fraggy_api.pilot_preparation import PilotPlan, dry_run, fixture_pages
from pydantic import ValidationError


@pytest.mark.parametrize("quantity", [20, 25, 26, 50])
def test_bounded_rehearsal_reuses_mapping_quality_and_never_networks(
    quantity, monkeypatch
):
    def denied(*args, **kwargs):
        raise AssertionError("Offline preparation attempted network access")

    monkeypatch.setattr(socket.socket, "connect", denied)
    result = dry_run(PilotPlan(quantity=quantity))
    assert result["records_validated"] == quantity
    assert result["pages_validated"] == (quantity + 24) // 25
    assert result["quality"]["unknown_years"] == quantity
    assert result["quality"]["missing_notes"] == quantity
    assert result["quality"]["complete"]
    assert result["external_requests"] == result["database_writes"] == 0
    assert result["staged"] == result["published"] == 0
    assert not result["scheduled"]
    assert result["images_collected"] == 0
    assert not result["approval"]["collection_ready"]
    assert result["provenance"]["source_record_ids"] == quantity


@pytest.mark.parametrize("quantity", [0, 19, 51, 100])
def test_rejects_mass_or_undersized_pilot(quantity):
    with pytest.raises(ValidationError):
        PilotPlan(quantity=quantity)


@pytest.mark.parametrize(
    "field", ["enabled", "live_discovery_approved", "live_collection_approved"]
)
def test_plan_cannot_authorize_any_live_activity(field):
    with pytest.raises(ValidationError):
        PilotPlan.model_validate({field: True})


def test_approval_budget_and_separate_storage_publication_decisions():
    report = PilotPlan(quantity=25).report()
    assert report["collection_attempt_ceiling"] == 2
    assert report["discovery_attempt_ceiling"] == 2
    assert report["qualified_candidate_count"] == 0
    assert not report["storage_approved"]
    assert not report["publication_approved"]
    assert "exact_reviewed_candidate_list_required" in report["blockers"]
    assert "monitored_contact_not_supplied" in report["blockers"]


def test_rehearsal_fingerprints_are_repeatable_and_do_not_suppress_new_versions():
    plan = PilotPlan()
    original = dry_run(plan)
    assert original["idempotency_digest"] == dry_run(plan)["idempotency_digest"]
    pages = fixture_pages(plan.quantity)
    page = json.loads(pages[0])
    page["results"]["bindings"][0]["itemLabel"]["value"] += " Fictional Flanker"
    pages[0] = json.dumps(page).encode()
    assert dry_run(plan, pages)["idempotency_digest"] != original["idempotency_digest"]


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unexpected", "malformed"])
def test_invalid_page_never_yields_a_successful_rehearsal(fault):
    pages = fixture_pages(25)
    page = json.loads(pages[0])
    rows = page["results"]["bindings"]
    if fault == "missing":
        rows.pop()
    elif fault == "duplicate":
        rows[1] = rows[0]
    elif fault == "unexpected":
        rows[0]["image"] = {"value": "https://example.invalid/forbidden.jpg"}
    elif fault == "malformed":
        page = {"results": "invalid"}
    with pytest.raises(CollectionError):
        dry_run(PilotPlan(), [json.dumps(page).encode()])


def test_no_checkpoint_success_on_missing_second_page():
    with pytest.raises(CollectionError, match="page_count"):
        dry_run(PilotPlan(quantity=50), fixture_pages(50)[:1])


def test_equal_names_with_missing_release_identity_require_manual_review():
    pages = fixture_pages(25)
    page = json.loads(pages[0])
    rows = page["results"]["bindings"]
    # Same fictional house, different source IDs, absent concentration/year.
    rows[5]["itemLabel"] = rows[0]["itemLabel"]
    result = dry_run(PilotPlan(), [json.dumps(page).encode()])
    assert result["quality"]["pair_classifications"]["incomplete_identity"] == 1
    assert result["records_validated"] == 25
    assert result["staged"] == result["published"] == 0


def test_unrequested_entity_is_rejected_before_quality_or_staging():
    page = json.loads(fixture_pages(25)[0])
    page["results"]["bindings"][0]["item"]["value"] = (
        "http://www.wikidata.org/entity/Q990000088888"
    )
    with pytest.raises(CollectionError, match="unrequested"):
        dry_run(PilotPlan(), [json.dumps(page).encode()])
