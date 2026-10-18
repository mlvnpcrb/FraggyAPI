"""Original synthetic preview fixtures in an owned disposable database only."""

import hashlib
import io
import json
import re
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .attribution import Attribution
from .media.service import ImageRights, approve, ingest
from .models import DataSource, FragranceVariant, SourceEntityLink
from .quality.benchmark_data import generate, identity


async def prepare(
    session: AsyncSession, directory: Path, size: int = 100
) -> dict[str, Any]:
    database = await session.scalar(text("SELECT current_database()"))
    if not isinstance(database, str) or not re.fullmatch(
        r"fraggy_(?:preview|test)_[a-f0-9]{32}", database
    ):
        raise ValueError("Owned disposable preview/test database required")
    if size not in {20, 100}:
        raise ValueError("Preview fixture size must be 20 or 100")
    fixture = await generate(session, size)
    registry = json.loads(
        (Path(__file__).resolve().parents[3] / "config/sources.json").read_text()
    )["sources"]
    for source in registry:
        if source["enabled"]:
            raise ValueError("Website adapters must remain disabled")
        session.add(
            DataSource(
                id=uuid4(),
                key=source["id"],
                name=source["name"],
                website=source["website"],
                adapter_identifier=source["adapter"],
                source_type="website",
                enabled=False,
                authorization_status="pending_review",
                licensing_status="pending_review",
            )
        )
    await session.flush()
    now = datetime.now(UTC)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    variant = await session.scalar(
        select(FragranceVariant)
        .where(FragranceVariant.release_id == identity("release:0:edp"))
        .order_by(FragranceVariant.id)
        .limit(1)
    )
    assert variant is not None
    parent = await session.scalar(
        select(SourceEntityLink).where(
            SourceEntityLink.release_id == variant.release_id
        )
    )
    assert parent is not None
    variant_link = SourceEntityLink(
        id=uuid4(),
        source_record_id=parent.source_record_id,
        variant_id=variant.id,
        review_status="approved",
    )
    session.add(variant_link)
    await session.flush()
    targets: list[tuple[str, UUID, Literal["primary", "gallery"], str]] = [
        ("fragrance_id", identity("fragrance:0"), "primary", "#c9a56e"),
        ("fragrance_id", identity("fragrance:0"), "gallery", "#a3b59c"),
        ("release_id", identity("release:0:edp"), "primary", "#a5b7c9"),
        ("variant_id", variant.id, "primary", "#b6a0b9"),
    ]
    image_ids = []
    for field, target, role, color in targets:
        link = await session.scalar(
            select(SourceEntityLink).where(getattr(SourceEntityLink, field) == target)
        )
        assert link is not None
        canvas = Image.new("RGB", (480, 640), "#f8f6ee")
        drawing = ImageDraw.Draw(canvas)
        drawing.rounded_rectangle((100, 160, 380, 560), radius=30, fill=color)
        drawing.rectangle((145, 75, 335, 160), fill="#51443c")
        drawing.rectangle((130, 300, 350, 430), fill="#faf7ed")
        drawing.text((172, 340), "FRAGGY / DEMO", fill="#302a25")
        drawing.text((180, 380), "FICTIONAL", fill="#302a25")
        output = io.BytesIO()
        canvas.save(output, "PNG")
        path = directory / "original.png"
        path.write_bytes(output.getvalue())
        rights = ImageRights(
            source_key="fictional-benchmark",
            source_url="https://example.invalid/original-preview-artwork",
            content_sha256=hashlib.sha256(output.getvalue()).hexdigest(),
            copyright_holder="FraggyAPI original fixture author",
            attribution=Attribution(
                provider="FraggyAPI original fixture author",
                text="Original fictional preview bottle artwork.",
                source_url="https://example.invalid/original-preview-artwork",
                license_name="Original synthetic fixture permission",
                license_url="https://example.invalid/original-preview-permission",
                copyright_holder="FraggyAPI original fixture author",
                last_verified=date.today(),
                modification_disclosure_required=True,
                modification_disclosure="Original drawing resized and converted to WebP; metadata removed.",
            ),
            download=True,
            storage=True,
            transformations=True,
            website_display=True,
            pwa_display=True,
            commercial_use=True,
            api_delivery=True,
            reviewed_at=now - timedelta(seconds=1),
            expires_at=now + timedelta(days=7),
            evidence="Original procedural artwork created by this preview; no external pixels or license approval",
            synthetic=True,
        )
        asset = await ingest(
            session,
            directory / "media",
            link.id,
            path,
            "image/png",
            rights,
            reviewer="original-preview-operator",
            reason="Explicit synthetic-only local preview fixture storage",
            alt="Original fictional preview bottle",
            role=role,
        )
        await approve(
            session,
            directory / "media",
            asset.id,
            "original-preview-publisher",
            "Explicit original synthetic artwork publication for local preview",
        )
        image_ids.append(str(asset.id))
    path.unlink(missing_ok=True)
    return {
        "fixture": fixture,
        "fragrance_id": str(identity("fragrance:0")),
        "release_id": str(identity("release:0:edp")),
        "variant_id": str(variant.id),
        "image_ids": image_ids,
        "genuine_fragrances": 0,
        "genuine_images": 0,
        "synthetic_images": len(image_ids),
        "source_key": "fictional-benchmark",
    }
