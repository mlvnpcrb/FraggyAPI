from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fraggy_api.database import Base, get_session
from fraggy_api.importing.authorization import review_source, revoke
from fraggy_api.importing.formats import (
    ImportErrorSafe,
    Manifest,
    Record,
    manifest_file,
    parse_file,
)
from fraggy_api.importing.matching import candidates
from fraggy_api.importing.pipeline import decide, preview, publish, stage
from fraggy_api.main import create_app
from fraggy_api.models import (
    Brand,
    DataReviewQueue,
    DataSource,
    FieldProvenance,
    Fragrance,
    FragranceRelease,
    Note,
    NoteAlias,
    SourceRecord,
)
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

EXAMPLES = Path(__file__).resolve().parents[3] / "data/examples"
PUBLIC_FIELDS = [
    "name",
    "slug",
    "brand_id",
    "fragrance_id",
    "concentration",
    "release_year",
    "notes",
    "accords",
]


@pytest.fixture
def manifest() -> Manifest:
    # Invented test policy only. No real-world license approval is asserted.
    return manifest_file(EXAMPLES / "source-manifest.json").model_copy(
        update={"synthetic": False}
    )


@pytest.fixture
def record() -> Record:
    return parse_file(EXAMPLES / "fragrances.json")[0]


async def authorize(session: AsyncSession, manifest: Manifest) -> None:
    await review_source(
        session,
        manifest,
        "test-operator",
        "Reviewed invented test evidence",
        allow_storage=True,
        publish_fields=PUBLIC_FIELDS,
    )


async def review_id(session: AsyncSession, record_id: str) -> UUID:
    result = await session.scalar(
        select(DataReviewQueue.id).where(
            DataReviewQueue.source_record_id == UUID(record_id),
            DataReviewQueue.status == "pending",
        )
    )
    assert result is not None
    return result


async def public(
    session: AsyncSession, *, demo: bool = False, production: bool = False
) -> dict:
    app = create_app(
        Settings(
            app_env="production" if production else "test",
            catalog_include_synthetic=demo,
        )
    )
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/fragrances")
        assert response.status_code == 200, response.text
        return response.json()


async def counts(session: AsyncSession) -> dict:
    return {
        table.name: await session.scalar(select(func.count()).select_from(table))
        for table in Base.metadata.sorted_tables
    }


async def new_release(
    session: AsyncSession, manifest: Manifest, record: Record
) -> tuple[dict, dict]:
    result = await stage(session, [record], manifest)
    decision = await decide(
        session,
        await review_id(session, result["records"][0]),
        "approve_new",
        "operator",
        "Original fictional record reviewed",
    )
    return result, decision


