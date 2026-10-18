"""Quality reports diagnose, never repair or authorize. All data is fictional."""

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from conftest import disposable_database, migrate
from fraggy_api.database import Base
from fraggy_api.importing.authorization import revoke
from fraggy_api.importing.formats import Manifest, Record
from fraggy_api.importing.pipeline import unpublish
from fraggy_api.models import (
    Brand,
    BrandAlias,
    Fragrance,
    FragranceRelease,
    SourceRecord,
)
from fraggy_api.quality.duplicates import classify_pair
from fraggy_api.quality.report import catalog_quality, human_report
from fraggy_api.seed import seed_demo
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from test_attribution import fictional_record as fictional_record
from test_attribution import licensed_manifest as licensed_manifest
from test_attribution import pilot
from test_import_pipeline import public


@pytest.mark.parametrize(
    "updates,expected",
    [
        ({}, "possible_duplicate"),
        ({"concentration": "eau_de_toilette"}, "distinct_concentration"),
        ({"concentration": "parfum"}, "distinct_concentration"),
        ({"year": None}, "incomplete_identity"),
        ({"concentration": None}, "incomplete_identity"),
        ({"year": 2025}, "distinct_year_review"),
        ({"version": "Reformulation"}, "distinct_version_review"),
        ({"reformulation": "prior-id"}, "distinct_version_review"),
        ({"name": "Paper Night"}, "related_name_review"),
        ({"name": "Unrelated"}, "different_name"),
        ({"brand": "Different"}, "different_brand"),
        ({"name": " "}, "incomplete_identity"),
        ({"brand": ""}, "incomplete_identity"),
    ],
)
def test_duplicate_distinctions(updates: dict, expected: str) -> None:
    base = {
        "brand": "Fictional Workshop",
        "name": "Paper Dawn",
        "concentration": "eau_de_parfum",
        "year": 2024,
    }
    assert classify_pair(base, {**base, **updates}) == expected


async def test_empty_report_has_defined_percentages(session: AsyncSession) -> None:
    report = await catalog_quality(session)
    assert report["totals"] == {
        "brands": 0,
        "fragrances": 0,
        "releases": 0,
        "notes": 0,
        "accords": 0,
        "awaiting_review": 0,
    }
    assert report["findings"] == [] and report["complete"] is True
    assert all(v["percent"] == 0.0 for v in report["missing_fields"].values())
    assert "read-only" in human_report(report)


async def test_quality_finds_missing_provenance_aliases_and_years_without_mutation(
    session: AsyncSession,
) -> None:
    a, b = (
        Brand(id=uuid4(), name="Invented A", slug="invented-a"),
        Brand(id=uuid4(), name="Invented B", slug="invented-b"),
    )
    session.add_all([a, b])
    await session.flush()
    session.add_all(
        [
            BrandAlias(brand_id=a.id, name="Shared Name"),
            BrandAlias(brand_id=b.id, name="Shared Name"),
            BrandAlias(brand_id=a.id, name="Invented B"),
        ]
    )
    line = Fragrance(id=uuid4(), name="Paper Dawn", slug="paper-dawn", brand_id=a.id)
    session.add(line)
    await session.flush()
    session.add_all(
        [
            FragranceRelease(
                fragrance_id=line.id, release_year=1100, concentration="eau_de_parfum"
            ),
            FragranceRelease(
                fragrance_id=line.id, release_year=1100, concentration="eau_de_parfum"
            ),
            FragranceRelease(
                fragrance_id=line.id, release_year=1100, concentration="eau_de_toilette"
            ),
            FragranceRelease(fragrance_id=line.id),
        ]
    )
    await session.flush()
    before = {
        t.name: await session.scalar(select(func.count()).select_from(t))
        for t in Base.metadata.sorted_tables
    }
    report = await catalog_quality(session)
    codes = {f["code"] for f in report["findings"]}
    assert {
        "ambiguous_brand_aliases",
        "shadowing_brand_aliases",
        "missing_provenance_fragrances",
        "implausible_year_fragrance_releases",
        "unknown_concentration",
    } <= codes
    assert {c["classification"] for c in report["duplicate_candidates"]} >= {
        "possible_duplicate",
        "distinct_concentration",
        "incomplete_identity",
    }
    assert all(not c["automatic_merge"] for c in report["duplicate_candidates"])
    assert (
        report["missing_fields"]["fragrance_releases.concentration"]["percent"] == 25.0
    )
    assert before == {
        t.name: await session.scalar(select(func.count()).select_from(t))
        for t in Base.metadata.sorted_tables
    }


async def test_seed_conflicts_unknowns_and_production_exclusion(
    session: AsyncSession,
) -> None:
    await seed_demo(session, allow_demo_data=True, publish_demo_catalog=True)
    report = await catalog_quality(session)
    assert (
        report["severity_counts"]["error"] == 0
    )  # Valid nullable composite FKs are not broken.
    assert report["totals"]["fragrances"] == 4
    assert report["publication_eligibility"]["fragrances_development"] == 4
    assert report["publication_eligibility"]["fragrances_production"] == 0
    assert any(f["code"] == "conflicting_source_claim" for f in report["findings"])
    assert report["totals"]["awaiting_review"] > 0
    assert "evidence" not in json.dumps(report) and "reviewer" not in json.dumps(report)


