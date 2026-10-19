from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from fraggy_api.database import get_session
from fraggy_api.main import create_app
from fraggy_api.models import (
    Brand,
    DataSource,
    FieldProvenance,
    Fragrance,
    SourceEntityLink,
    SourceRecord,
)
from fraggy_api.seed import demo_id, seed_demo
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import event, update
from sqlalchemy.ext.asyncio import AsyncSession


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    await seed_demo(session, allow_demo_data=True, publish_demo_catalog=True)
    app = create_app(Settings(app_env="test", catalog_include_synthetic=True))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        yield http


async def test_catalog_and_detail(client: AsyncClient) -> None:
    response = await client.get("/api/v1/fragrances")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pagination"] == {"limit": 20, "offset": 0, "total": 4}
    assert all(item["synthetic"] for item in body["data"])
    paper = next(item for item in body["data"] if item["name"] == "Paper Horizon")
    assert len(paper["releases"]) == 3
    assert {release["concentration"] for release in paper["releases"]} == {
        "eau_de_parfum",
        "eau_de_toilette",
    }
    assert any(release["release_year"] is None for release in paper["releases"])
    assert (
        len(
            next(
                r for r in paper["releases"] if r["id"] == str(demo_id("release:edp"))
            )["notes"]
        )
        == 4
    )
    detail = await client.get(f"/api/v1/fragrances/{paper['id']}")
    assert detail.json()["data"] == paper
    assert set(paper) == {
        "attributions",
        "primary_image",
        "images",
        "id",
        "name",
        "slug",
        "synthetic",
        "brand",
        "releases",
        "releases_truncated",
    }
    for forbidden in [
        "description",
        "payload",
        "evidence",
        "source_url",
        "media",
        "reviewer",
        "version_metadata",
    ]:
        assert forbidden not in response.text


@pytest.mark.parametrize("path,total", [("brands", 2), ("notes", 4), ("accords", 1)])
async def test_lookups(client: AsyncClient, path: str, total: int) -> None:
    response = await client.get(f"/api/v1/{path}?limit=1")
    assert response.status_code == 200
    assert response.json()["pagination"]["total"] == total
    assert len(response.json()["data"]) == 1
    brand = await client.get("/api/v1/brands/nacre-workshop")
    assert brand.json()["data"]["id"] == str(demo_id("brand:1"))


@pytest.mark.parametrize(
    "query,total",
    [
        ("q=PAPER", 1),
        ("q=nacre", 2),
        ("brand=morrow-grove", 2),
        ("concentration=eau_de_toilette&year=2020", 1),
        ("concentration=eau_de_toilette&year=2025", 0),
        (
            f"notes={demo_id('note:1')}&accords={demo_id('accord:1')}&concentration=eau_de_parfum",
            1,
        ),
        (f"notes={demo_id('note:1')}&concentration=eau_de_toilette", 0),
        ("q=no-such-fragrance", 0),
        ("q=%25", 0),
    ],
)
async def test_search_and_filters(client: AsyncClient, query: str, total: int) -> None:
    response = await client.get("/api/v1/fragrances?" + query)
    assert response.status_code == 200, response.text
    assert response.json()["pagination"]["total"] == total


