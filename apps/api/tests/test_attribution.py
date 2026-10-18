"""Fictional policies only; real PostgreSQL exercises every publication boundary."""

from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from fraggy_api.attribution import Attribution
from fraggy_api.database import get_session
from fraggy_api.importing.authorization import review_source, revoke
from fraggy_api.importing.formats import (
    ImportErrorSafe,
    Manifest,
    Record,
    manifest_file,
    parse_file,
)
from fraggy_api.importing.pipeline import decide, preview, publish, stage, unpublish
from fraggy_api.main import create_app
from fraggy_api.models import (
    DataReviewQueue,
    DataSource,
    FragranceRelease,
)
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from test_import_pipeline import PUBLIC_FIELDS, new_release, public, review_id

EXAMPLES = Path(__file__).resolve().parents[3] / "data/examples"


def credit(**changes: object) -> Attribution:
    return Attribution.model_validate(
        {
            "provider": "FraggyAPI fictional workshop",
            "text": "Original invented fragrance metadata courtesy of Fictional Workshop.",
            "source_url": "https://example.invalid/workshop",
            "license_name": "Fictional pilot permission — not a real license",
            "license_url": "https://example.invalid/fictional-permission",
            "copyright_holder": "Fictional Workshop",
            "placement": "adjacent_record",
            "modification_disclosure_required": True,
            "modification_disclosure": "Names normalized; records matched and projected by FraggyAPI.",
            "last_verified": date.today().isoformat(),
            **changes,
        }
    )


@pytest.fixture
def licensed_manifest() -> Manifest:
    return manifest_file(EXAMPLES / "source-manifest.json").model_copy(
        update={
            "synthetic": False,
            "attribution_requirements": ["Display provider credit beside every record"],
            "attribution": credit(),
        }
    )


@pytest.fixture
def fictional_record() -> Record:
    return parse_file(EXAMPLES / "fragrances.json")[0]


async def authorize(session: AsyncSession, manifest: Manifest) -> DataSource:
    return await review_source(
        session,
        manifest,
        "private-reviewer",
        "PRIVATE_LEGAL_NOTE",
        allow_storage=True,
        publish_fields=PUBLIC_FIELDS,
        accept_attribution=True,
    )


async def pilot(
    session: AsyncSession, manifest: Manifest, record: Record
) -> tuple[UUID, UUID]:
    await authorize(session, manifest)
    assert (await preview(session, [record], manifest))["canonical_writes"] == 0
    staged, decision = await new_release(session, manifest, record)
    identity = UUID(staged["records"][0])
    assert (await public(session))["data"] == []
    await publish(
        session, identity, PUBLIC_FIELDS, "private-publisher", "PRIVATE_FIELD_NOTE"
    )
    return identity, UUID(decision["release_id"])


async def test_attribution_pilot_all_seven_endpoints_and_privacy(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, _ = await pilot(session, licensed_manifest, fictional_record)
    data = (await public(session))["data"][0]
    attrs = data["attributions"]
    assert len(attrs) == 1
    assert attrs[0]["provider"] == licensed_manifest.provider
    assert "/name" in attrs[0]["fields"] and "/brand/name" in attrs[0]["fields"]
    assert "/releases/0/concentration" in attrs[0]["fields"]
    assert any(p.startswith("/releases/0/notes/") for p in attrs[0]["fields"])
    assert data["brand"]["attributions"][0]["fields"] == ["/name", "/slug"]
    app = create_app(Settings(app_env="test"))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for path in [
            "/brands",
            "/brands/" + data["brand"]["slug"],
            "/fragrances",
            "/fragrances/search?q=Papier",
            "/fragrances/" + data["id"],
            "/notes",
            "/accords",
        ]:
            response = await client.get("/api/v1" + path)
            assert response.status_code == 200, response.text
            body = response.json()["data"]
            entries = body if isinstance(body, list) else [body]
            assert entries and all(e["attributions"] for e in entries)
            for private in [
                "PRIVATE_LEGAL_NOTE",
                "PRIVATE_FIELD_NOTE",
                "private-reviewer",
                "private-publisher",
                str(identity),
                "manifest_digest",
                "source_record_id",
                "rights_evidence",
                "transformation_history",
            ]:
                assert private not in response.text
    await revoke(
        session, licensed_manifest.source_id, "operator", "Pilot permission withdrawn"
    )
    assert (await public(session))["data"] == []


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "data:text/html,x",
        "//example.com",
        "http://example.com",
        "https://user:pass@example.com",
        "https://example.com/?token=x",
        "https://localhost",
        "https://127.0.0.1",
        "https://example.com\\@evil.com",
        "https://example.com/\nfoo",
        "https://example.com:99",
        "https://host.local",
    ],
)
def test_unsafe_attribution_urls_rejected(url: str) -> None:
    for field in ("source_url", "license_url"):
        with pytest.raises(ValueError):
            credit(**{field: url})


