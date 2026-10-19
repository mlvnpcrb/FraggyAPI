# ruff: noqa: F811 -- pytest registers the explicitly imported fixtures.
"""Existing synthetic local HTTP/database collector; no external source."""

import json

from fraggy_api.collection.policy import CollectionError
from test_collection import collection_url, enable, environment, server  # noqa: F401


async def test_operational_collector_access_denial_has_actionable_diagnostic(
    environment,
):
    env = environment
    env.server.responses = [(403, b"private restriction body", {})]
    await enable(env)
    result = await env.collector.run(env.identity)
    assert result["status"] == "failed" and result["attempts"] == 1
    assert result["diagnostics"][-1]["category"] == "access_restricted"
    assert result["source_health"]["health"] == "blocked"
    assert "private" not in json.dumps(result)


async def test_operational_timeout_retry_budget_and_health(environment, monkeypatch):
    env = environment

    async def timeout(*args, **kwargs):
        raise CollectionError("network_timeout")

    monkeypatch.setattr(env.collector.transport, "fetch", timeout)
    await enable(env)
    result = await env.collector.run(env.identity)
    assert result["status"] == "failed" and result["attempts"] == 3
    assert result["errors"][-1]["code"] == "retry_exhausted"
    assert result["diagnostics"][-1]["category"] == "network_timeout_or_failure"
    assert result["source_health"]["health"] == "degraded"
