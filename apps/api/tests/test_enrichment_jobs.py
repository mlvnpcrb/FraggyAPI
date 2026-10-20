"""Real local collector leases and staging, no external provider requests."""

# ruff: noqa: F811

import asyncio
from datetime import timedelta

import pytest
from fraggy_api.collection.enrichment import request_intent, run_intent
from fraggy_api.collection.policy import review_collection
from fraggy_api.models import CollectionRun, EnrichmentIntent, Fragrance, SourceRecord
from sqlalchemy import func, select
from test_collection import collection_url, enable, environment, server  # noqa: F401, F811


async def bounded(env):
    grant = env.grant.model_copy(
        update={
            "endpoint": env.grant.endpoint.model_copy(
                update={"max_pages": 2, "retries": 0}
            )
        }
    )
    async with env.factory.begin() as session:
        await review_collection(
            session, grant, "fixture-operator", "Bounded original enrichment fixture"
        )
    await enable(env, interval=60)
    return grant


async def intent(env):
    async with env.factory.begin() as session:
        row = await request_intent(
            session, env.manifest.source_id, "Imaginary Cedar Orbit", env.clock.now()
        )
        return row.id


async def test_existing_collector_runs_once_stages_and_preserves_review(environment):
    env = environment
    await bounded(env)
    identity = await intent(env)
    results = await asyncio.gather(
        run_intent(env.collector, identity), run_intent(env.collector, identity)
    )
    assert any(item.get("status") == "succeeded" for item in results)
    assert len(env.server.requests) == 2
    async with env.factory() as session:
        row = await session.get(EnrichmentIntent, identity)
        assert row.status == "review" and row.collection_run_id
        assert (
            await session.scalar(select(func.count()).select_from(CollectionRun)) == 1
        )
        assert await session.scalar(select(func.count()).select_from(SourceRecord)) == 2
        assert await session.scalar(select(func.count()).select_from(Fragrance)) == 0
    again = await run_intent(env.collector, identity)
    assert again["status"] == "review"
    assert len(env.server.requests) == 2


async def test_intents_deduplicate_under_concurrent_transactions(environment):
    env = environment

    async def enqueue():
        async with env.factory.begin() as session:
            return (
                await request_intent(
                    session, "openbeautyfacts", "Lattafa Khamrah", env.clock.now()
                )
            ).id

    assert len(set(await asyncio.gather(*(enqueue() for _ in range(4))))) == 1
    identity = await enqueue()
    result = await run_intent(env.collector, identity)
    assert result["diagnostic"] == "provider_collection_not_configured"
    assert env.server.requests == []


async def test_budget_and_source_cooldown_prevent_dispatch(environment):
    env = environment
    await enable(env)
    identity = await intent(env)
    result = await run_intent(env.collector, identity)
    assert result["diagnostic"] == "enrichment_request_budget_exceeded"
    assert env.server.requests == []
    await bounded(env)
    async with env.factory.begin() as session:
        row = await session.get(EnrichmentIntent, identity)
        row.status = "pending"
        from fraggy_api.models import CollectionSource

        config = await session.get(CollectionSource, env.identity)
        config.next_due_at = env.clock.now() + timedelta(hours=1)
    assert (await run_intent(env.collector, identity))[
        "diagnostic"
    ] == "enrichment_source_cooldown"
    assert env.server.requests == []


async def test_external_enrichment_is_blocked_even_after_other_authorization(
    session, monkeypatch
):
    from datetime import UTC, datetime
    from types import SimpleNamespace

    from fraggy_api.collection.enrichment import admit
    from fraggy_api.collection.policy import CollectionError

    at = datetime.now(UTC)
    identity = (
        await request_intent(session, "openbeautyfacts", "Lattafa Khamrah", at)
    ).id
    monkeypatch.setattr(
        "fraggy_api.collection.enrichment.authorize",
        lambda *args: SimpleNamespace(manifest=SimpleNamespace(synthetic=False)),
    )
    with pytest.raises(CollectionError, match="provider_live_disabled"):
        await admit(
            session,
            identity,
            SimpleNamespace(),
            SimpleNamespace(key="openbeautyfacts"),
            at,
        )


async def test_expired_collector_lease_can_resume_same_intent_without_new_lease_system(
    environment,
):
    env = environment
    await bounded(env)
    identity = await intent(env)
    old_run = await env.collector.claim(env.identity, enrichment_intent_id=identity)
    assert old_run
    env.clock.value += timedelta(seconds=61)
    result = await run_intent(env.collector, identity)
    assert result["status"] == "succeeded"
    async with env.factory() as session:
        assert (await session.get(CollectionRun, old_run)).status == "interrupted"
        row = await session.get(EnrichmentIntent, identity)
        assert row.status == "review" and row.collection_run_id != old_run


async def test_daily_attempt_budget_is_enforced_across_intents(environment):
    env = environment
    await bounded(env)
    identity = await intent(env)
    assert (await run_intent(env.collector, identity))["status"] == "succeeded"
    # Each 2-page run reserves 2 attempts. A third would exceed 4/day.
    for expected in ("succeeded", "blocked"):
        env.clock.value += timedelta(hours=2)
        async with env.factory.begin() as session:
            await request_intent(
                session,
                env.manifest.source_id,
                "Imaginary Cedar Orbit",
                env.clock.now(),
            )
        result = await run_intent(env.collector, identity)
        assert result["status"] == expected
    assert result["diagnostic"] == "enrichment_request_budget_exceeded"
    assert len(env.server.requests) == 4
