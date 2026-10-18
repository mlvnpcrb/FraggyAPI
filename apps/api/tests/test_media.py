"""Original generated raster fixtures only; no third-party image access."""

import hashlib
import io
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fraggy_api.attribution import Attribution
from fraggy_api.database import get_session
from fraggy_api.main import create_app
from fraggy_api.media.processing import (
    MAX_BYTES,
    MediaError,
    optimize,
    read_local,
)
from fraggy_api.media.service import (
    ImageRights,
    approve,
    garbage_collect,
    ingest,
    revoke,
    revoke_source,
)
from fraggy_api.models import (
    DataSource,
    FragranceRelease,
    FragranceVariant,
    MediaAsset,
    SourceEntityLink,
)
from fraggy_api.seed import demo_id, seed_demo
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
from pydantic import ValidationError
from sqlalchemy import func, select


def artwork(color="gold", size=(400, 600), fmt="PNG", **options):
    image = Image.new("RGB", size, "ivory")
    drawing = ImageDraw.Draw(image)
    drawing.rectangle(
        (size[0] // 4, size[1] // 3, size[0] * 3 // 4, size[1] * 4 // 5), fill=color
    )
    drawing.text((size[0] // 3, size[1] // 2), "FICTIONAL", fill="black")
    buffer = io.BytesIO()
    image.save(buffer, fmt, **options)
    return buffer.getvalue()


def rights_for(data):
    now = datetime.now(UTC)
    return ImageRights(
        source_key="synthetic-public-demo",
        source_url="https://example.invalid/original-bottle",
        content_sha256=hashlib.sha256(data).hexdigest(),
        copyright_holder="FraggyAPI fictional artwork workshop",
        attribution=Attribution(
            provider="Fictional artwork workshop",
            text="Original synthetic bottle artwork.",
            source_url="https://example.invalid/original-bottle",
            license_name="Original test permission",
            license_url="https://example.invalid/test-permission",
            copyright_holder="FraggyAPI fictional artwork workshop",
            last_verified=date.today(),
            modification_disclosure_required=True,
            modification_disclosure="Metadata stripped, resized and converted to WebP.",
        ),
        download=True,
        storage=True,
        transformations=True,
        website_display=True,
        pwa_display=True,
        commercial_use=True,
        api_delivery=True,
        reviewed_at=now - timedelta(minutes=1),
        expires_at=now + timedelta(days=1),
        evidence="PRIVATE_ORIGINAL_FIXTURE_PERMISSION",
        synthetic=True,
    )


@pytest_asyncio.fixture
async def media(session, tmp_path):
    await seed_demo(session, allow_demo_data=True, publish_demo_catalog=True)
    source = await session.get(DataSource, demo_id("public-source"))
    source.reviewed_at = datetime.now(UTC)
    source.evidence = [{"kind": "original_image_fixture_review"}]
    root = tmp_path / "private-store"
    path = tmp_path / "original.png"
    data = artwork()
    path.write_bytes(data)
    app = create_app(
        Settings(app_env="test", catalog_include_synthetic=True, media_root=root)
    )
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        env = SimpleNamespace(
            session=session,
            path=path,
            data=data,
            root=root,
            source=source,
            client=client,
            app=app,
        )
        yield env


async def add(env, *, target="fragrance:1", role="primary", data=None):
    if data is not None:
        env.path.write_bytes(data)
    content = env.path.read_bytes()
    link_id = demo_id("public-link:" + str(demo_id(target)))
    asset = await ingest(
        env.session,
        env.root,
        link_id,
        env.path,
        "image/png",
        rights_for(content),
        reviewer="fixture-operator",
        reason="Original fictional image storage review",
        alt="Original fictional gold bottle",
        role=role,
    )
    return asset


async def detail(env):
    return (
        await env.client.get(f"/api/v1/fragrances/{demo_id('fragrance:1')}")
    ).json()["data"]


async def test_pending_approval_publication_attribution_and_bytes(media):
    asset = await add(media)
    assert (await detail(media))["primary_image"] is None
    url = f"/api/v1/media/{asset.id}/display"
    assert (await media.client.get(url)).status_code == 404
    await approve(
        media.session,
        media.root,
        asset.id,
        "publisher",
        "Separately reviewed fictional image publication",
    )
    result = await detail(media)
    assert result["primary_image"]["id"] == str(asset.id)
    assert len(result["images"]) == 1
    assert (
        result["primary_image"]["attribution"]["copyright_holder"]
        == "FraggyAPI fictional artwork workshop"
    )
    assert "PRIVATE_ORIGINAL" not in str(result)
    assert "storage_reviewer" not in str(result)
    response = await media.client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/webp"
    assert response.headers["cache-control"] == "no-store"  # Global API middleware.
    with Image.open(io.BytesIO(response.content)) as rendered:
        assert rendered.format == "WEBP" and not rendered.getexif()


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "license",
        "expired",
        "link",
        "binding",
        "content",
        "evidence",
        "production",
    ],
)
async def test_image_rights_fail_closed(media, change):
    asset = await add(media)
    await approve(
        media.session,
        media.root,
        asset.id,
        "publisher",
        "Original fictional publication",
    )
    if change == "source":
        media.source.authorization_status = "restricted"
    elif change == "license":
        media.source.licensing_status = "restricted"
    elif change == "expired":
        policy = dict(asset.image_policy)
        policy["rights"] = {
            **policy["rights"],
            "expires_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        }
        asset.image_policy = policy
    elif change == "link":
        link = await media.session.get(SourceEntityLink, asset.entity_link_id)
        link.review_status = "rejected"
    elif change == "binding":
        asset.media_metadata = {**asset.media_metadata, "alt": "Unreviewed change"}
    elif change == "content":
        asset.content_sha256 = "a" * 64
    elif change == "evidence":
        asset.image_policy = {}
    elif change == "production":
        media.app.state.settings.app_env = "production"
    await media.session.flush()
    response = await media.client.get(f"/api/v1/media/{asset.id}/display")
    assert response.status_code == 404
    listing = await media.client.get("/api/v1/fragrances")
    assert all(f["primary_image"] is None for f in listing.json()["data"])


async def test_gallery_dedup_and_image_revocation(media):
    first = await add(media)
    with pytest.raises(MediaError, match="duplicate_target_image"):
        await add(media)
    second = await add(media, role="gallery", data=artwork("blue"))
    for asset in (first, second):
        await approve(
            media.session,
            media.root,
            asset.id,
            "publisher",
            "Original fictional image approval",
        )
    assert len((await detail(media))["images"]) == 2
    await revoke(
        media.session, first.id, "operator", "Withdraw original fictional image"
    )
    assert (await detail(media))["primary_image"] is None
    assert len((await detail(media))["images"]) == 1
    assert (
        await media.client.get(f"/api/v1/media/{first.id}/thumb")
    ).status_code == 404
    removed = await garbage_collect(media.session, media.root)
    assert removed == 2
    assert (
        await media.client.get(f"/api/v1/media/{second.id}/display")
    ).status_code == 200


async def test_concentration_variant_and_reformulation_binding(media):
    release = await add(media, target="release:edp")
    await approve(
        media.session, media.root, release.id, "publisher", "Exact EDP image approval"
    )
    result = await detail(media)
    assert result["primary_image"] is None
    edp = next(r for r in result["releases"] if r["id"] == str(demo_id("release:edp")))
    assert edp["primary_image"]["id"] == str(release.id)
    assert all(
        r["primary_image"] is None for r in result["releases"] if r["id"] != edp["id"]
    )
    variant = FragranceVariant(
        id=uuid4(), release_id=demo_id("release:edp"), bottle_size_ml=75
    )
    media.session.add(variant)
    link = SourceEntityLink(
        id=uuid4(),
        variant_id=variant.id,
        source_record_id=demo_id("public-record"),
        review_status="approved",
    )
    media.session.add(link)
    await media.session.flush()
    asset = await ingest(
        media.session,
        media.root,
        link.id,
        media.path,
        "image/png",
        rights_for(media.data),
        reviewer="operator",
        reason="Exact invented variant image",
        alt="Fictional 75 ml bottle",
        role="primary",
    )
    await approve(
        media.session, media.root, asset.id, "publisher", "Exact variant publication"
    )
    result = await detail(media)
    edp = next(r for r in result["releases"] if r["id"] == str(demo_id("release:edp")))
    assert edp["variant_images"][0]["variant_id"] == str(variant.id)
    # Identical binary assets across rights targets share storage, never approvals.
    assert len(list(media.root.glob("*.webp"))) == 2
    canonical = await media.session.get(FragranceRelease, demo_id("release:edp"))
    canonical.version_label = "Unreviewed reformulation"
    await media.session.flush()
    assert (
        await media.client.get(f"/api/v1/media/{asset.id}/display")
    ).status_code == 404
    assert all(
        not r["images"] and not r["variant_images"]
        for r in (await detail(media))["releases"]
    )


async def test_source_revocation_and_shared_blob_safety(media):
    first = await add(media)
    second = await add(media, target="release:edp")
    for asset in (first, second):
        await approve(
            media.session,
            media.root,
            asset.id,
            "publisher",
            "Original fictional publication",
        )
    await revoke(media.session, first.id, "operator", "Image-only revocation")
    assert (
        await garbage_collect(media.session, media.root) == 0
    )  # Other grant still needs shared bytes.
    assert (
        await media.client.get(f"/api/v1/media/{second.id}/display")
    ).status_code == 200
    assert (
        await revoke_source(
            media.session, media.source.id, "operator", "Source access withdrawn"
        )
        == 2
    )
    assert await garbage_collect(media.session, media.root) == 2
    assert (
        await media.client.get(f"/api/v1/media/{second.id}/display")
    ).status_code == 404


@pytest.mark.parametrize("damage", ["missing", "corrupt", "symlink"])
async def test_missing_broken_and_symlink_media(media, damage):
    asset = await add(media)
    await approve(
        media.session, media.root, asset.id, "publisher", "Original fictional image"
    )
    hashed = asset.media_metadata["renditions"]["display"]["sha256"]
    path = media.root / (hashed + ".webp")
    if damage == "missing":
        path.unlink()
    elif damage == "corrupt":
        path.write_bytes(b"corrupt")
    else:
        path.unlink()
        path.symlink_to(media.path)
    assert (
        await media.client.get(f"/api/v1/media/{asset.id}/display")
    ).status_code == 404
    if damage != "corrupt":
        assert (await detail(media))["primary_image"] is None


@pytest.mark.parametrize(
    "flag",
    [
        "download",
        "storage",
        "transformations",
        "website_display",
        "pwa_display",
        "commercial_use",
        "api_delivery",
    ],
)
def test_each_image_permission_is_independent(flag):
    values = rights_for(artwork()).model_dump()
    values[flag] = False
    with pytest.raises(ValidationError):
        ImageRights.model_validate(values)


@pytest.mark.parametrize(
    "data,mime",
    [
        (b"<svg></svg>", "image/svg+xml"),
        (b"not an image", "image/png"),
        (b"x" * (MAX_BYTES + 1), "image/png"),
        (artwork(size=(20, 20)), "image/png"),
        (artwork(size=(4100, 40)), "image/png"),
        (artwork(), "image/jpeg"),
    ],
)
def test_invalid_images(data, mime):
    with pytest.raises(MediaError):
        optimize(data, mime)


def test_animation_and_exif_are_handled():
    buffer = io.BytesIO()
    a = Image.new("RGB", (64, 64), "red")
    b = Image.new("RGB", (64, 64), "blue")
    a.save(buffer, "WEBP", save_all=True, append_images=[b])
    with pytest.raises(MediaError):
        optimize(buffer.getvalue(), "image/webp")
    exif = Image.Exif()
    exif[0x010E] = "PRIVATE CAMERA DATA"
    exif[0x0112] = 6
    _, outputs, sizes = optimize(artwork(fmt="JPEG", exif=exif), "image/jpeg")
    assert sizes["display"] == (600, 400)
    assert max(sizes["thumb"]) == 320
    for data in outputs.values():
        with Image.open(io.BytesIO(data)) as rendered:
            assert not rendered.getexif()
            assert not {"exif", "icc_profile", "xmp", "comment"} & rendered.info.keys()


async def test_hash_mismatch_stores_nothing(media):
    policy = rights_for(media.data)
    policy.content_sha256 = "0" * 64
    with pytest.raises(MediaError, match="hash_mismatch"):
        await ingest(
            media.session,
            media.root,
            demo_id("public-link:" + str(demo_id("fragrance:1"))),
            media.path,
            "image/png",
            policy,
            reviewer="operator",
            reason="Hash-pinned review",
            alt="Fictional bottle",
        )
    assert not media.root.exists()
    assert (
        await media.session.scalar(
            select(func.count())
            .select_from(MediaAsset)
            .where(MediaAsset.content_sha256 == "0" * 64)
        )
        == 0
    )


def test_read_local_denies_symlink_and_directory(tmp_path):
    path = tmp_path / "original.png"
    path.write_bytes(artwork())
    link = tmp_path / "link.png"
    link.symlink_to(path)
    for invalid in (link, tmp_path):
        with pytest.raises(MediaError):
            read_local(invalid)


async def test_explicit_new_primary_demotes_old_with_valid_proof(media):
    first = await add(media)
    await approve(
        media.session, media.root, first.id, "publisher", "First original primary"
    )
    second = await add(media, data=artwork("blue"))
    await approve(
        media.session, media.root, second.id, "publisher", "Explicitly replace primary"
    )
    result = await detail(media)
    assert result["primary_image"]["id"] == str(second.id)
    assert [i["role"] for i in result["images"]] == ["primary", "gallery"]
    assert first.image_policy["primary_replaced_by"] == str(second.id)
    assert (
        await media.client.get(f"/api/v1/media/{first.id}/display")
    ).status_code == 200


async def test_source_storage_withdrawal_enforces_retention_cleanup(media):
    asset = await add(media)
    await approve(
        media.session, media.root, asset.id, "publisher", "Original fictional primary"
    )
    media.source.licensing_status = "restricted"
    await media.session.flush()
    assert await garbage_collect(media.session, media.root) == 2
    assert asset.storage_status == "restricted"
    assert not asset.media_metadata


async def test_separately_licensed_image_can_be_public_in_production(session, tmp_path):
    # Entirely invented local fixtures simulate a real-license workflow. No real
    # source/image is approved, acquired or published outside this disposable DB.
    from fraggy_api.importing.formats import Record, manifest_file
    from test_attribution import credit, pilot
    from test_import_pipeline import EXAMPLES

    manifest = manifest_file(EXAMPLES / "source-manifest.json").model_copy(
        update={
            "synthetic": False,
            "source_id": "original-image-policy-test",
            "attribution": credit(),
            "attribution_requirements": ["Adjacent original fixture credit"],
        }
    )
    record = Record(
        source_record_id="original-image-fixture",
        brand_name="Invented Image Workshop",
        fragrance_name="Original Bottle Policy Test",
        concentration="EDP",
    )
    _, release_id = await pilot(session, manifest, record)
    link_id = await session.scalar(
        select(SourceEntityLink.id).where(SourceEntityLink.release_id == release_id)
    )
    data = artwork()
    path = tmp_path / "original.png"
    path.write_bytes(data)
    root = tmp_path / "store"
    rights = rights_for(data).model_copy(
        update={"synthetic": False, "source_key": manifest.source_id}
    )
    asset = await ingest(
        session,
        root,
        link_id,
        path,
        "image/png",
        rights,
        reviewer="operator",
        reason="Original-only simulated license review",
        alt="Original fictional bottle",
        role="primary",
    )
    await approve(
        session,
        root,
        asset.id,
        "publisher",
        "Independent original-only image permission",
    )
    app = create_app(
        Settings(app_env="production", catalog_include_synthetic=True, media_root=root)
    )
    app.dependency_overrides[get_session] = lambda: session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        listing = (await client.get("/api/v1/fragrances")).json()
        image = listing["data"][0]["releases"][0]["primary_image"]
        assert image["id"] == str(asset.id) and not image["synthetic"]
        assert "PRIVATE_ORIGINAL" not in str(listing)
        assert (await client.get(image["url"])).status_code == 200


def test_safe_decoder_rejects_bombs_and_truncated_files(monkeypatch):
    data = artwork()
    with pytest.raises(MediaError):
        optimize(data[:80], "image/png")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    with pytest.raises(MediaError):
        optimize(data, "image/png")
