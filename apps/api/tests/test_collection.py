"""Original fictional HTTP fixtures; external perfume collection is never enabled."""

import asyncio
import csv
import io
import json
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from conftest import disposable_database, migrate
from fraggy_api.collection.adapters import extract
from fraggy_api.collection.engine import Collector, activate, cancel, revoke_collection
from fraggy_api.collection.policy import (
    CollectionError,
    Endpoint,
    Grant,
    review_collection,
    source_pair,
)
from fraggy_api.collection.transport import HTTPTransport
from fraggy_api.database import create_engine
from fraggy_api.importing.authorization import review_source, revoke
from fraggy_api.importing.formats import manifest_file
from fraggy_api.importing.pipeline import decide, publish
from fraggy_api.models import (
    CollectionRun,
    CollectionSource,
    SourceRecord,
)
from fraggy_api.settings import Settings
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from test_attribution import credit
from test_import_pipeline import PUBLIC_FIELDS, public, review_id

EXAMPLES = Path(__file__).resolve().parents[3] / "data/examples"


def fictional(number=1):
    return {
        "source_record_id": f"original-{number}",
        "source_url": f"https://example.invalid/original/{number}",
        "brand_name": "Invented Collection Observatory",
        "fragrance_name": "Imaginary Cedar Orbit",
        "concentration": "EDP" if number == 1 else "EDT",
        "release_year": 2024,
        "version_label": "Original" if number == 1 else "Separate concentration",
        "notes": [{"name": "Cedar", "position": "base"}],
        "accords": ["Woody"],
        "perfumers": ["Invented Workshop Perfumer"],
        "bottle_sizes_ml": [50, 100],
    }


class Clock:
    def __init__(self):
        self.value = datetime.now(UTC)
        self.waits = []

    def now(self):
        return self.value

    async def sleep(self, seconds):
        self.waits.append(seconds)
        self.value += timedelta(seconds=seconds)
        await asyncio.sleep(0)


@pytest.fixture
def server():
    state = SimpleNamespace(
        requests=[], responses=[], records=[fictional(1), fictional(2)], etag=None
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            query = parse_qs(urlsplit(self.path).query)
            state.requests.append(
                {"query": query, "if_none_match": self.headers.get("If-None-Match")}
            )
            if state.responses:
                status, body, headers = state.responses.pop(0)
            elif state.etag and self.headers.get("If-None-Match") == state.etag:
                status, body, headers = 304, b"", {}
            else:
                second = query.get("cursor") == ["page-2"]
                payload = {
                    "records": [state.records[1 if second else 0]],
                    "next_cursor": None if second else "page-2",
                    "watermark": "v1",
                }
                status, body, headers = (
                    200,
                    json.dumps(payload).encode(),
                    {"Content-Type": "application/json"},
                )
                if state.etag:
                    headers["ETag"] = state.etag
            self.send_response(status)
            for name, value in headers.items():
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    state.url = f"http://127.0.0.1:{http.server_port}/catalog"
    try:
        yield state
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)


@pytest.fixture(scope="module")
def collection_url():
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        yield url