async def test_complete_authorized_workflow_and_revocation(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    result, decision = await new_release(session, manifest, record)
    assert result["inserted"] == result["review_required"] == 1
    assert (await public(session))["data"] == []
    identity = UUID(result["records"][0])
    await publish(
        session,
        identity,
        PUBLIC_FIELDS,
        "publisher",
        "Verified field redistribution evidence",
    )
    body = await public(session)
    assert body["pagination"]["total"] == 1
    assert body["data"][0]["releases"][0]["concentration"] == "eau_de_parfum"
    assert len(body["data"][0]["releases"][0]["notes"]) == 4
    assert "payload" not in str(body) and "evidence" not in str(body)
    fragrance_id = body["data"][0]["id"]
    await revoke(
        session, manifest.source_id, "publisher", "Withdraw publication permission"
    )
    assert (await public(session))["data"] == []
    await authorize(session, manifest)
    assert (await public(session))[
        "data"
    ] == []  # Source re-review cannot resurrect grants.
    await publish(
        session,
        identity,
        PUBLIC_FIELDS,
        "publisher",
        "Separate renewed record approval",
    )
    assert (await public(session))["data"][0]["id"] == fragrance_id
    again = await stage(session, [record], manifest)
    assert again["skipped"] == 1 and again["inserted"] == 0
    assert await session.scalar(select(func.count()).select_from(FragranceRelease)) == 1
    assert (
        await session.get(FragranceRelease, UUID(decision["release_id"]))
    ).id == UUID(decision["release_id"])
    source = await session.scalar(
        select(DataSource).where(DataSource.key == manifest.source_id)
    )
    assert source is not None and not source.enabled


async def test_unverified_flag_quarantines_without_payload(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    # Manifest says approved/storage/redistribution, but has no trusted DB review.
    before = await counts(session)
    dry = await preview(session, [record], manifest)
    assert dry["rows"][0]["classification"] == "rights_review_required"
    assert await counts(session) == before
    result = await stage(session, [record], manifest)
    assert result["quarantined"] == 1
    snapshot = await session.get(SourceRecord, UUID(result["records"][0]))
    assert (
        snapshot is not None
        and snapshot.payload is None
        and snapshot.source_url is None
    )
    assert record.source_record_id not in snapshot.source_record_id
    assert record.fragrance_name not in str(snapshot.__dict__)
    with pytest.raises(ImportErrorSafe):
        await decide(
            session,
            await review_id(session, result["records"][0]),
            "approve_new",
            "operator",
            "Flag is not authorization",
        )
    assert (await public(session))["data"] == []


async def test_dry_run_and_batch_rollback(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    before = await counts(session)
    dry = await preview(session, [record], manifest)
    assert dry["rows"][0]["classification"] == "new_fragrance"
    assert await counts(session) == before
    restricted = manifest.model_copy(
        update={
            "permitted_fields": [
                f for f in manifest.permitted_fields if f != "source_url"
            ]
        }
    )
    await authorize(session, restricted)
    before = await counts(session)
    bad = record.model_copy(
        update={
            "source_record_id": "second",
            "source_url": "https://example.invalid/not-permitted",
        }
    )
    with pytest.raises(ImportErrorSafe):
        async with session.begin_nested():
            # Nested transaction proves that a late second-row policy error rolls back
            # the first snapshot, its queue item and the ingestion run together.
            await stage(session, [record, bad], restricted)
    assert await counts(session) == before


async def test_changed_manifest_is_not_authority(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    changed = manifest.model_copy(update={"provider": "Different provider"})
    assert (await preview(session, [record], changed))["rows"][0][
        "classification"
    ] == "rights_review_required"
    result = await stage(session, [record], changed)
    assert result["quarantined"] == 1


@pytest.mark.parametrize("decision", ["defer", "reject"])
async def test_reject_defer_are_auditable(
    session: AsyncSession, manifest: Manifest, record: Record, decision: str
) -> None:
    await authorize(session, manifest)
    result = await stage(session, [record], manifest)
    item_id = await review_id(session, result["records"][0])
    await decide(session, item_id, decision, "operator-a", "Human decision reason")
    item = await session.get(DataReviewQueue, item_id)
    assert (
        item is not None
        and item.reviewer == "operator-a"
        and item.resolved_at is not None
    )
    assert item.context["history"][-1]["decision"] == decision
    assert item.status == ("pending" if decision == "defer" else "dismissed")
    assert await session.scalar(select(func.count()).select_from(Fragrance)) == 0
    if decision == "reject":
        with pytest.raises(ImportErrorSafe):
            await decide(
                session, item_id, "approve_new", "other", "Cannot overwrite review"
            )


async def test_matching_and_separate_concentrations(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    _, original = await new_release(session, manifest, record)
    assert (await candidates(session, record))[
        "classification"
    ] == "exact_identity_match"
    edt = record.model_copy(update={"source_record_id": "edt", "concentration": "EDT"})
    match = await candidates(session, edt)
    assert (
        match["classification"] == "possible_duplicate"
        and "different_or_unknown_concentration" in match["reasons"]
    )
    result = await stage(session, [edt], manifest)
    item = await review_id(session, result["records"][0])
    with pytest.raises(ImportErrorSafe):
        async with session.begin_nested():
            await decide(
                session,
                item,
                "link_existing",
                "operator",
                "Cannot merge EDT and EDP",
                UUID(original["release_id"]),
            )
    separate = await decide(
        session,
        item,
        "separate_release",
        "operator",
        "Keep the EDT as its own release",
        UUID(original["release_id"]),
    )
    releases = (
        await session.scalars(select(FragranceRelease).order_by(FragranceRelease.id))
    ).all()
    assert len(releases) == 2 and len({r.fragrance_id for r in releases}) == 1
    assert {r.concentration for r in releases} == {"eau_de_toilette", "eau_de_parfum"}
    assert separate["release_id"] != original["release_id"]


async def test_aliases_and_conflicting_claims_do_not_overwrite(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    _, original = await new_release(session, manifest, record)
    alias = record.model_copy(
        update={
            "source_record_id": "alias",
            "brand_name": record.brand_aliases[0],
            "release_year": None,
        }
    )
    match = await candidates(session, alias)
    assert match["classification"] == "possible_duplicate"
    result = await stage(session, [alias], manifest)
    await decide(
        session,
        await review_id(session, result["records"][0]),
        "link_existing",
        "operator",
        "Confirmed same release with missing year",
        UUID(original["release_id"]),
    )
    assert await session.scalar(select(func.count()).select_from(FragranceRelease)) == 1
    release = await session.get(FragranceRelease, UUID(original["release_id"]))
    assert release is not None and release.release_year == 2024
    assert (
        await session.scalar(
            select(func.count())
            .select_from(FieldProvenance)
            .where(FieldProvenance.value_state == "conflicting")
        )
        >= 1
    )
    assert await session.scalar(select(func.count()).select_from(Brand)) == 1


async def test_revised_source_record_preserves_history(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    result, _ = await new_release(session, manifest, record)
    changed = record.model_copy(update={"release_year": 2025})
    revised = await stage(session, [changed], manifest)
    assert revised["inserted"] == 1 and revised["records"][0] != result["records"][0]
    rows = (
        await session.scalars(select(SourceRecord).order_by(SourceRecord.revision))
    ).all()
    assert [r.revision for r in rows] == [1, 2]
    assert rows[0].payload["original"]["release_year"] == 2024
    assert await session.scalar(select(func.count()).select_from(FragranceRelease)) == 1


async def test_synthetic_import_is_never_public_in_production(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    manifest = manifest.model_copy(update={"synthetic": True})
    await authorize(session, manifest)
    result, _ = await new_release(session, manifest, record)
    await publish(
        session,
        UUID(result["records"][0]),
        PUBLIC_FIELDS,
        "operator",
        "Fictional demo only",
    )
    assert (await public(session))["data"] == []
    demo = await public(session, demo=True)
    assert demo["data"][0]["synthetic"] is True
    assert (await public(session, demo=True, production=True))["data"] == []


async def test_ambiguous_note_rolls_back_canonical_review(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    result = await stage(session, [record], manifest)
    for i in range(2):
        note = Note(id=uuid4(), name=f"Other note {i}", slug=f"other-note-{i}")
        session.add(note)
        await session.flush()
        session.add(NoteAlias(note_id=note.id, name="Bergamot"))
    await session.flush()
    before = await counts(session)
    with pytest.raises(ImportErrorSafe):
        async with session.begin_nested():
            await decide(
                session,
                await review_id(session, result["records"][0]),
                "approve_new",
                "operator",
                "Ambiguous alias must be reviewed",
            )
    assert await counts(session) == before


@pytest.mark.parametrize(
    "case", ["storage", "attribution", "fields", "website", "actor"]
)
async def test_source_authorization_guards(
    session: AsyncSession, manifest: Manifest, case: str
) -> None:
    updates = {
        "storage": {"storage_permissions": False},
        "attribution": {"attribution_requirements": ["Must display provider credit"]},
        "fields": {"permitted_fields": []},
        "website": {"source_id": "fragrantica"},
    }
    manifest = manifest.model_copy(update=updates.get(case, {}))
    with pytest.raises(ImportErrorSafe):
        await review_source(
            session,
            manifest,
            "" if case == "actor" else "operator",
            "Review reason",
            allow_storage=True,
            publish_fields=PUBLIC_FIELDS,
        )


async def test_publication_needs_record_and_source_review(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    result = await stage(session, [record], manifest)
    with pytest.raises(ImportErrorSafe):
        await publish(
            session,
            UUID(result["records"][0]),
            PUBLIC_FIELDS,
            "operator",
            "Not reviewed yet",
        )
    await decide(
        session,
        await review_id(session, result["records"][0]),
        "approve_new",
        "operator",
        "Review record",
    )
    with pytest.raises(ImportErrorSafe):
        await publish(
            session,
            UUID(result["records"][0]),
            ["payload"],
            "operator",
            "Not an allowed publication field",
        )


async def test_identifiers_sizes_and_flankers_require_review(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    record = record.model_copy(update={"gtin": "12345670"})
    _, original = await new_release(session, manifest, record)
    assert (await candidates(session, record))[
        "classification"
    ] == "exact_identity_match"
    for modified in [
        record.model_copy(update={"bottle_sizes_ml": [100]}),
        record.model_copy(update={"fragrance_name": "Papier Nuit Flanker"}),
    ]:
        result = await candidates(session, modified)
        assert result["classification"] == "conflict_requiring_review"
        assert result["automatic_merge"] is False
    flanker = record.model_copy(
        update={"source_record_id": "flanker", "fragrance_name": "Papier Nuit Flanker"}
    )
    result = await stage(session, [flanker], manifest)
    with pytest.raises(ImportErrorSafe):
        await decide(
            session,
            await review_id(session, result["records"][0]),
            "link_existing",
            "operator",
            "Do not merge flankers",
            UUID(original["release_id"]),
        )


async def test_note_aliases_and_duplicate_identity_candidates(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await authorize(session, manifest)
    await new_release(session, manifest, record)
    repeated = record.model_copy(update={"source_record_id": "another-source-record"})
    await new_release(session, manifest, repeated)
    match = await candidates(session, record)
    assert (
        match["classification"] == "possible_duplicate"
        and len(match["release_ids"]) == 2
    )
    assert match == await candidates(session, record)
    assert await session.scalar(select(func.count()).select_from(Note)) == 4
    incoming_notes = [
        n.model_copy(update={"name": "Cedar wood"}) if n.name == "Cedar" else n
        for n in record.notes
    ]
    alias_record = record.model_copy(
        update={"source_record_id": "note-alias", "notes": incoming_notes}
    )
    await new_release(session, manifest, alias_record)
    assert await session.scalar(select(func.count()).select_from(Note)) == 4


async def test_storage_only_and_storage_withdrawal(
    session: AsyncSession, manifest: Manifest, record: Record
) -> None:
    await review_source(
        session,
        manifest,
        "operator",
        "Private storage reviewed only",
        allow_storage=True,
        publish_fields=[],
    )
    result, _ = await new_release(session, manifest, record)
    identity = UUID(result["records"][0])
    with pytest.raises(ImportErrorSafe):
        await publish(
            session,
            identity,
            PUBLIC_FIELDS,
            "operator",
            "Storage does not authorize publication",
        )
    await review_source(
        session,
        manifest,
        "operator",
        "Withdraw raw snapshot storage",
        allow_storage=False,
        publish_fields=[],
    )
    snapshot = await session.get(SourceRecord, identity)
    assert (
        snapshot is not None
        and snapshot.payload is None
        and snapshot.storage_status == "restricted"
    )
    assert (await public(session))["data"] == []
