"""Offline proposals cannot approve sources or turn fixture IDs into real data."""

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fraggy_api.pilot_readiness import (
    USER_AGENT_TEMPLATE,
    Candidate,
    PilotProposal,
    usable_contact,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[3]


def original_candidate(**changes):
    return Candidate.model_validate(
        {
            "qid": "Q990000000001",
            "synthetic": True,
            "classification": "fragrance",
            "fragrance_name": "Original Fictional Perfume",
            "brand_name": "Original Fictional Workshop",
            "relationship": "brand",
            "checked_fields": [
                "identity",
                "classification",
                "name",
                "relationship",
                "concentration",
                "release_year",
                "notes",
                "accords",
            ],
            "reviewer": "fixture-reviewer",
            "verified_on": date.today(),
            "evidence_urls": ["https://www.wikidata.org/wiki/Q990000000001"],
            **changes,
        }
    )


def test_disabled_live_proposal_contains_no_invented_real_candidates():
    proposal = PilotProposal.model_validate_json(
        (ROOT / "config/wikidata-pilot-proposal.json").read_text()
    )
    assert proposal.user_agent == USER_AGENT_TEMPLATE
    report = proposal.report()
    assert report["enabled"] is False and report["network_requests"] == 0
    assert report["real_candidate_count"] == report["qualified_candidate_count"] == 0
    assert "monitored_contact_not_supplied" in report["blockers"]


@pytest.mark.parametrize(
    "flag", ["enabled", "live_discovery_approved", "live_collection_approved"]
)
def test_proposal_never_activates_or_approves_collection(flag):
    with pytest.raises(ValidationError):
        PilotProposal.model_validate({flag: True})


def test_synthetic_candidate_never_becomes_qualified_for_live_collection():
    candidate = original_candidate()
    assert candidate.blockers() == ["synthetic_not_a_real_candidate"]
    assert (
        PilotProposal(candidates=[candidate]).report()["qualified_candidate_count"] == 0
    )


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"classification": "brand"}, "fragrance_classification_not_verified"),
        ({"relationship": "manufacturer"}, "brand_relationship_not_verified"),
        ({"brand_name": " "}, "brand_relationship_not_verified"),
        ({"checked_fields": ["identity"]}, "field_assessment_incomplete"),
        ({"ambiguities": ["Same name as a brand"]}, "unresolved_ambiguity"),
        ({"reviewer": None}, "review_evidence_incomplete"),
        (
            {"evidence_urls": ["https://example.invalid/fixture"]},
            "entity_evidence_missing",
        ),
    ],
)
def test_candidate_validation_preserves_ambiguity_and_missing_metadata(
    changes, expected
):
    candidate = original_candidate(**changes)
    assert expected in candidate.blockers()
    assert candidate.concentration is None and candidate.release_year is None
    assert candidate.notes is None and candidate.accords is None


@pytest.mark.parametrize(
    "changes",
    [
        {"qid": "Q1 UNION SELECT"},
        {"verified_on": date.today() + timedelta(days=1)},
        {"checked_fields": ["identity", "identity"]},
        {"evidence_urls": ["javascript:alert(1)"]},
    ],
)
def test_invalid_candidate_evidence_is_rejected(changes):
    with pytest.raises(ValidationError):
        original_candidate(**changes)


def test_duplicate_and_oversized_candidate_lists_are_rejected():
    candidate = original_candidate()
    with pytest.raises(ValidationError):
        PilotProposal(candidates=[candidate, candidate])
    with pytest.raises(ValidationError):
        PilotProposal(candidates=[candidate] * 101)


@pytest.mark.parametrize(
    "contact",
    [
        None,
        USER_AGENT_TEMPLATE,
        USER_AGENT_TEMPLATE.replace("CONTACT_EMAIL", "fixture@example.invalid"),
        USER_AGENT_TEMPLATE.replace("CONTACT_EMAIL", "someone@example.org"),
        USER_AGENT_TEMPLATE.replace("CONTACT_EMAIL", "not-an-email"),
    ],
)
def test_placeholder_and_unverified_example_contacts_are_not_live_ready(contact):
    assert not usable_contact(contact)


def test_offline_command_reports_blockers_without_source_activation():
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_pilot_readiness.py"),
            str(ROOT / "config/wikidata-pilot-proposal.json"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert (
        report["offline_only"]
        and report["network_requests"] == 0
        and report["enabled"] is False
    )