@pytest_asyncio.fixture
async def environment(collection_url, server):
    engine = create_engine(
        Settings(app_env="test", database_url=SecretStr(collection_url))
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    manifest = manifest_file(EXAMPLES / "source-manifest.json").model_copy(
        update={
            "source_id": "fictional-collector-" + uuid4().hex,
            "synthetic": True,
            "attribution_requirements": ["Adjacent original fictional source credit"],
            "attribution": credit(),
        }
    )
    instant = datetime.now(UTC)
    grant = Grant(
        manifest=manifest,
        endpoint=Endpoint(
            url=server.url, adapter="rest_json", minimum_interval_seconds=0.01
        ),
        automated_access=True,
        database_storage=True,
        commercial_reuse=True,
        api_redistribution=True,
        attribution_accepted=True,
        access_restrictions=["GET only; original local fixture; no external requests"],
        evidence={
            name: "Original fictional fixture permission, not an external license"
            for name in (
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
        expires_at=instant + timedelta(days=1),
    )
    async with factory.begin() as session:
        source = await review_source(
            session,
            manifest,
            "fixture-operator",
            "Original invented fixture review",
            allow_storage=True,
            publish_fields=PUBLIC_FIELDS,
            accept_attribution=True,
        )
        config = await review_collection(
            session,
            grant,
            "fixture-operator",
            "Original local HTTP collection approval",
        )
        identity, source_id = config.id, source.id
    clock = Clock()
    collector = Collector(factory, clock=clock.now, sleep=clock.sleep)
    env = SimpleNamespace(
        factory=factory,
        grant=grant,
        manifest=manifest,
        identity=identity,
        source_id=source_id,
        collector=collector,
        clock=clock,
        server=server,
    )
    try:
        yield env
    finally:
        async with factory.begin() as session:
            await revoke_collection(
                session, identity, "fixture-operator", "End original fixture permission"
            )
            await revoke(
                session,
                manifest.source_id,
                "fixture-operator",
                "End original fixture test",
            )
        await engine.dispose()


async def enable(env, **kwargs):
    async with env.factory.begin() as session:
        await activate(
            session,
            env.identity,
            "fixture-operator",
            "Explicit original fixture activation",
            **kwargs,
        )
    env.clock.value = max(env.clock.value, datetime.now(UTC))


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/private",
        "https://user:password@example.invalid/a",
        "https://example.invalid/a?token=secret",
        "https://example.invalid/#fragment",
        "http://",
        "https://example.invalid/\nsecret",
    ],
)
def test_endpoint_rejects_unreviewed_url_components(url):
    with pytest.raises(ValidationError):
        Endpoint(url=url, adapter="json_feed", minimum_interval_seconds=1)


@pytest.mark.parametrize("kind", ["rest_json", "json_feed", "csv_feed", "html_json"])
def test_adapter_shapes_preserve_source_identity_and_concentration(kind):
    row = fictional()
    endpoint = Endpoint(
        url="http://127.0.0.1:1234/catalog", adapter=kind, minimum_interval_seconds=1
    )
    if kind == "csv_feed":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(
            {k: json.dumps(v) if isinstance(v, list) else v for k, v in row.items()}
        )
        body, content_type = output.getvalue().encode(), "text/csv; charset=utf-8"
    elif kind == "html_json":
        body = (
            '<html><script id="fragrance-data" type="application/json">'
            + json.dumps([row])
            + "</script></html>"
        ).encode()
        content_type = "text/html"
    else:
        body, content_type = json.dumps([row]).encode(), "application/json"
    page = extract(body, endpoint, content_type)
    assert page.records[0].source_record_id == "original-1"
    assert (
        page.records[0].concentration == "EDP"
    )  # Existing materializer owns canonical normalization.
    assert page.records[0].bottle_sizes_ml == [50, 100]
    assert page.records[0].perfumers == ["Invented Workshop Perfumer"]


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"concentration": "invented concentration"},
        {"notes": ["not positioned metadata"]},
        {"bottle_sizes_ml": [-1]},
        {"brand_name": "\t"},
    ],
)
def test_malformed_records_are_rejected_without_inventing_defaults(bad):
    endpoint = Endpoint(
        url="http://127.0.0.1:1234/catalog",
        adapter="rest_json",
        minimum_interval_seconds=1,
    )
    row = {} if not bad else {**fictional(), **bad}
    with pytest.raises(CollectionError, match="malformed_page"):
        extract(json.dumps([row]).encode(), endpoint, "application/json")


async def test_disabled_sources_deny_network_and_schedule_by_default(environment):
    env = environment
    assert await env.collector.tick() == []
    with pytest.raises(CollectionError, match="not_authorized"):
        await env.collector.run(env.identity)
    assert env.server.requests == []


@pytest.mark.parametrize(
    "field",
    [
        "automated_access",
        "database_storage",
        "commercial_reuse",
        "api_redistribution",
        "attribution_accepted",
    ],
)
async def test_authorization_requires_every_permission(environment, field):
    with pytest.raises(ValidationError):
        Grant.model_validate(
            {**environment.grant.model_dump(mode="json"), field: False}
        )
    assert environment.server.requests == []


@pytest.mark.parametrize(
    "change",
    [
        "expired",
        "future",
        "tampered",
        "revoked",
        "storage_withdrawn",
        "manifest_changed",
    ],
)
async def test_stale_inconsistent_or_revoked_policy_fails_closed(environment, change):
    env = environment
    await enable(env)
    async with env.factory.begin() as session:
        config, source = await source_pair(session, env.identity, lock=True)
        if change == "expired":
            env.clock.value += timedelta(days=2)
        elif change == "future":
            env.clock.value -= timedelta(days=2)
        elif change == "tampered":
            config.configuration = {
                **config.configuration,
                "endpoint": {
                    **config.configuration["endpoint"],
                    "url": "https://evil.invalid/",
                },
            }
        elif change == "revoked":
            await revoke_collection(
                session,
                env.identity,
                "fixture-operator",
                "Withdraw original fixture permission",
            )
        elif change == "storage_withdrawn":
            await review_source(
                session,
                env.manifest,
                "fixture-operator",
                "Withdraw storage",
                allow_storage=False,
                publish_fields=[],
            )
        else:
            source.evidence = []
    with pytest.raises(CollectionError, match="not_authorized"):
        await env.collector.run(env.identity)
    assert env.server.requests == []


