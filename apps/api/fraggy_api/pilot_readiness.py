"""Offline pilot review only. This module has no network or activation operation."""

import re
from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from .importing.formats import Strict

USER_AGENT_TEMPLATE: Literal[
    "FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; CONTACT_EMAIL)"
] = "FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; CONTACT_EMAIL)"


def usable_contact(agent: str | None) -> bool:
    if agent is None:
        return False
    match = re.fullmatch(
        r"FraggyAPI/[0-9.]+ \(https://github.com/mlvnpcrb/FraggyAPI; ([A-Za-z0-9_.+-]+)@([A-Za-z0-9.-]+)\)",
        agent,
    )
    if not match:
        return False
    domain = match[2].lower()
    return (
        "." in domain
        and domain not in {"example.com", "example.org", "example.net"}
        and not domain.endswith((".invalid", ".localhost", ".local"))
    )


class Candidate(Strict):
    qid: str = Field(pattern=r"^Q[1-9][0-9]{0,15}$")
    synthetic: bool
    classification: Literal["fragrance", "brand", "other", "unverified"]
    fragrance_name: str | None = Field(default=None, max_length=300)
    brand_name: str | None = Field(default=None, max_length=300)
    relationship: Literal["brand", "manufacturer", "ambiguous", "unknown"] = "unknown"
    concentration: str | None = Field(default=None, max_length=80)
    release_year: int | None = Field(default=None, ge=1000, le=2999)
    notes: list[str] | None = Field(default=None, max_length=40)
    accords: list[str] | None = Field(default=None, max_length=20)
    checked_fields: list[
        Literal[
            "identity",
            "classification",
            "name",
            "relationship",
            "concentration",
            "release_year",
            "notes",
            "accords",
        ]
    ] = Field(default_factory=list, max_length=8)
    ambiguities: list[str] = Field(default_factory=list, max_length=20)
    reviewer: str | None = Field(default=None, max_length=100)
    verified_on: date | None = None
    evidence_urls: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def evidence(self) -> "Candidate":
        from .attribution import safe_public_url

        if len(set(self.checked_fields)) != len(self.checked_fields):
            raise ValueError("Duplicate field checks")
        for url in self.evidence_urls:
            safe_public_url(url)
        if self.verified_on and self.verified_on > date.today():
            raise ValueError("Future verification is invalid")
        return self

    def blockers(self) -> list[str]:
        result = []
        if self.synthetic:
            result.append("synthetic_not_a_real_candidate")
        if self.classification != "fragrance":
            result.append("fragrance_classification_not_verified")
        if not self.fragrance_name or not self.fragrance_name.strip():
            result.append("name_not_verified")
        if (
            not self.brand_name
            or not self.brand_name.strip()
            or self.relationship != "brand"
        ):
            result.append("brand_relationship_not_verified")
        if set(self.checked_fields) != {
            "identity",
            "classification",
            "name",
            "relationship",
            "concentration",
            "release_year",
            "notes",
            "accords",
        }:
            result.append("field_assessment_incomplete")
        if f"https://www.wikidata.org/wiki/{self.qid}" not in self.evidence_urls:
            result.append("entity_evidence_missing")
        if self.ambiguities:
            result.append("unresolved_ambiguity")
        if (
            not self.reviewer
            or not self.reviewer.strip()
            or not self.verified_on
            or not self.evidence_urls
        ):
            result.append("review_evidence_incomplete")
        return result


class PilotProposal(Strict):
    enabled: Literal[False] = False
    live_discovery_approved: Literal[False] = False
    live_collection_approved: Literal[False] = False
    user_agent: Literal[
        "FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; CONTACT_EMAIL)"
    ] = USER_AGENT_TEMPLATE
    candidates: list[Candidate] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique(self) -> "PilotProposal":
        if len({c.qid for c in self.candidates}) != len(self.candidates):
            raise ValueError("Duplicate candidate identities")
        return self

    def report(self) -> dict[str, object]:
        return {
            "offline_only": True,
            "network_requests": 0,
            "enabled": False,
            "real_candidate_count": sum(not c.synthetic for c in self.candidates),
            "qualified_candidate_count": sum(not c.blockers() for c in self.candidates),
            "synthetic_candidate_count": sum(c.synthetic for c in self.candidates),
            "blockers": [
                "monitored_contact_not_supplied",
                "explicit_discovery_approval_required",
                "explicit_collection_approval_required",
                "endpoint_access_review_required",
            ],
            "candidates": [
                {
                    "qid": c.qid,
                    "source_url": f"https://www.wikidata.org/wiki/{c.qid}",
                    "missing_fields": [
                        field
                        for field in (
                            "fragrance_name",
                            "brand_name",
                            "concentration",
                            "release_year",
                            "notes",
                            "accords",
                        )
                        if getattr(c, field) is None
                    ],
                    "blockers": c.blockers(),
                }
                for c in self.candidates
            ],
        }
