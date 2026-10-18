"""Owned original preview fixtures; no application database reset or network."""

import stat

import pytest
from fraggy_api.database import get_session
from fraggy_api.main import create_app
from fraggy_api.models import CollectionSource, DataSource, MediaAsset
from fraggy_api.preview import prepare
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from sqlalchemy import func, select


async def test_preview_has_original_images_credits_pagination_and_disabled_sources(
    session, tmp_path
):
    fixture = await prepare(session, tmp_path, 20)
    assert fixture["genuine_fragrances"] == fixture["genuine_images"] == 0
    assert fixture["synthetic_images"] == 4
    assert await session.scalar(select(func.count()).select_from(CollectionSource)) == 0
    sources = (
        await session.scalars(
            select(DataSource).where(DataSource.source_type == "website")
        )
    ).all()
    assert len(sources) == 7 and all(
        not s.enabled
        and s.authorization_status == s.licensing_status == "pending_review"
        for s in sources
    )
    app = create_app(
        Settings(
            app_env="test",
            catalog_include_synthetic=True,
            media_root=tmp_path / "media",
        )
    )
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = (await client.get("/api/v1/fragrances?limit=2")).json()
        second = (await client.get("/api/v1/fragrances?limit=2&offset=2")).json()
        assert (
            first["pagination"]["total"] == 20
            and first["data"][0]["id"] != second["data"][0]["id"]
        )
        detail = (
            await client.get("/api/v1/fragrances/" + fixture["fragrance_id"])
        ).json()["data"]
        assert detail["synthetic"] and detail["attributions"]
        assert len(detail["images"]) == 2 and detail["primary_image"]
        assert sum(len(r["variant_images"]) for r in detail["releases"]) == 1
        assert (await client.get(detail["primary_image"]["url"])).status_code == 200
        assert "evidence" not in str(detail) and "storage_reviewer" not in str(detail)
    for blob in (tmp_path / "media").glob("*.webp"):
        assert stat.S_IMODE(blob.stat().st_mode) == 0o600
    assets = (await session.scalars(select(MediaAsset))).all()
    assert all(a.image_policy["rights"]["synthetic"] for a in assets)


async def test_preview_does_not_overwrite_existing_catalog(session, tmp_path):
    await prepare(session, tmp_path, 20)
    with pytest.raises(ValueError, match="empty"):
        await prepare(session, tmp_path, 20)