async def test_external_transport_denies_before_dns(environment, monkeypatch):
    import socket

    grant = environment.grant.model_copy(
        update={
            "manifest": environment.manifest.model_copy(update={"synthetic": False}),
            "endpoint": environment.grant.endpoint.model_copy(
                update={"url": "https://example.invalid/catalog"}
            ),
        }
    )
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: pytest.fail("DNS must not be called"),
    )
    with pytest.raises(CollectionError, match="external_network_disabled"):
        await HTTPTransport().fetch(grant, None, None, None)


async def test_pagination_idempotency_incremental_changes_and_conditional_requests(
    environment,
):
    env = environment
    await enable(env)
    first = await env.collector.run(env.identity)
    assert (
        first["status"] == "succeeded"
        and first["records_staged"] == 2
        and first["pages"] == 2
    )
    assert env.server.requests[1]["query"]["cursor"] == ["page-2"]
    again = await env.collector.run(env.identity)
    assert again["records_unchanged"] == 2 and again["records_staged"] == 0
    assert env.server.requests[2]["query"]["since"] == ["v1"]
    env.server.records[0] = {**fictional(), "release_year": 2025}
    changed = await env.collector.run(env.identity)
    assert changed["records_staged"] == 1 and changed["records_unchanged"] == 1
    async with env.factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SourceRecord)
                .where(SourceRecord.source_id == env.source_id)
            )
            == 3
        )
    env.server.etag = '"fictional-v1"'
    env.server.responses = [
        (
            200,
            json.dumps({"records": env.server.records, "watermark": "v1"}).encode(),
            {"Content-Type": "application/json", "ETag": env.server.etag},
        )
    ]
    await env.collector.run(env.identity)
    conditional = await env.collector.run(env.identity)
    assert (
        conditional["status"] == "succeeded"
        and conditional["pages"] == 0
        and conditional["records_staged"] == 0
    )
    assert env.server.requests[-1]["if_none_match"] == '"fictional-v1"'


async def test_rate_limits_retry_backoff_and_retry_budget(environment):
    env = environment
    env.server.responses = [
        (503, b"untrusted upstream error", {"Content-Type": "text/plain"}),
        (429, b"", {"Retry-After": "2"}),
    ]
    await enable(env)
    result = await env.collector.run(env.identity)
    assert result["status"] == "succeeded" and result["attempts"] == 4
    assert sum(env.clock.waits) >= 3
    assert [e["code"] for e in result["errors"]] == [
        "transient_retry",
        "transient_retry",
    ]
    env.server.responses = [(503, b"private data must not escape", {})] * 3
    failed = await env.collector.run(env.identity)
    assert failed["status"] == "failed" and failed["attempts"] == 3
    assert failed["errors"][-1]["code"] == "retry_exhausted"
    assert "private" not in json.dumps(failed)


async def test_page_rollback_checkpoint_resume_and_partial_schedule(environment):
    env = environment
    async with env.factory.begin() as session:
        grant = env.grant.model_copy(
            update={"endpoint": env.grant.endpoint.model_copy(update={"max_pages": 1})}
        )
        await review_collection(
            session, grant, "fixture-operator", "Limit original fixture pages"
        )
    await enable(env, schedule=True, interval=60)
    partial = (await env.collector.tick())[0]
    assert partial["status"] == "partial" and partial["records_staged"] == 1
    assert await env.collector.tick() == []
    env.clock.value += timedelta(seconds=61)
    env.server.responses = [
        (
            200,
            b'{"records":[{"secret":"invalid"}]}',
            {"Content-Type": "application/json"},
        )
    ]
    failed = (await env.collector.tick())[0]
    assert failed["status"] == "failed" and failed["records_staged"] == 0
    async with env.factory() as session:
        config = await session.get(CollectionSource, env.identity)
        assert config.checkpoint["cursor"] == "page-2"
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SourceRecord)
                .where(SourceRecord.source_id == env.source_id)
            )
            == 1
        )
    env.clock.value += timedelta(seconds=61)
    resumed = (await env.collector.tick())[0]
    assert resumed["status"] == "succeeded" and resumed["records_staged"] == 1