@pytest.mark.parametrize(
    "changes",
    [
        {"text": ""},
        {"provider": " "},
        {"text": "hidden\x00"},
        {"license_name": ""},
        {"source_url": ""},
    ],
)
def test_missing_metadata_rejected(changes: dict) -> None:
    with pytest.raises(ValueError):
        credit(**changes)


@pytest.mark.parametrize(
    "case",
    [
        "acceptance",
        "missing",
        "placement",
        "conditions",
        "source_conditions",
        "modifications",
        "provider",
        "expired",
        "future",
        "storage",
        "redistribution",
    ],
)
async def test_unsupported_or_unreviewed_obligations_block_publication(
    session: AsyncSession, licensed_manifest: Manifest, case: str
) -> None:
    updates = {
        "missing": {"attribution": None},
        "placement": {"attribution": credit(placement="global_footer")},
        "conditions": {
            "attribution": credit(
                redistribution_conditions=["Unknown downstream restriction"]
            )
        },
        "source_conditions": {
            "redistribution_conditions": ["Additional written permission required"]
        },
        "modifications": {"attribution": credit(modification_disclosure=None)},
        "provider": {"provider": "Other provider"},
        "expired": {
            "attribution": credit(
                last_verified=(date.today() - timedelta(days=366)).isoformat()
            )
        },
        "future": {
            "attribution": credit(
                last_verified=(date.today() + timedelta(days=1)).isoformat()
            )
        },
        "storage": {"storage_permissions": False},
        "redistribution": {"redistribution_permissions": False},
    }
    manifest = licensed_manifest.model_copy(update=updates.get(case, {}))
    with pytest.raises(ImportErrorSafe):
        await review_source(
            session,
            manifest,
            "operator",
            "Must fail closed",
            allow_storage=True,
            publish_fields=PUBLIC_FIELDS,
            accept_attribution=case != "acceptance",
        )