async def test_exact_ranking_and_pagination(
    client: AsyncClient, session: AsyncSession
) -> None:
    # Grant the revised fixture name explicitly; an ORM edit alone is insufficient.
    await session.execute(
        update(Fragrance)
        .where(Fragrance.id == demo_id("fragrance:2"))
        .values(name="Paper Horizon Extended")
    )
    await session.execute(
        update(FieldProvenance)
        .where(
            FieldProvenance.id == demo_id(f"public-claim:{demo_id('fragrance:2')}:name")
        )
        .values(value="Paper Horizon Extended")
    )
    response = await client.get("/api/v1/fragrances/search?q=Paper%20Horizon&limit=1")
    assert response.status_code == 200, response.text
    assert response.json()["data"][0]["name"] == "Paper Horizon"
    assert response.json()["pagination"]["total"] == 2
    second = await client.get(
        "/api/v1/fragrances/search?q=Paper%20Horizon&limit=1&offset=1"
    )
    assert second.json()["data"][0]["name"] == "Paper Horizon Extended"
    empty = await client.get("/api/v1/fragrances?offset=10000")
    assert empty.json()["data"] == []
    ascending = (await client.get("/api/v1/fragrances?sort=name")).json()["data"]
    descending = (await client.get("/api/v1/fragrances?sort=name_desc")).json()["data"]
    assert [f["id"] for f in ascending] == [f["id"] for f in reversed(descending)]


