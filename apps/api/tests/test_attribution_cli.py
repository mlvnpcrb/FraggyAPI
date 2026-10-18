"""Actual local CLI pilot; invented data in a disposable migrated database."""

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import disposable_database, migrate
from fastapi.testclient import TestClient
from fraggy_api.main import create_app
from fraggy_api.settings import Settings
from pydantic import SecretStr
from test_attribution import credit

ROOT = Path(__file__).resolve().parents[3]


def test_complete_attributed_cli_pilot(tmp_path: Path) -> None:
    manifest = json.loads((ROOT / "data/examples/source-manifest.json").read_text())
    manifest["attribution"] = credit().model_dump(mode="json")
    manifest["attribution_requirements"] = ["Provider credit beside every record"]
    path = tmp_path / "fictional-manifest.json"
    path.write_text(json.dumps(manifest))
    fields = "name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords"
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        environment = {
            **os.environ,
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "APP_ENV": "test",
        }

        def command(*args: str, expected: int = 0) -> dict:
            result = subprocess.run(
                [sys.executable, "-m", "fraggy_api.importing.cli", *args],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            assert result.returncode == expected, result.stdout + result.stderr
            return json.loads(result.stdout)

        def published() -> list:
            with TestClient(
                create_app(
                    Settings(
                        app_env="test",
                        database_url=SecretStr(url),
                        catalog_include_synthetic=True,
                    )
                )
            ) as client:
                response = client.get("/api/v1/fragrances")
                assert response.status_code == 200
                return response.json()["data"]

        review = [
            "source-review",
            "--manifest",
            str(path),
            "--allow-storage",
            "--publish-fields",
            fields,
            "--reviewer",
            "pilot-operator",
            "--reason",
            "Reviewed invented fixture policy",
        ]
        command(*review, expected=1)  # Missing explicit attribution acceptance.
        assert (
            command(*review, "--accept-attribution")["publication_status"]
            == "synthetic"
        )
        for extension in ("csv", "json", "jsonl"):
            assert (
                command(
                    "import",
                    "--manifest",
                    str(path),
                    "--file",
                    str(ROOT / f"data/examples/fragrances.{extension}"),
                    "--dry-run",
                )["canonical_writes"]
                == 0
            )
        assert published() == []
        loaded = command(
            "import",
            "--manifest",
            str(path),
            "--file",
            str(ROOT / "data/examples/fragrances.csv"),
        )
        identity = loaded["batches"][0]["records"][0]
        pending = command("pending", "--source", manifest["source_id"])["reviews"]
        command(
            "review",
            "--review-id",
            pending[0]["id"],
            "--decision",
            "approve_new",
            "--reviewer",
            "pilot-operator",
            "--reason",
            "Confirmed fictional canonical identity",
        )
        assert published() == []
        command(
            "publish",
            "--record-id",
            identity,
            "--fields",
            fields,
            "--reviewer",
            "pilot-publisher",
            "--reason",
            "Verified public claims and supported credits",
        )
        data = published()
        assert data[0]["attributions"][0]["text"] == manifest["attribution"]["text"]
        assert data[0]["synthetic"] is True
        command(
            "unpublish",
            "--record-id",
            identity,
            "--fields",
            "release_year",
            "--reviewer",
            "pilot-publisher",
            "--reason",
            "Withdraw year",
        )
        assert published()[0]["releases"][0]["release_year"] is None
        command(
            "revoke",
            "--source",
            manifest["source_id"],
            "--reviewer",
            "pilot-publisher",
            "--reason",
            "End fictional pilot",
        )
        assert published() == []


def test_public_request_uses_one_postgresql_snapshot() -> None:
    import asyncio
    from uuid import uuid4

    from fastapi import Request
    from fraggy_api.database import create_engine, get_session, request_session_factory
    from fraggy_api.models import DataSource
    from sqlalchemy import delete, func, select, text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    with disposable_database() as url:
        migrate(url, "upgrade", "head")

        async def verify() -> None:
            engine = create_engine(Settings(database_url=SecretStr(url)))
            factory = async_sessionmaker(engine, expire_on_commit=False)
            app = create_app(Settings(app_env="test"))
            app.state.session_factory = request_session_factory(engine)
            request = Request({"type": "http", "app": app})
            identity = uuid4()
            dependency = get_session(request)
            try:
                reader = await anext(dependency)
                assert (
                    await reader.scalar(text("SHOW transaction_isolation"))
                    == "repeatable read"
                )
                count = (
                    select(func.count())
                    .select_from(DataSource)
                    .where(DataSource.id == identity)
                )
                assert await reader.scalar(count) == 0
                async with factory() as writer, writer.begin():
                    writer.add(
                        DataSource(
                            id=identity,
                            key="snapshot-test",
                            name="Fictional Snapshot",
                            website="https://example.invalid/",
                            source_type="synthetic_file_import",
                        )
                    )
                # An operator may commit between public projection queries. This
                # response keeps its original snapshot; the next request sees it.
                assert await reader.scalar(count) == 0
                await dependency.aclose()
                dependency = get_session(request)
                next_reader = await anext(dependency)
                assert await next_reader.scalar(count) == 1
            finally:
                await dependency.aclose()
                async with factory() as cleanup, cleanup.begin():
                    await cleanup.execute(
                        delete(DataSource).where(DataSource.id == identity)
                    )
                await engine.dispose()

        asyncio.run(verify())