async def test_quality_tracks_attribution_rights_and_withdrawal(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    identity, release_id = await pilot(session, licensed_manifest, fictional_record)
    report = await catalog_quality(session)
    assert report["attribution_coverage"] == {
        "sources_requiring_credit": 1,
        "sources_with_supported_credit": 1,
    }
    assert report["publication_eligibility"]["fragrances_production"] == 1
    await unpublish(session, identity, ["release_year"], "operator", "Withdraw year")
    report = await catalog_quality(session)
    assert report["publication_eligibility"]["selected_claims_blocked"] > 0
    assert (await public(session))["data"][0]["releases"][0]["release_year"] is None
    release = await session.get(FragranceRelease, release_id)
    assert release is not None
    release.release_year = 2025
    await session.flush()
    assert any(
        f["code"] == "stale_claim_fragrance_releases"
        for f in (await catalog_quality(session))["findings"]
    )
    await revoke(session, licensed_manifest.source_id, "operator", "Withdraw source")
    report = await catalog_quality(session)
    assert report["publication_eligibility"]["fragrances_production"] == 0
    assert (await public(session))["data"] == []
    assert not any(
        f["code"] == "missing_or_unsupported_attribution" for f in report["findings"]
    )
    assert all(
        term not in json.dumps(report)
        for term in ["PRIVATE_LEGAL_NOTE", "PRIVATE_FIELD_NOTE", "private-reviewer"]
    )


def test_actual_quality_cli_is_read_only_json_and_text() -> None:
    root = Path(__file__).resolve().parents[3]
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        environment = {
            **os.environ,
            "APP_ENV": "test",
            "DATABASE_URL": url,
            "MIGRATION_DATABASE_URL": url,
        }
        for format in ("json", "text"):
            result = subprocess.run(
                [sys.executable, "-m", "fraggy_api.quality.cli", "--format", format],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            if format == "json":
                assert json.loads(result.stdout)["automatic_changes"] == 0
            else:
                assert "fragrances: 0" in result.stdout
        # A malicious production/remote configuration is rejected before checkout.
        for update in (
            {"APP_ENV": "production"},
            {
                "DATABASE_URL": "postgresql+asyncpg://invalid:invalid@remote.invalid/invalid"
            },
        ):
            result = subprocess.run(
                [sys.executable, "-m", "fraggy_api.quality.cli"],
                cwd=root,
                env={**environment, **update},
                capture_output=True,
                text=True,
            )
            assert result.returncode == 1
            assert "require non-production loopback" in result.stdout
            assert "remote.invalid" not in result.stdout


async def test_missing_credit_and_unsafe_url_are_sanitized(
    session: AsyncSession, licensed_manifest: Manifest, fictional_record: Record
) -> None:
    from fraggy_api.models import DataSource, SourceRecord

    identity, _ = await pilot(session, licensed_manifest, fictional_record)
    source = await session.scalar(
        select(DataSource).where(DataSource.key == licensed_manifest.source_id)
    )
    assert source is not None
    events = [dict(e) for e in source.evidence]
    events[-1]["attribution_accepted"] = False
    source.evidence = events
    snapshot = await session.get(SourceRecord, identity)
    assert snapshot is not None
    snapshot.source_url = "javascript:private-untrusted-url"
    await session.flush()
    report = await catalog_quality(session)
    codes = {f["code"] for f in report["findings"]}
    assert {
        "missing_or_unsupported_attribution",
        "unsafe_public_url_source_records_source_url",
        "unapproved_publication_permission",
    } <= codes
    assert report["publication_eligibility"]["fragrances_production"] == 0
    assert "private-untrusted-url" not in json.dumps(report)
    assert report["attribution_coverage"]["sources_with_supported_credit"] == 0


async def test_quality_command_transaction_blocks_writes(
    catalog_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fraggy_api.quality import cli
    from sqlalchemy import insert
    from sqlalchemy.exc import DBAPIError

    monkeypatch.setenv("DATABASE_URL", catalog_url)
    monkeypatch.setenv("APP_ENV", "test")

    async def malicious(session: AsyncSession) -> dict:
        await session.execute(
            insert(Brand).values(
                id=uuid4(), name="Must Not Exist", slug="must-not-exist"
            )
        )
        return {}

    monkeypatch.setattr(cli, "catalog_quality", malicious)
    with pytest.raises(DBAPIError) as caught:
        await cli.run()
    assert getattr(caught.value.orig, "sqlstate", None) == "25006"


async def test_duplicate_limits_explicitly_mark_incomplete(
    session: AsyncSession,
) -> None:
    brand = Brand(id=uuid4(), name="Bounded House", slug="bounded-house")
    session.add(brand)
    await session.flush()
    line = Fragrance(
        id=uuid4(), brand_id=brand.id, name="Repeated Fable", slug="repeated-fable"
    )
    session.add(line)
    await session.flush()
    session.add_all(
        [
            FragranceRelease(
                fragrance_id=line.id, concentration="eau_de_parfum", release_year=2024
            )
            for _ in range(23)
        ]
    )
    await session.flush()
    report = await catalog_quality(session)
    assert report["complete"] is False
    assert report["duplicate_analysis"]["overflow_releases"] == 2
    assert len(report["duplicate_candidates"]) == 210


async def test_related_name_flankers_remain_separate(session: AsyncSession) -> None:
    brand = Brand(
        id=uuid4(), name="Invented Flanker House", slug="invented-flanker-house"
    )
    session.add(brand)
    await session.flush()
    session.add_all(
        [
            Fragrance(brand_id=brand.id, name=name, slug=slug)
            for name, slug in [
                ("Paper Horizon", "paper-horizon"),
                ("Paper Horizon Night", "paper-horizon-night"),
            ]
        ]
    )
    await session.flush()
    report = await catalog_quality(session)
    assert [r["classification"] for r in report["duplicate_candidates"]] == [
        "related_name_review"
    ]
    assert report["totals"]["fragrances"] == 2


async def test_benchmark_fixture_rights_filters_and_credit_deduplication(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    import fraggy_api.public_credits as credits
    from fraggy_api.catalog_api import CatalogQuery, catalog
    from fraggy_api.public_rights import read_access
    from fraggy_api.quality.benchmark_data import generate, identity

    # Fail promptly on a pathological plan; do not ANALYZE away the uncommitted
    # import state that exposed the regression in the full suite.
    await session.execute(text("SET LOCAL statement_timeout = '10s'"))
    fixture = await generate(session, 100)
    assert fixture["fragrances"] == 100 and fixture["releases"] == 210
    # Thousands of repeated underlying house/note claims collapse to distinct
    # authorized source/entity/field/value contributions before the credit cap.
    monkeypatch.setattr(credits, "MAX_CREDIT_CLAIMS", 1000)
    access = await read_access(session, True)
    page = await catalog(session, CatalogQuery(q="Cedar", limit=20), access)
    assert page.pagination.total == 50 and len(page.data) == 20
    assert all(f.synthetic and f.attributions for f in page.data)
    filtered = await catalog(
        session,
        CatalogQuery(
            concentration="eau_de_parfum", year=2020, notes=[identity("note:0")]
        ),
        access,
    )
    assert filtered.data
    for fragrance in filtered.data:
        assert any(
            r.concentration == "eau_de_parfum"
            and r.release_year == 2020
            and any(n.id == identity("note:0") for n in r.notes)
            for r in fragrance.releases
        )
    assert (await public(session, demo=True, production=True))["data"] == []
    with pytest.raises(ValueError, match="must be empty"):
        await generate(session, 100)


async def test_300_record_starter_import_batches_and_manual_publication(
    session: AsyncSession,
    licensed_manifest: Manifest,
    fictional_record: Record,
    tmp_path: Path,
) -> None:
    from fraggy_api.importing.formats import parse_file
    from fraggy_api.importing.pipeline import decide, preview, publish, stage
    from test_attribution import authorize
    from test_import_pipeline import PUBLIC_FIELDS, review_id

    manifest = licensed_manifest.model_copy(
        update={"source_id": "fictional-starter-300", "synthetic": True}
    )
    await authorize(session, manifest)
    rows = [
        fictional_record.model_copy(
            update={
                "source_record_id": f"starter-{i}",
                "fragrance_name": f"Invented Starter {i:03}",
                "concentration": ["EDP", "EDT", "Extrait"][i % 3],
            }
        ).model_dump(mode="json")
        for i in range(300)
    ]
    path = tmp_path / "original-fictional-starter.json"
    path.write_text(json.dumps(rows))
    records = parse_file(path)
    assert len(records) == 300
    assert (await preview(session, records, manifest))["canonical_writes"] == 0
    assert await session.scalar(select(func.count()).select_from(SourceRecord)) == 0
    staged = []
    for offset in range(0, 300, 100):
        batch = await stage(session, records[offset : offset + 100], manifest)
        assert batch["inserted"] == 100
        staged.extend(batch["records"])
    assert (await public(session, demo=True))["data"] == []
    for identity in staged[:3]:
        await decide(
            session,
            await review_id(session, identity),
            "approve_new",
            "starter-reviewer",
            "Reviewed original invented release",
        )
        await publish(
            session,
            UUID(identity),
            PUBLIC_FIELDS,
            "starter-publisher",
            "Verified invented fields and complete credits",
        )
    report = await catalog_quality(session)
    assert (
        report["totals"]["fragrances"] == 3
        and report["totals"]["awaiting_review"] == 297
    )
    assert report["source_coverage"][0]["records"] == 300
    page = (await public(session, demo=True))["data"]
    assert len(page) == 3 and all(p["attributions"] and p["synthetic"] for p in page)
    assert {r["concentration"] for p in page for r in p["releases"]} == {
        "eau_de_parfum",
        "eau_de_toilette",
        "extrait_de_parfum",
    }
    assert (await public(session, demo=True, production=True))["data"] == []