@pytest.mark.parametrize(
    "query",
    [
        "limit=0",
        "limit=51",
        "offset=-1",
        "offset=10001",
        "year=999",
        "notes=invalid",
        "concentration=edp",
        "unexpected=yes",
        "sort=random",
        "q=" + "x" * 121,
    ],
)
async def test_invalid_inputs(client: AsyncClient, query: str) -> None:
    response = await client.get("/api/v1/fragrances?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "422"


async def test_errors(client: AsyncClient, session: AsyncSession) -> None:
    assert (await client.get("/api/v1/fragrances/search?q=%20")).status_code == 400
    assert (await client.get(f"/api/v1/fragrances/{uuid4()}")).status_code == 404
    assert (await client.get("/api/v1/fragrances/not-a-uuid")).status_code == 422
    assert (await client.get("/api/v1/brands/missing")).status_code == 404
    assert (await client.get("/api/v1/source-records")).status_code == 404


@pytest.mark.parametrize("env,demo", [("test", False), ("production", True)])
async def test_synthetic_visibility(
    session: AsyncSession, client: AsyncClient, env: str, demo: bool
) -> None:
    app = create_app(Settings(app_env=env, catalog_include_synthetic=demo))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        for path in ["fragrances", "brands", "notes", "accords"]:
            assert (await http.get(f"/api/v1/{path}")).json()["data"] == []
        assert (
            await http.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")
        ).status_code == 404


@pytest.mark.parametrize(
    "change", ["rights", "selection", "value", "record", "source", "link"]
)
async def test_fail_closed(
    client: AsyncClient, session: AsyncSession, change: str
) -> None:
    identity = demo_id("release:edt")
    claim = await session.get(
        FieldProvenance, demo_id(f"public-claim:{identity}:concentration")
    )
    assert claim is not None
    if change == "rights":
        claim.usage_rights_status = "pending_review"
    elif change == "selection":
        claim.selection_status = "candidate"
    elif change == "value":
        claim.value = "other"
    elif change == "record":
        await session.execute(
            update(SourceRecord)
            .where(SourceRecord.id == demo_id("public-record"))
            .values(redistribution_status="restricted")
        )
    elif change == "source":
        await session.execute(
            update(DataSource)
            .where(DataSource.id == demo_id("public-source"))
            .values(licensing_status="restricted")
        )
    else:
        await session.execute(
            update(SourceEntityLink)
            .where(SourceEntityLink.id == demo_id(f"public-link:{identity}"))
            .values(review_status="pending_review")
        )
    await session.flush()
    filtered = await client.get("/api/v1/fragrances?concentration=eau_de_toilette")
    assert filtered.json()["data"] == []
    detail = await client.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")
    if change in {"record", "source"}:
        assert detail.status_code == 404
    else:
        assert all(
            r["concentration"] != "eau_de_toilette"
            for r in detail.json()["data"]["releases"]
        )


async def test_stale_identity_grant_hides_entity(
    client: AsyncClient, session: AsyncSession
) -> None:
    brand = await session.get(Brand, demo_id("brand:1"))
    assert brand is not None
    brand.name = "Unreviewed replacement"
    await session.flush()
    assert (await client.get("/api/v1/fragrances")).json()["pagination"]["total"] == 2


async def test_query_count_is_bounded(
    client: AsyncClient, session: AsyncSession
) -> None:
    counts: list[str] = []
    bind = session.get_bind()

    def count(*args: object) -> None:
        counts.append(str(args[2]))

    event.listen(bind, "before_cursor_execute", count)
    try:
        for limit in (1, 50):
            counts.clear()
            response = await client.get(f"/api/v1/fragrances?limit={limit}")
            assert response.status_code == 200, response.text
            assert (
                len(counts) == 6
            )  # Window total, file policies and one bounded media batch.
    finally:
        event.remove(bind, "before_cursor_execute", count)


async def test_empty_database(session: AsyncSession) -> None:
    app = create_app(Settings(app_env="test"))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        assert (await http.get("/api/v1/fragrances")).json() == {
            "data": [],
            "pagination": {"limit": 20, "offset": 0, "total": 0},
        }


async def test_sanitized_server_error() -> None:
    app = create_app()

    async def broken() -> AsyncIterator[AsyncSession]:
        raise RuntimeError("private password and evidence")
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = broken
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as http:
        response = await http.get("/api/v1/fragrances")
        assert response.status_code == 500
        assert response.json() == {
            "error": {"code": "500", "message": "Internal server error"}
        }


async def test_approved_chain_and_revocation(
    session: AsyncSession, client: AsyncClient
) -> None:
    """Test invented data only: simulate a fully reviewed licensing chain."""
    from datetime import UTC, datetime

    fields = [
        "name",
        "slug",
        "brand_id",
        "fragrance_id",
        "concentration",
        "release_year",
        "notes",
        "accords",
    ]
    await session.execute(
        update(DataSource)
        .where(DataSource.id == demo_id("public-source"))
        .values(
            source_type="test_fixture",
            authorization_status="approved",
            licensing_status="approved",
            reviewed_at=datetime.now(UTC),
            evidence=[{"test": "not a real license"}],
            permitted_fields=fields,
        )
    )
    await session.execute(
        update(SourceRecord)
        .where(SourceRecord.id == demo_id("public-record"))
        .values(
            storage_status="approved",
            storage_evidence="Invented test only",
            redistribution_status="approved",
            redistribution_evidence="Invented test only",
        )
    )
    await session.execute(
        update(FieldProvenance)
        .where(
            FieldProvenance.usage_rights_status == "synthetic",
            FieldProvenance.selection_status == "selected",
        )
        .values(
            usage_rights_status="approved",
            rights_evidence="Invented test only",
        )
    )
    app = create_app(Settings(app_env="production"))
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.get("/api/v1/fragrances")
        assert response.json()["pagination"]["total"] == 4
        assert not any(f["synthetic"] for f in response.json()["data"])
        # Mixed licensed/synthetic metadata must label the whole public context.
        # Production must still suppress the synthetic scalar, not the real identity.
        from fraggy_api.seed import COLLECTED_AT

        await session.execute(
            update(FieldProvenance)
            .where(
                FieldProvenance.id
                == demo_id(f"public-claim:{demo_id('release:edp')}:concentration")
            )
            .values(usage_rights_status="pending_review")
        )
        await session.execute(
            update(SourceRecord)
            .where(SourceRecord.id == demo_id("record:1"))
            .values(processing_state="linked")
        )
        await session.execute(
            update(SourceEntityLink)
            .where(SourceEntityLink.id == demo_id("link:1"))
            .values(review_status="approved")
        )
        session.add(
            FieldProvenance(
                entity_link_id=demo_id("link:1"),
                field_path="concentration",
                value="eau_de_parfum",
                value_state="known",
                selection_status="selected",
                collected_at=COLLECTED_AT,
                usage_rights_status="synthetic",
            )
        )
        await session.flush()
        demo_detail = (
            await client.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")
        ).json()["data"]
        assert demo_detail["synthetic"] is True
        demo_release = next(
            r for r in demo_detail["releases"] if r["id"] == str(demo_id("release:edp"))
        )
        assert (
            demo_release["synthetic"] is True
            and demo_release["concentration"] == "eau_de_parfum"
        )
        production_detail = (
            await http.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")
        ).json()["data"]
        assert production_detail["synthetic"] is False
        assert (
            next(
                r
                for r in production_detail["releases"]
                if r["id"] == str(demo_id("release:edp"))
            )["concentration"]
            is None
        )
        # Selecting a claim with unknown rights must never authorize publication.
        await session.execute(
            update(FieldProvenance)
            .where(FieldProvenance.field_path == "concentration")
            .values(usage_rights_status="pending_review")
        )
        assert (
            await http.get("/api/v1/fragrances?concentration=eau_de_toilette")
        ).json()["data"] == []
        # Uninterpreted restrictions fail closed; no automatic legal interpretation.
        await session.execute(
            update(DataSource)
            .where(DataSource.id == demo_id("public-source"))
            .values(reuse_restrictions=["private use only"])
        )
        assert (await http.get("/api/v1/fragrances")).json()["data"] == []
        await session.execute(
            update(DataSource)
            .where(DataSource.id == demo_id("public-source"))
            .values(reuse_restrictions=[], permitted_fields=["name"])
        )
        assert (await http.get("/api/v1/brands")).json()["data"] == []


async def test_openapi_and_unknown_route(client: AsyncClient) -> None:
    # Development-only schema remains available; the catalog stays read-only.
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as http:
        schema = (await http.get("/openapi.json")).json()
        for path in [
            "brands",
            "brands/{slug}",
            "fragrances",
            "fragrances/{id}",
            "fragrances/search",
            "notes",
            "accords",
        ]:
            assert set(schema["paths"]["/api/v1/" + path]) == {"get"}
        response = await http.get("/api/v1/private-evidence")
        assert response.json()["error"]["code"] == "404"


async def test_nested_release_bound(client: AsyncClient, session: AsyncSession) -> None:
    from fraggy_api.models import FragranceRelease
    from fraggy_api.seed import COLLECTED_AT

    for _ in range(22):
        identity, link_id = uuid4(), uuid4()
        session.add(FragranceRelease(id=identity, fragrance_id=demo_id("fragrance:1")))
        await session.flush()
        session.add(
            SourceEntityLink(
                id=link_id,
                source_record_id=demo_id("public-record"),
                release_id=identity,
                review_status="approved",
            )
        )
        await session.flush()
        session.add(
            FieldProvenance(
                entity_link_id=link_id,
                field_path="fragrance_id",
                value=str(demo_id("fragrance:1")),
                value_state="known",
                selection_status="selected",
                collected_at=COLLECTED_AT,
                usage_rights_status="synthetic",
            )
        )
    await session.flush()
    detail = (await client.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")).json()[
        "data"
    ]
    assert len(detail["releases"]) == 20
    assert detail["releases_truncated"] is True


async def test_note_rights_apply_to_filter_and_response(
    client: AsyncClient, session: AsyncSession
) -> None:
    await session.execute(
        update(FieldProvenance)
        .where(FieldProvenance.id == demo_id(f"public-claim:{demo_id('note:1')}:name"))
        .values(usage_rights_status="restricted")
    )
    assert (await client.get(f"/api/v1/fragrances?notes={demo_id('note:1')}")).json()[
        "data"
    ] == []
    detail = (await client.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")).json()[
        "data"
    ]
    assert all(
        note["name"] != "Cedar"
        for release in detail["releases"]
        for note in release["notes"]
    )


async def test_public_no_store(client: AsyncClient) -> None:
    response = await client.get("/api/v1/fragrances")
    assert response.headers["cache-control"] == "no-store"
