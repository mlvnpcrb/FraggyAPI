"""Explicit original-fictional HTTP collection demo in one UUID-owned database."""

import argparse
import asyncio
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import UTC, date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import asyncpg
from fraggy_api.attribution import Attribution
from fraggy_api.collection.engine import Collector, activate, revoke_collection
from fraggy_api.collection.policy import (
    CollectionError,
    Endpoint,
    Grant,
    review_collection,
)
from fraggy_api.database import create_engine, get_session
from fraggy_api.importing.authorization import review_source, revoke
from fraggy_api.importing.formats import manifest_file, parse_file
from fraggy_api.importing.pipeline import decide, publish
from fraggy_api.main import create_app
from fraggy_api.media.service import ImageRights, garbage_collect
from fraggy_api.media.service import approve as approve_image
from fraggy_api.media.service import ingest as ingest_image
from fraggy_api.media.service import revoke_source as revoke_images
from fraggy_api.models import DataReviewQueue, SourceEntityLink, SourceRecord
from fraggy_api.settings import Settings
from httpx2 import ASGITransport, AsyncClient
from PIL import Image, ImageDraw
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "name",
    "slug",
    "brand_id",
    "fragrance_id",
    "concentration",
    "release_year",
    "notes",
    "accords",
]


async def run(size: int = 2, *, first_source: bool = False) -> dict[str, Any]:
    if size not in {2, 100, 1000}:
        raise CollectionError("invalid_demonstration_size")
    settings = Settings()
    parsed = make_url(settings.database_url.get_secret_value())
    if settings.app_env == "production" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise CollectionError("nonproduction_loopback_database_required")
    original = parse_file(ROOT / "data/examples/fragrances.json")[0].model_dump(
        mode="json"
    )
    rows = [
        {
            **original,
            "source_record_id": f"original-collector-{i:04d}",
            "fragrance_name": f"Original{i:04d} Fictional Collector",
            "concentration": "EDP" if i % 2 == 0 else "EDT",
            "version_label": "Separate original fictional concentration",
        }
        for i in range(size)
    ]
    if first_source and size != 100:
        raise CollectionError("first_source_demo_requires_100_original_records")
    entity_ids = [f"Q990000000{i:03d}" for i in range(size)]
    page_size = 1 if size == 2 else 100
    requests: list[dict[str, list[str]]] = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            query = parse_qs(urlsplit(self.path).query)
            requests.append(query)
            offset = int(query.get("cursor", ["0"])[0])
            body = json.dumps(
                {
                    "records": rows[offset : offset + page_size],
                    "next_cursor": str(offset + page_size)
                    if offset + page_size < size
                    else None,
                    "watermark": "fictional-v1",
                }
            ).encode()
            if first_source:
                match = re.search(
                    r"VALUES \?item \{ ([^}]+) \}", query.get("query", [""])[0]
                )
                assert match is not None
                ids = re.findall(r"wd:(Q[0-9]+)", match[1])
                assert set(ids) <= set(entity_ids) and len(ids) <= 25
                body = json.dumps(
                    {
                        "head": {"vars": ["item", "itemLabel", "brand", "brandLabel"]},
                        "results": {
                            "bindings": [
                                {
                                    "item": {
                                        "type": "uri",
                                        "value": "http://www.wikidata.org/entity/"
                                        + identifier,
                                    },
                                    "itemLabel": {
                                        "type": "literal",
                                        "xml:lang": "en",
                                        "value": "Invented"
                                        + identifier
                                        + " Fictional Orbit",
                                    },
                                    "brand": {
                                        "type": "uri",
                                        "value": "http://www.wikidata.org/entity/Q990000099999",
                                    },
                                    "brandLabel": {
                                        "type": "literal",
                                        "xml:lang": "en",
                                        "value": "Original Fictional Workshop",
                                    },
                                }
                                for identifier in ids
                            ]
                        },
                    }
                ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    admin = await asyncpg.connect(
        parsed.set(drivername="postgresql").render_as_string(hide_password=False)
    )
    name = "fraggy_demo_" + uuid4().hex
    created = False
    engine = None
    started = time.perf_counter()
    media_temp = TemporaryDirectory(prefix="fraggy-original-images-")
    try:
        await admin.execute(f'CREATE DATABASE "{name}"')
        created = True
        url = parsed.set(database=name).render_as_string(hide_password=False)
        migration = await asyncio.to_thread(
            subprocess.run,
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "apps/api/alembic.ini",
                "upgrade",
                "head",
            ],
            cwd=ROOT,
            env={
                **os.environ,
                "DATABASE_URL": url,
                "MIGRATION_DATABASE_URL": url,
                "APP_ENV": "test",
            },
            capture_output=True,
            text=True,
        )
        if migration.returncode:
            raise CollectionError("demonstration_migration_failed")
        config = Settings(
            app_env="test",
            database_url=SecretStr(url),
            catalog_include_synthetic=True,
            media_root=Path(media_temp.name) / "store",
        )
        engine = create_engine(config)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        manifest = manifest_file(
            ROOT / "data/examples/source-manifest.json"
        ).model_copy(
            update={
                "source_id": "fictional-collection-demonstration",
                "attribution_requirements": ["Adjacent original fictional credit"],
                "attribution": Attribution(
                    provider="FraggyAPI fictional workshop",
                    text="Original fictional metadata created for this demonstration.",
                    source_url="https://example.invalid/fictional-demo",
                    license_name="Original fictional demonstration permission",
                    license_url="https://example.invalid/fictional-demo-license",
                    copyright_holder="Fictional Workshop",
                    placement="adjacent_record",
                    modification_disclosure_required=True,
                    modification_disclosure="Metadata normalized and projected by FraggyAPI.",
                    last_verified=date.today(),
                ),
            }
        )
        if first_source:
            manifest = manifest.model_copy(
                update={
                    "permitted_fields": [*manifest.permitted_fields, "source_metadata"]
                }
            )
        instant = datetime.now(UTC)
        grant = Grant(
            manifest=manifest,
            endpoint=Endpoint(
                url=f"http://127.0.0.1:{server.server_port}/catalog",
                adapter="wikidata_sparql" if first_source else "rest_json",
                minimum_interval_seconds=0.01,
                **(
                    {
                        "entity_ids": entity_ids,
                        "user_agent": "FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; fixture@example.invalid)",
                    }
                    if first_source
                    else {}
                ),
            ),
            automated_access=True,
            database_storage=True,
            commercial_reuse=True,
            api_redistribution=True,
            attribution_accepted=True,
            access_restrictions=[
                "Original fictional local HTTP only; GET; no external access"
            ],
            evidence={
                k: "Original demonstration rights only; not an external license"
                for k in (
                    "automated_access",
                    "database_storage",
                    "commercial_reuse",
                    "api_redistribution",
                    "attribution",
                    "rate_limits",
                    "access_restrictions",
                )
            },
            reviewed_at=instant - timedelta(minutes=1),
            expires_at=instant + timedelta(hours=1),
        )
        async with factory.begin() as session:
            source = await review_source(
                session,
                manifest,
                "fictional-demo-operator",
                "Original fictional permission",
                allow_storage=True,
                publish_fields=FIELDS,
                accept_attribution=True,
            )
            collection = await review_collection(
                session,
                grant,
                "fictional-demo-operator",
                "Explicit original local demonstration",
            )
            assert not collection.enabled and not collection.schedule_enabled
            identity = collection.id
            await activate(
                session,
                identity,
                "fictional-demo-operator",
                "Activate original local fixture schedule",
                schedule=True,
                interval=60,
            )
        source_id = source.id
        collector = Collector(factory)
        result = (await collector.tick())[0]
        assert result["status"] == "succeeded" and result["records_staged"] == size
        again = await collector.run(identity)
        assert again["records_unchanged"] == size and again["records_staged"] == 0
        app = create_app(config)

        async def session_override():
            async with factory() as session:
                yield session

        app.dependency_overrides[get_session] = session_override
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before = (await client.get("/api/v1/fragrances")).json()
            assert before["data"] == []
            async with factory.begin() as session:
                snapshots = list(
                    (
                        await session.scalars(
                            select(SourceRecord)
                            .where(SourceRecord.source_id == source_id)
                            .order_by(SourceRecord.source_record_id)
                            .limit(2)
                        )
                    ).all()
                )
                for snapshot in snapshots:
                    review = await session.scalar(
                        select(DataReviewQueue.id).where(
                            DataReviewQueue.source_record_id == snapshot.id,
                            DataReviewQueue.status == "pending",
                        )
                    )
                    assert review is not None
                    await decide(
                        session,
                        review,
                        "approve_new",
                        "fictional-demo-operator",
                        "Separate original fictional record",
                    )
                    await publish(
                        session,
                        snapshot.id,
                        FIELDS,
                        "fictional-demo-operator",
                        "Explicit fictional field publication",
                    )
            published = (await client.get("/api/v1/fragrances")).json()
            assert len(published["data"]) == 2 and all(
                row["attributions"] and row["synthetic"] for row in published["data"]
            )
            media_result: dict[str, Any] = {"processed": 0}
            if first_source:
                image = Image.new("RGB", (400, 600), "ivory")
                drawing = ImageDraw.Draw(image)
                drawing.rounded_rectangle(
                    (100, 160, 300, 500), radius=25, fill="#d3b994"
                )
                drawing.rectangle((130, 100, 270, 160), fill="#695039")
                drawing.text((145, 280), "FICTIONAL", fill="black")
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                path = Path(media_temp.name) / "original.png"
                path.write_bytes(buffer.getvalue())
                image_rights = ImageRights(
                    source_key=manifest.source_id,
                    source_url="https://example.invalid/original-artwork",
                    content_sha256=hashlib.sha256(buffer.getvalue()).hexdigest(),
                    attribution=manifest.attribution.model_copy(
                        update={
                            "text": "Original fictional bottle artwork.",
                            "modification_disclosure": "Metadata stripped, converted to WebP and resized.",
                        }
                    ),
                    copyright_holder="Fictional Workshop",
                    download=True,
                    storage=True,
                    transformations=True,
                    website_display=True,
                    pwa_display=True,
                    commercial_use=True,
                    api_delivery=True,
                    reviewed_at=instant - timedelta(minutes=1),
                    expires_at=instant + timedelta(hours=1),
                    evidence="Original fictional artwork owned by demonstration author",
                    synthetic=True,
                )
                async with factory.begin() as session:
                    link = await session.scalar(
                        select(SourceEntityLink).where(
                            SourceEntityLink.fragrance_id == published["data"][0]["id"]
                        )
                    )
                    assert link is not None
                    asset = await ingest_image(
                        session,
                        config.media_root,
                        link.id,
                        path,
                        "image/png",
                        image_rights,
                        reviewer="fictional-demo-operator",
                        reason="Original fictional image storage review",
                        alt="Original fictional amber bottle",
                        role="primary",
                    )
                    image_id = asset.id
                assert (
                    await client.get(f"/api/v1/media/{image_id}/display")
                ).status_code == 404
                async with factory.begin() as session:
                    await approve_image(
                        session,
                        config.media_root,
                        image_id,
                        "fictional-demo-operator",
                        "Separate original image publication review",
                    )
                published = (await client.get("/api/v1/fragrances")).json()
                response = await client.get(f"/api/v1/media/{image_id}/display")
                assert (
                    response.status_code == 200
                    and response.headers["content-type"] == "image/webp"
                )
                assert sum(bool(f["primary_image"]) for f in published["data"]) == 1
                media_result = {
                    "processed": 1,
                    "approved": 1,
                    "renditions": 2,
                    "api_bytes": len(response.content),
                    "public_pending_status": 404,
                    "public_approved_status": 200,
                }
            quality = await collector.quality()
            assert quality["complete"] and quality["automatic_changes"] == 0
            async with factory.begin() as session:
                await revoke(
                    session,
                    manifest.source_id,
                    "fictional-demo-operator",
                    "Withdraw original fixture rights",
                )
                await revoke_collection(
                    session,
                    identity,
                    "fictional-demo-operator",
                    "Withdraw original local fixture collection",
                )
            withdrawn = (await client.get("/api/v1/fragrances")).json()
            assert withdrawn["data"] == []
            denied = False
            try:
                await collector.run(identity)
            except CollectionError:
                denied = True
            assert denied
            if first_source:
                assert (
                    await client.get(f"/api/v1/media/{image_id}/display")
                ).status_code == 404
                async with factory.begin() as session:
                    await revoke_images(
                        session,
                        source_id,
                        "fictional-demo-operator",
                        "Source rights withdrawn",
                    )
                async with factory.begin() as session:
                    media_result["blobs_removed"] = await garbage_collect(
                        session, config.media_root
                    )
                media_result["public_revoked_status"] = 404
        return {
            "synthetic_only": True,
            "source_adapter": "wikidata_sparql" if first_source else "rest_json",
            "media": media_result,
            "fixture_records": size,
            "records_left_for_manual_review": size - 2,
            "external_requests": 0,
            "collection_http_requests": len(requests),
            "scheduled_run": result,
            "idempotent_run": again,
            "public_before_review": 0,
            "public_after_explicit_publication": len(published["data"]),
            "public_after_revocation": 0,
            "collection_denied_after_revocation": denied,
            "catalog_quality": {
                "complete": quality["complete"],
                "severity_counts": quality["severity_counts"],
            },
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "api_method": "real FastAPI ASGI routes; local HTTP fixture for collection",
            "database_cleanup": "UUID-owned disposable database dropped in finally",
        }
    finally:
        if engine:
            await engine.dispose()
        if created:
            await admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        await admin.close()
        media_temp.cleanup()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main() -> None:
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--records", type=int, choices=(2, 100, 1000), default=2)
        parser.add_argument("--first-source", action="store_true")
        args = parser.parse_args()
        print(
            json.dumps(
                asyncio.run(run(args.records, first_source=args.first_source)),
                ensure_ascii=True,
            )
        )
    except Exception:
        print(json.dumps({"error": "synthetic_collection_demonstration_failed"}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
