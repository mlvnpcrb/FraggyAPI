"""Independent source capabilities. Registration never grants network access."""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ..importing.formats import Record, digest
from .offline_sources import ADAPTERS, FixturePage
from .openbeautyfacts import parse_search
from .policy import CollectionError


@dataclass(frozen=True)
class Provider:
    key: str
    capabilities: tuple[str, ...]
    contract: str
    live_enabled: bool = False

    def parse(self, body: bytes, at: datetime) -> dict[str, Any]:
        if self.key == "openbeautyfacts":
            return parse_search(body, collected_at=at)
        if self.key in ADAPTERS:
            page = FixturePage.model_validate_json(body)
            records = ADAPTERS[self.key].parse(page)
            return {
                "source": self.key,
                "observations": [
                    {
                        "raw": page.payload,
                        "proposed_record": record.model_dump(mode="json"),
                        "source_record_id": record.source_record_id,
                        "collected_at": at.isoformat(),
                        "usage_rights": "fixture_only",
                        "publication_authorized": False,
                    }
                    for record in records
                ],
            }
        raise CollectionError("provider_contract_not_verified")


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from ..importing.formats import Manifest

PROVIDERS = {
    provider.key: provider
    for provider in (
        Provider(
            "openbeautyfacts",
            ("category_filter", "barcode_lookup"),
            "official_documented_offline",
        ),
        Provider("fragrantica", (), "fictional_fixture_only"),
        Provider("parfumo", (), "fictional_fixture_only"),
        Provider("wikidata", ("reviewed_entity_ids",), "structured_sparql"),
        Provider("official_brand", (), "provider_specific_feed_required"),
        *(
            Provider(key, (), "unverified_skeleton")
            for key in (
                "basenotes",
                "wikiparfum",
                "perfume_society",
                "perfumemaster",
                "scentbase",
            )
        ),
    )
}


def records_for_review(
    provider: str, body: bytes, at: datetime
) -> tuple[dict[str, Any], list[Record]]:
    """Offline extraction only; neither parsing nor a valid schema approves rights."""
    definition = PROVIDERS.get(provider)
    if definition is None:
        raise CollectionError("provider_not_registered")
    report = definition.parse(body, at)
    return report, [
        Record.model_validate(row["proposed_record"])
        for row in report["observations"]
        if row["proposed_record"] is not None
    ]


async def stage_provider_page(
    session: "AsyncSession",
    provider: str,
    body: bytes,
    at: datetime,
    manifest: "Manifest",
) -> dict[str, Any]:
    """Explicit local staging; raw observations require an existing storage grant.

    No requests, publication, canonical writes or source approval. Live collection
    remains unavailable; this is also used for original local contract validation.
    """
    from ..importing.authorization import check_storage, source_for
    from ..importing.pipeline import stage
    from ..models import SourceRecord

    report, records = records_for_review(provider, body, at)
    if manifest.source_id != provider:
        raise CollectionError("provider_manifest_mismatch")
    source = await source_for(session, manifest, create=False)
    if source is None or any(
        not check_storage(source, manifest, row) for row in records
    ):
        raise CollectionError("provider_storage_not_authorized")
    observations = [
        row for row in report["observations"] if row["proposed_record"] is not None
    ]
    records = [
        Record.model_validate(
            {
                **record.model_dump(mode="json"),
                "source_metadata": {
                    **record.source_metadata,
                    "source_observation_digest": digest(row["raw"]),
                },
            }
        )
        for record, row in zip(records, observations, strict=True)
    ]
    # This additional metadata must itself fall within explicitly reviewed fields.
    if any(not check_storage(source, manifest, row) for row in records):
        raise CollectionError("provider_storage_not_authorized")
    raw_fields = {
        "source_observation." + field for row in observations for field in row["raw"]
    }
    if not raw_fields <= set(manifest.permitted_fields):
        raise CollectionError("provider_raw_fields_not_authorized")
    summary = await stage(session, records, manifest)
    summary["unmapped_observations"] = len(report["observations"]) - len(records)
    # Stage's row locks/rights checks/idempotent revisions remain authoritative.
    for row, identity in zip(
        (r for r in report["observations"] if r["proposed_record"] is not None),
        summary["records"],
        strict=True,
    ):
        from uuid import UUID

        snapshot = await session.get(SourceRecord, UUID(identity))
        assert snapshot is not None and snapshot.payload
        if "source_observation" not in snapshot.payload:
            snapshot.payload = {**snapshot.payload, "source_observation": row}
    return summary