async def test_multiple_sources_and_field_specific_credits(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, release = await pilot(session, licensed_manifest, fictional_record)
    # Second invented provider supplies only concentration. It cannot take credit
    # for brand/name/notes merely because the canonical line already exists.
    second = licensed_manifest.model_copy(
        update={
            "source_id": "fictional-second-provider",
            "provider": "Second Fictional Provider",
            "attribution": credit(
                provider="Second Fictional Provider",
                text="Concentration supplied by Second Fictional Provider.",
            ),
        }
    )
    await authorize(session, second)
    staged = await stage(session, [fictional_record], second)
    await decide(
        session,
        await review_id(session, staged["records"][0]),
        "link_existing",
        "operator",
        "Same fictional release independently verified",
        release,
    )
    await publish(
        session,
        UUID(staged["records"][0]),
        ["concentration"],
        "operator",
        "Only concentration authorized for this record",
    )
    data = (await public(session))["data"][0]
    assert len(data["attributions"]) == 2
    second_credit = next(
        a for a in data["attributions"] if a["provider"] == second.provider
    )
    assert second_credit["fields"] == ["/releases/0/concentration"]
    assert len(data["brand"]["attributions"]) == 1
    await unpublish(
        session,
        identity,
        ["concentration"],
        "operator",
        "Withdraw first provider field",
    )
    data = (await public(session))["data"][0]
    assert data["releases"][0]["concentration"] == "eau_de_parfum"
    first_credit = next(
        a for a in data["attributions"] if a["provider"] == licensed_manifest.provider
    )
    assert "/releases/0/concentration" not in first_credit["fields"]
    await revoke(session, second.source_id, "operator", "Withdraw second provider")
    data = (await public(session))["data"][0]
    assert data["releases"][0]["concentration"] is None
    assert len(data["attributions"]) == 1


async def test_identical_public_credits_deduplicate_across_sources(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    _, release = await pilot(session, licensed_manifest, fictional_record)
    second = licensed_manifest.model_copy(
        update={"source_id": "fictional-second-archive"}
    )
    await authorize(session, second)
    staged = await stage(session, [fictional_record], second)
    await decide(
        session,
        await review_id(session, staged["records"][0]),
        "link_existing",
        "operator",
        "Same release",
        release,
    )
    await publish(
        session,
        UUID(staged["records"][0]),
        ["name", "slug", "brand_id", "fragrance_id", "concentration"],
        "operator",
        "Reviewed fields",
    )
    data = (await public(session))["data"][0]
    assert len(data["attributions"]) == 1
    assert len(data["attributions"][0]["fields"]) == len(
        set(data["attributions"][0]["fields"])
    )
    await revoke(
        session, licensed_manifest.source_id, "operator", "First archive revoked"
    )
    assert len((await public(session))["data"][0]["attributions"]) == 1


async def test_license_changes_invalidate_old_grants(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, release = await pilot(session, licensed_manifest, fictional_record)
    changed = licensed_manifest.model_copy(
        update={"attribution": credit(license_name="Revised fictional permission")}
    )
    await authorize(session, changed)
    assert (await public(session))["data"] == []
    with pytest.raises(ImportErrorSafe):
        await publish(
            session,
            identity,
            PUBLIC_FIELDS,
            "operator",
            "Old digest cannot be republished",
        )
    staged = await stage(session, [fictional_record], changed)
    await decide(
        session,
        await review_id(session, staged["records"][0]),
        "link_existing",
        "operator",
        "Revalidate snapshot under new permission",
        release,
    )
    await publish(
        session,
        UUID(staged["records"][0]),
        PUBLIC_FIELDS,
        "operator",
        "New field approval",
    )
    assert (await public(session))["data"][0]["attributions"][0][
        "license_name"
    ] == "Revised fictional permission"


async def test_stale_claim_cannot_be_republished_or_attributed(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, release_id = await pilot(session, licensed_manifest, fictional_record)
    release = await session.get(FragranceRelease, release_id)
    assert release is not None
    release.release_year = 2025
    await session.flush()
    with pytest.raises(ImportErrorSafe, match="Stale canonical"):
        await publish(
            session,
            identity,
            ["release_year"],
            "operator",
            "Value changed after review",
        )
    data = (await public(session))["data"][0]
    assert data["releases"][0]["release_year"] is None
    assert "/releases/0/release_year" not in data["attributions"][0]["fields"]


async def test_invalid_db_policy_never_silently_drops_required_credit(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    await pilot(session, licensed_manifest, fictional_record)
    source = await session.scalar(
        select(DataSource).where(DataSource.key == licensed_manifest.source_id)
    )
    assert source is not None
    events = [dict(e) for e in source.evidence]
    events[-1]["attribution_accepted"] = False
    source.evidence = events
    await session.flush()
    assert (await public(session))["data"] == []


async def test_field_revocation_removes_credit_and_preserves_other_fields(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, _ = await pilot(session, licensed_manifest, fictional_record)
    await unpublish(
        session, identity, ["release_year"], "operator", "Withdraw only year"
    )
    body = (await public(session))["data"][0]
    assert body["releases"][0]["release_year"] is None
    assert body["releases"][0]["concentration"] == "eau_de_parfum"
    assert "/releases/0/release_year" not in body["attributions"][0]["fields"]
    audit = await session.scalar(
        select(DataReviewQueue).where(
            DataReviewQueue.source_record_id == identity,
            DataReviewQueue.reason == "Field publication revoked",
        )
    )
    assert audit is not None and audit.context["decision"] == "unpublish"


async def test_synthetic_attribution_never_reaches_production(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    synthetic = licensed_manifest.model_copy(update={"synthetic": True})
    await pilot(session, synthetic, fictional_record)
    assert (await public(session))["data"] == []
    assert (await public(session, demo=True))["data"][0]["attributions"]
    assert (await public(session, demo=True, production=True))["data"] == []


async def test_attributed_query_count_is_constant(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    from sqlalchemy import event

    await pilot(session, licensed_manifest, fictional_record)
    app = create_app(Settings(app_env="test"))
    app.dependency_overrides[get_session] = lambda: session
    statements: list[str] = []

    def count(*args: object) -> None:
        statements.append(str(args[2]))

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", count)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            for limit in (1, 50):
                statements.clear()
                response = await client.get(f"/api/v1/fragrances?limit={limit}")
                assert response.status_code == 200
                assert len(statements) == 7
    finally:
        event.remove(bind, "before_cursor_execute", count)


async def test_credit_overflow_never_returns_incomplete_attribution(
    session: AsyncSession,
    licensed_manifest: Manifest,
    fictional_record: Record,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fraggy_api.public_credits as credits

    await pilot(session, licensed_manifest, fictional_record)
    monkeypatch.setattr(credits, "MAX_CREDIT_CLAIMS", 1)
    app = create_app(Settings(app_env="test"))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/fragrances")
        assert response.status_code == 503
        assert "data" not in response.json()


async def test_old_manifest_digest_and_unattributed_api_remain_compatible(
    session: AsyncSession, fictional_record: Record
) -> None:
    import json

    from fraggy_api.importing.formats import digest

    path = EXAMPLES / "source-manifest.json"
    original = json.loads(path.read_text())
    manifest = manifest_file(path)
    assert digest(manifest.model_dump(mode="json")) == digest(original)
    manifest = manifest.model_copy(update={"synthetic": False})
    await authorize(session, manifest)
    staged, _ = await new_release(session, manifest, fictional_record)
    await publish(
        session,
        UUID(staged["records"][0]),
        PUBLIC_FIELDS,
        "operator",
        "No attribution required in this invented policy",
    )
    body = (await public(session))["data"][0]
    assert body["name"] == fictional_record.fragrance_name
    assert body["attributions"] == []
    assert body["brand"]["attributions"] == []
    assert body["releases"][0]["attributions"] == []