async def test_concurrent_claims_expired_lease_fencing_and_cancellation(environment):
    env = environment
    await enable(env)
    claims = await asyncio.gather(
        env.collector.claim(env.identity), env.collector.claim(env.identity)
    )
    assert sum(identity is not None for identity in claims) == 1
    old = next(identity for identity in claims if identity)
    env.clock.value += timedelta(seconds=61)
    fresh = await env.collector.claim(env.identity)
    assert fresh and fresh != old
    stale = await env.collector.execute(env.identity, old)
    assert stale["status"] == "interrupted" and env.server.requests == []
    async with env.factory.begin() as session:
        await cancel(session, fresh, "fixture-operator", "Cancel original fixture run")
    cancelled = await env.collector.execute(env.identity, fresh)
    assert cancelled["status"] == "cancelled" and env.server.requests == []
    assert (await env.collector.run(env.identity))["status"] == "succeeded"


@pytest.mark.parametrize("withdrawal", ["collection", "publication", "storage"])
async def test_revocation_during_response_discards_page_before_storage(
    environment, withdrawal
):
    env = environment
    await enable(env)

    class RevokingTransport(HTTPTransport):
        async def fetch(self, *args):
            response = await super().fetch(*args)
            async with env.factory.begin() as session:
                if withdrawal == "collection":
                    await revoke_collection(
                        session,
                        env.identity,
                        "fixture-operator",
                        "Withdraw original fixture permission",
                    )
                elif withdrawal == "publication":
                    await revoke(
                        session,
                        env.manifest.source_id,
                        "fixture-operator",
                        "Withdraw original fictional publication",
                    )
                else:
                    await review_source(
                        session,
                        env.manifest,
                        "fixture-operator",
                        "Withdraw original fictional storage",
                        allow_storage=False,
                        publish_fields=[],
                    )
            return response

    worker = Collector(
        env.factory, RevokingTransport(), clock=env.clock.now, sleep=env.clock.sleep
    )
    result = await worker.run(env.identity)
    assert (
        result["status"] == ("cancelled" if withdrawal == "collection" else "failed")
        and result["records_staged"] == 0
    )
    async with env.factory() as session:
        assert (
            await session.scalar(
                select(func.count())
                .select_from(SourceRecord)
                .where(SourceRecord.source_id == env.source_id)
            )
            == 0
        )


async def test_scheduled_http_to_manual_publication_api_quality_and_revocation(
    environment,
):
    env = environment
    await enable(env, schedule=True, interval=60)
    result = (await env.collector.tick())[0]
    assert result["status"] == "succeeded" and result["records_staged"] == 2
    async with env.factory.begin() as session:
        pending = list(
            (
                await session.scalars(
                    select(SourceRecord)
                    .where(SourceRecord.source_id == env.source_id)
                    .order_by(SourceRecord.source_record_id)
                )
            ).all()
        )
        assert len(pending) == 2
        assert (await public(session, demo=True))["data"] == []
        decisions = []
        for record in pending:
            decision = await decide(
                session,
                await review_id(session, str(record.id)),
                "approve_new",
                "fixture-operator",
                "New original fictional concentration",
            )
            decisions.append(decision)
        assert (await public(session, demo=True))["data"] == []
        for record in pending:
            await publish(
                session,
                record.id,
                PUBLIC_FIELDS,
                "fixture-operator",
                "Explicit fictional field publication",
            )
        response = await public(session, demo=True)
        assert len(response["data"]) == 2
        assert {f["releases"][0]["concentration"] for f in response["data"]} == {
            "eau_de_parfum",
            "eau_de_toilette",
        }
        assert all(f["attributions"] and f["synthetic"] for f in response["data"])
        assert (await public(session, demo=True, production=True))["data"] == []
    report = await env.collector.quality()
    assert report["complete"] and report["automatic_changes"] == 0
    async with env.factory.begin() as session:
        await revoke(
            session,
            env.manifest.source_id,
            "fixture-operator",
            "Withdraw fictional redistribution",
        )
        await revoke_collection(
            session,
            env.identity,
            "fixture-operator",
            "Withdraw original fixture permission",
        )
        assert (await public(session, demo=True))["data"] == []
    with pytest.raises(CollectionError):
        await env.collector.run(env.identity)


