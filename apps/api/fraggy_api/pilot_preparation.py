"""Phase 2J offline rehearsal. No transport, database, activation or publication."""

import json
from datetime import date
from typing import Any

from pydantic import Field, model_validator

from .collection.policy import CollectionError, Endpoint
from .collection.quality import assess
from .collection.wikidata import PAGE_SIZE, records
from .importing.formats import digest, key
from .pilot_readiness import PilotProposal


class PilotPlan(PilotProposal):
    quantity: int = Field(default=25, ge=20, le=50)

    @model_validator(mode="after")
    def bounded_candidates(self) -> "PilotPlan":
        if len(self.candidates) > self.quantity:
            raise ValueError("Candidate count exceeds pilot scope")
        return self

    def report(self) -> dict[str, object]:
        result = super().report()
        raw_blockers = result["blockers"]
        assert isinstance(raw_blockers, list)
        blockers = [str(value) for value in raw_blockers]
        if len(self.candidates) != self.quantity:
            blockers.append("exact_reviewed_candidate_list_required")
        if any(c.blockers() for c in self.candidates):
            blockers.append("candidate_review_incomplete")
        if any(
            c.verified_on and (date.today() - c.verified_on).days > 30
            for c in self.candidates
        ):
            blockers.append("candidate_review_expired")
        return {
            **result,
            "quantity": self.quantity,
            "blockers": blockers,
            "collection_ready": False,
            "storage_approved": False,
            "publication_approved": False,
            "schedule_enabled": False,
            "images": 0,
            "collection_attempt_ceiling": ((self.quantity + 24) // 25) * 2,
            "discovery_attempt_ceiling": 2,
            "database_writes": 0,
        }


def fixture_endpoint(quantity: int) -> Endpoint:
    if not 20 <= quantity <= 50:
        raise CollectionError("pilot_quantity_out_of_bounds")
    return Endpoint(
        url="http://127.0.0.1:1",
        adapter="wikidata_sparql",
        entity_ids=[f"Q990000000{i:03d}" for i in range(quantity)],
        user_agent="FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; fixture@example.invalid)",
        minimum_interval_seconds=1,
        max_pages=(quantity + 24) // 25,
        max_records=quantity,
        retries=1,
    )


def fixture_pages(quantity: int) -> list[bytes]:
    config = fixture_endpoint(quantity)
    pages = []
    for offset in range(0, quantity, PAGE_SIZE):
        rows = []
        for index, identity in enumerate(
            config.entity_ids[offset : offset + PAGE_SIZE], start=offset
        ):
            rows.append(
                {
                    "item": {
                        "type": "uri",
                        "value": "http://www.wikidata.org/entity/" + identity,
                    },
                    "itemLabel": {
                        "type": "literal",
                        "xml:lang": "en",
                        "value": f"Invented{index:03d} Fictional Pilot",
                    },
                    "brand": {
                        "type": "uri",
                        "value": f"http://www.wikidata.org/entity/Q990000099{index % 5:03d}",
                    },
                    "brandLabel": {
                        "type": "literal",
                        "xml:lang": "en",
                        "value": f"Original Fictional House {index % 5}",
                    },
                }
            )
        pages.append(json.dumps({"results": {"bindings": rows}}).encode())
    return pages


def dry_run(plan: PilotPlan, pages: list[bytes] | None = None) -> dict[str, Any]:
    """Parse only local synthetic SPARQL fixtures through the existing adapter."""
    endpoint = fixture_endpoint(plan.quantity)
    bodies = fixture_pages(plan.quantity) if pages is None else pages
    if len(bodies) != endpoint.max_pages:
        raise CollectionError("pilot_fixture_page_count_mismatch")
    parsed = []
    cursor = None
    for body in bodies:
        batch, cursor = records(body, endpoint, cursor)
        parsed.extend(batch)
    if cursor is not None or len(parsed) != plan.quantity:
        raise CollectionError("pilot_fixture_incomplete")
    identities = [record.source_record_id for record in parsed]
    if len(set(identities)) != len(identities):
        raise CollectionError("pilot_duplicate_source_identity")
    quality = assess(parsed)
    return {
        "offline_only": True,
        "synthetic_only": True,
        "external_requests": 0,
        "database_writes": 0,
        "staged": 0,
        "published": 0,
        "scheduled": False,
        "images_collected": 0,
        "records_validated": len(parsed),
        "brands": len({key(record.brand_name) for record in parsed}),
        "pages_validated": len(bodies),
        "quality": quality,
        "idempotency_digest": digest([r.model_dump(mode="json") for r in parsed]),
        "provenance": {
            "source_record_ids": len(set(identities)),
            "source_urls": sum(bool(r.source_url) for r in parsed),
            "mapping": "wikidata_sparql_v1",
        },
        "rollback": "No persisted state; discard this report. Real pilot requires the documented source-revocation workflow.",
        "approval": plan.report(),
    }
