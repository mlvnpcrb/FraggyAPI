"""Real operator commands against a migrated, disposable PostgreSQL database."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
from conftest import disposable_database, migrate
from fastapi.testclient import TestClient
from fraggy_api.main import create_app
from fraggy_api.settings import Settings
from pydantic import SecretStr
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "data/examples"


def test_cli_smoke_import_review_publication_and_revoke() -> None:
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        environment = {
            **os.environ,
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "APP_ENV": "test",
        }

        def command(*args: str) -> dict:
            result = subprocess.run(
                [sys.executable, "-m", "fraggy_api.importing.cli", *args],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(result.stdout)

        async def count_records() -> int:
            connection = await asyncpg.connect(
                make_url(url)
                .set(drivername="postgresql")
                .render_as_string(hide_password=False)
            )
            try:
                return await connection.fetchval("SELECT count(*) FROM source_records")
            finally:
                await connection.close()

        manifest, file = (
            str(EXAMPLES / "source-manifest.json"),
            str(EXAMPLES / "fragrances.csv"),
        )
        assert (
            command(
                "import", "--", "--file", file, "--manifest", manifest, "--dry-run"
            )["dry_run"]
            is True
        )
        assert asyncio.run(count_records()) == 0
        fields = (
            "name,slug,brand_id,fragrance_id,concentration,release_year,notes,accords"
        )
        assert (
            command(
                "source-review",
                "--manifest",
                manifest,
                "--allow-storage",
                "--publish-fields",
                fields,
                "--reviewer",
                "smoke-operator",
                "--reason",
                "Reviewed original fictional fixture",
            )["storage_authorization"]
            == "synthetic"
        )
        imported = command(
            "import", "--file", file, "--manifest", manifest, "--batch-size", "1"
        )
        run = imported["batches"][0]
        identity = run["records"][0]
        assert imported["summary"]["inserted"] == 1
        assert command("results", "--run-id", run["run_id"])["accepted"] == 1
        assert (
            command("inspect", "--record-id", identity)["payload"]["original"][
                "brand_name"
            ]
            == "Maison Élan Imaginaire"
        )
        pending = command("pending", "--source", "fictional-workshop-import")["reviews"]
        assert len(pending) == 1
        reviewed = command(
            "review",
            "--review-id",
            pending[0]["id"],
            "--decision",
            "approve_new",
            "--reviewer",
            "smoke-operator",
            "--reason",
            "Confirmed invented identities",
        )
        assert reviewed["inserted"] == 1
        # Even after canonical review, no publication takes place implicitly.
        with TestClient(
            create_app(
                Settings(database_url=SecretStr(url), catalog_include_synthetic=True)
            )
        ) as client:
            assert client.get("/api/v1/fragrances").json()["data"] == []
        assert (
            command(
                "publish",
                "--record-id",
                identity,
                "--fields",
                fields,
                "--reviewer",
                "smoke-publisher",
                "--reason",
                "Explicit fictional publication",
            )["approved_claims"]
            > 0
        )
        with TestClient(
            create_app(
                Settings(database_url=SecretStr(url), catalog_include_synthetic=True)
            )
        ) as client:
            data = client.get("/api/v1/fragrances").json()["data"]
            assert len(data) == 1 and data[0]["synthetic"] is True
            fragrance_id = data[0]["id"]
        assert command("provenance", "--fragrance-id", fragrance_id)["claims"]
        assert (
            command("source-status", "--source", "fictional-workshop-import")[
                "authorization"
            ]
            == "synthetic"
        )
        assert (
            command("import", "--file", file, "--manifest", manifest)["summary"][
                "skipped"
            ]
            == 1
        )
        command(
            "revoke",
            "--source",
            "fictional-workshop-import",
            "--reviewer",
            "smoke-publisher",
            "--reason",
            "Withdraw demo publication",
        )
        with TestClient(
            create_app(
                Settings(database_url=SecretStr(url), catalog_include_synthetic=True)
            )
        ) as client:
            assert client.get("/api/v1/fragrances").json()["data"] == []
        assert asyncio.run(count_records()) == 1
        print(
            "PASS CLI smoke: parse, dry-run, review source, stage, inspect, approve, publish, API, provenance, reimport, revoke"
        )


@pytest.mark.parametrize(
    "args",
    [
        ["import", "--file", "missing.json", "--manifest", "missing.json"],
        ["pending", "--limit", "101"],
        [
            "source-review",
            "--manifest",
            "data/examples/source-manifest.json",
            "--reviewer",
            "",
            "--reason",
            "review",
        ],
    ],
)
def test_cli_errors_are_safe(args: list[str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "fraggy_api.importing.cli", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    body = json.loads(result.stdout)
    assert "error" in body


def test_cli_refuses_production() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "fraggy_api.importing.cli", "pending"],
        cwd=ROOT,
        env={**os.environ, "APP_ENV": "production"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "non-production" in result.stdout


def test_cli_partial_batch_failure_can_resume(tmp_path: Path) -> None:
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        environment = {
            **os.environ,
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
            "APP_ENV": "test",
        }
        raw = json.loads((EXAMPLES / "source-manifest.json").read_text())
        raw["permitted_fields"].remove("source_url")
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps(raw))
        original = json.loads((EXAMPLES / "fragrances.json").read_text())[0]
        path = tmp_path / "input.json"
        path.write_text(
            json.dumps(
                [
                    original,
                    {
                        **original,
                        "source_record_id": "second",
                        "source_url": "https://example.invalid/not-permitted",
                    },
                ]
            )
        )

        def command(*args: str) -> subprocess.CompletedProcess:
            return subprocess.run(
                [sys.executable, "-m", "fraggy_api.importing.cli", *args],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
            )

        approved = command(
            "source-review",
            "--manifest",
            str(manifest),
            "--allow-storage",
            "--reviewer",
            "operator",
            "--reason",
            "Storage only",
        )
        assert approved.returncode == 0, approved.stdout
        failed = command(
            "import",
            "--file",
            str(path),
            "--manifest",
            str(manifest),
            "--batch-size",
            "1",
        )
        assert failed.returncode == 1
        report = json.loads(failed.stdout)
        assert (
            report["failed_batch_start_row"] == 2
            and report["completed_batches"][0]["inserted"] == 1
        )
        # Correct the second row, retaining its stable provider ID. The first batch
        # is skipped; no duplicate snapshot or canonical row is created on resume.
        path.write_text(
            json.dumps([original, {**original, "source_record_id": "second"}])
        )
        resumed = command(
            "import",
            "--file",
            str(path),
            "--manifest",
            str(manifest),
            "--batch-size",
            "1",
        )
        assert resumed.returncode == 0, resumed.stdout
        summary = json.loads(resumed.stdout)["summary"]
        assert summary["skipped"] == 1 and summary["inserted"] == 1