async def test_worker_task_interruption_releases_lease_without_staging(environment):
    env = environment
    await enable(env)
    entered = asyncio.Event()

    class BlockedTransport(HTTPTransport):
        async def fetch(self, *args):
            entered.set()
            await asyncio.Event().wait()

    worker = Collector(
        env.factory, BlockedTransport(), clock=env.clock.now, sleep=env.clock.sleep
    )
    task = asyncio.create_task(worker.run(env.identity))
    await asyncio.wait_for(entered.wait(), timeout=5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with env.factory() as session:
        config = await session.get(CollectionSource, env.identity)
        assert config.current_run_id is None and config.lease_until is None
        run = await session.scalar(
            select(CollectionRun).where(CollectionRun.collection_id == env.identity)
        )
        assert run.status == "cancelled" and run.records_staged == 0
    assert (await env.collector.run(env.identity))["status"] == "succeeded"


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404])
async def test_redirects_and_access_denials_are_not_followed_or_retried(
    environment, status
):
    env = environment
    env.server.responses = [
        (status, b"", {"Location": "https://unapproved.invalid/private"})
    ]
    await enable(env)
    result = await env.collector.run(env.identity)
    assert result["status"] == "failed" and result["attempts"] == 1
    assert len(env.server.requests) == 1 and result["records_staged"] == 0
    assert result["errors"][-1]["code"] == "http_status_denied"


async def test_server_retry_after_defers_future_runs_without_evading_limit(environment):
    env = environment
    env.server.responses = [(429, b"", {"Retry-After": "3600"})]
    await enable(env, schedule=True)
    failed = await env.collector.run(env.identity)
    assert failed["status"] == "failed" and failed["attempts"] == 1
    assert (await env.collector.run(env.identity))["status"] == "not_claimed"
    assert len(env.server.requests) == 1
    async with env.factory() as session:
        config = await session.get(CollectionSource, env.identity)
        assert config.next_request_at >= env.clock.now() + timedelta(seconds=3599)
        assert config.next_due_at >= config.next_request_at


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.1", "::1", "169.254.169.254", "fc00::1"]
)
async def test_real_transport_blocks_private_dns_even_with_external_opt_in(
    environment, monkeypatch, address
):
    import socket

    env = environment
    grant = env.grant.model_copy(
        update={
            "manifest": env.manifest.model_copy(update={"synthetic": False}),
            "endpoint": env.grant.endpoint.model_copy(
                update={"url": "https://example.invalid/catalog"}
            ),
        }
    )
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *args, **kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", (address, 443))
        ],
    )
    with pytest.raises(CollectionError, match="network_address_denied"):
        await HTTPTransport(allow_external=True).fetch(grant, None, None, None)
    assert env.server.requests == []


async def test_source_field_map_drops_unlicensed_narrative_and_preserves_identity():
    endpoint = Endpoint(
        url="http://127.0.0.1:1234/catalog",
        adapter="json_feed",
        minimum_interval_seconds=1,
        field_map={
            "source_record_id": "id",
            "brand_name": "house",
            "fragrance_name": "product",
        },
    )
    page = extract(
        json.dumps(
            [
                {
                    "id": "original-mapped",
                    "house": "Invented House",
                    "product": "Imagined Product",
                    "review": "Unlicensed prose must not be staged",
                }
            ]
        ).encode(),
        endpoint,
        "application/json",
    )
    assert (
        page.records[0].concentration is None and page.records[0].release_year is None
    )
    assert "review" not in page.records[0].model_dump()


async def test_page_quality_reuses_phase_2e_rules_and_is_explicitly_bounded():
    from fraggy_api.collection.quality import assess
    from fraggy_api.importing.formats import Record

    a = Record.model_validate({**fictional(), "version_label": None})
    b = Record.model_validate({**fictional(2), "version_label": None})
    report = assess([a, b])
    assert report["pair_classifications"] == {"distinct_concentration": 1}
    limited = assess([a] * 60)
    assert not limited["complete"] and limited["candidate_pairs_examined"] == 1000


async def test_cli_monitoring_uses_sanitized_output_and_production_guard(environment):
    from fraggy_api.collection.cli import run

    env = environment
    await enable(env)
    result = await env.collector.run(env.identity)
    summary = await env.collector.summary(UUID(result["run_id"]))
    assert summary["quality"]["records"] == 2
    assert env.server.url not in json.dumps(summary)
    with pytest.raises(
        CollectionError, match="nonproduction_loopback_database_required"
    ):
        import os
        from unittest.mock import patch

        with patch.dict(os.environ, {"APP_ENV": "production"}):
            await run(SimpleNamespace(command="list"))
