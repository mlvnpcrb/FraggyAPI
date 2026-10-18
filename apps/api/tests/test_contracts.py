import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fraggy_api.contracts import FieldClaimInput, SourceRecordInput
from pydantic import ValidationError


def test_retention_contract_rejects_unlicensed_payload_and_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        SourceRecordInput(
            source_id=uuid4(),
            source_record_id="x",
            collected_at=datetime.now(UTC),
            payload={"name": "public does not mean permitted"},
        )
    with pytest.raises(ValidationError):
        SourceRecordInput(
            source_id=uuid4(), source_record_id="x", collected_at=datetime(2026, 1, 1)
        )
    assert (
        SourceRecordInput(
            source_id=uuid4(), source_record_id="x", collected_at=datetime.now(UTC)
        ).payload
        is None
    )


def test_claim_contract_unknowns_confidence_and_rights() -> None:
    claim = FieldClaimInput(
        entity_link_id=uuid4(),
        field_path="release_year",
        value_state="unknown",
        collected_at=datetime.now(UTC),
    )
    assert claim.value is None and claim.confidence is None
    for changes in [
        {"confidence": Decimal("1.5")},
        {"value": 2020},
        {"usage_rights_status": "approved"},
        {"field_path": " "},
    ]:
        with pytest.raises(ValidationError):
            FieldClaimInput.model_validate({**claim.model_dump(), **changes})


@pytest.mark.parametrize(
    "environment,extra_args",
    [("development", []), ("production", ["--allow-demo-data"])],
)
def test_demo_cli_refuses_implicit_or_production_seed(
    environment: str, extra_args: list[str]
) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "fraggy_api.seed", *extra_args],
        env={**os.environ, "APP_ENV": environment},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "Refusing seed" in result.stderr


def test_redistribution_permission_requires_separate_evidence() -> None:
    base = dict(
        source_id=uuid4(), source_record_id="synthetic", collected_at=datetime.now(UTC)
    )
    with pytest.raises(ValidationError):
        SourceRecordInput(**base, redistribution_status="approved")
    record = SourceRecordInput(
        **base,
        redistribution_status="approved",
        redistribution_evidence="review-reference-001",
    )
    assert record.storage_status == "pending_review" and record.payload is None
