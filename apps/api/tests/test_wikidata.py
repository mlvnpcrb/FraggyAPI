# ruff: noqa: F811 -- pytest registers explicitly imported fixtures by name.
"""Wikidata protocol fixtures contain exclusively invented Q IDs and names."""

import json
from datetime import UTC, datetime

import pytest
from fraggy_api.collection.adapters import extract
from fraggy_api.collection.engine import activate
from fraggy_api.collection.policy import CollectionError, Endpoint, review_collection
from fraggy_api.collection.transport import HTTPTransport
from fraggy_api.collection.wikidata import page_ids, query
from fraggy_api.importing.formats import digest
from fraggy_api.models import SourceRecord
from pydantic import ValidationError
from sqlalchemy import select
from test_collection import collection_url, server  # noqa: F401
from test_collection import environment as collection_environment  # noqa: F401
from test_import_pipeline import public


def endpoint(url="https://query.wikidata.org/sparql", size=100):
    return Endpoint(
        url=url,
        adapter="wikidata_sparql",
        minimum_interval_seconds=1,
        max_records=size,
        entity_ids=[f"Q990000000{i:03d}" for i in range(size)],
        user_agent="FraggyAPI/0.1 (https://github.com/mlvnpcrb/FraggyAPI; fixture@example.invalid)",
    )


def document(ids):
    return json.dumps(
        {
            "head": {"vars": ["item", "itemLabel", "brand", "brandLabel"]},
            "results": {
                "bindings": [
                    {
                        "item": {
                            "type": "uri",
                            "value": "http://www.wikidata.org/entity/" + i,
                        },
                        "itemLabel": {
                            "type": "literal",
                            "xml:lang": "en",
                            "value": "Invented" + i + " Fictional Orbit",
                        },
                        "brand": {
                            "type": "uri",
                            "value": "http://www.wikidata.org/entity/Q990000099999",
                        },
                        "brandLabel": {
                            "type": "literal",
                            "xml:lang": "en",
                            "value": "Original Fictional Brand",
                        },
                    }
                    for i in ids
                ]
            },
        }
    ).encode()


def test_source_mapping_preserves_unknowns_and_fixed_queries():
    config = endpoint()
    ids, next_cursor = page_ids(config, None)
    page = extract(document(ids), config, "application/sparql-results+json")
    assert len(page.records) == 25 and page.next_cursor == next_cursor == "25"
    record = page.records[0]
    assert record.source_record_id == ids[0]
    assert record.source_url == "https://www.wikidata.org/wiki/" + ids[0]
    assert record.source_metadata["brand"] == "Q990000099999"
    assert record.brand_name == "Original Fictional Brand"
    assert (
        record.concentration is None
        and record.release_year is None
        and record.version_label is None
    )
    assert not record.notes and not record.perfumers and not record.bottle_sizes_ml
    assert "P18" not in query(config, None)  # No image acquisition.
    assert "P1716" in query(config, None)
    assert page_ids(config, "75")[1] is None


@pytest.mark.parametrize(
    "change",
    [
        "id",
        "duplicate",
        "label",
        "brand",
        "unrequested",
        "oversize",
        "cursor",
        "mime",
        "malformed",
        "missing",
    ],
)
def test_bad_or_ambiguous_source_pages_fail_closed(change):
    config = endpoint()
    body = json.loads(document(config.entity_ids[:25]))
    rows = body["results"]["bindings"]
    mime = "application/sparql-results+json"
    cursor = None
    if change == "id":
        rows[0]["item"]["value"] = "https://attacker.invalid/entity/Q1"
    elif change == "duplicate":
        rows[1] = rows[0]
    elif change == "label":
        rows[0]["itemLabel"]["xml:lang"] = "de"
    elif change == "brand":
        del rows[0]["brandLabel"]
    elif change == "unrequested":
        rows[0]["item"]["value"] = "http://www.wikidata.org/entity/Q1"
    elif change == "oversize":
        rows.extend(rows * 25)
    elif change == "cursor":
        cursor = "../query"
    elif change == "mime":
        mime = "text/html"
    elif change == "malformed":
        body = []
    elif change == "missing":
        rows.pop()
    with pytest.raises(CollectionError):
        extract(json.dumps(body).encode(), config, mime, cursor)


@pytest.mark.parametrize(
    "change",
    [
        {"entity_ids": ["Q1 } UNION { ?x ?y ?z"]},
        {"entity_ids": ["Q1", "Q1"]},
        {"entity_ids": []},
        {"user_agent": None},
        {"url": "https://attacker.invalid/sparql"},
        {
            "field_map": {
                "source_record_id": "id",
                "brand_name": "brand",
                "fragrance_name": "name",
            }
        },
    ],
)
def test_unreviewable_source_configuration_is_rejected(change):
    values = endpoint().model_dump()
    values.update(change)
    with pytest.raises(ValidationError):
        Endpoint.model_validate(values)


def test_existing_collection_digests_are_compatible():
    old = {
        "url": "http://127.0.0.1:1234/catalog",
        "adapter": "rest_json",
        "minimum_interval_seconds": 1,
    }
    config = Endpoint.model_validate(old)
    assert "entity_ids" not in config.model_dump(mode="json")
    assert "user_agent" not in config.model_dump(mode="json")
    assert digest(config.model_dump(mode="json")) == digest(
        Endpoint.model_validate(config.model_dump()).model_dump(mode="json")
    )


async def test_wikidata_external_access_requires_separate_opt_in(
    collection_environment, monkeypatch
):
    import socket

    def denied(*args, **kwargs):
        pytest.fail("No external DNS/socket work without approval")

    monkeypatch.setattr(socket, "getaddrinfo", denied)
    grant = collection_environment.grant.model_copy(
        update={
            "manifest": collection_environment.manifest.model_copy(
                update={"synthetic": False}
            ),
            "endpoint": endpoint(),
        }
    )
    with pytest.raises(CollectionError, match="external_network_disabled"):
        await HTTPTransport().fetch(grant, None, None, None)


async def test_100_record_offline_source_pilot_stages_and_reruns_idempotently(
    collection_environment,
):
    env = collection_environment
    config = endpoint(env.server.url)
    from fraggy_api.importing.authorization import review_source
    from test_import_pipeline import PUBLIC_FIELDS

    manifest = env.manifest.model_copy(
        update={"permitted_fields": [*env.manifest.permitted_fields, "source_metadata"]}
    )
    async with env.factory.begin() as session:
        await review_source(
            session,
            manifest,
            "fixture-operator",
            "Original fixture source-specific reference storage",
            allow_storage=True,
            publish_fields=PUBLIC_FIELDS,
            accept_attribution=True,
        )
    grant = env.grant.model_copy(update={"endpoint": config, "manifest": manifest})
    async with env.factory.begin() as session:
        reviewed = await review_collection(
            session,
            grant,
            "fixture-operator",
            "Original offline Wikidata-format fixture only",
        )
        assert not reviewed.enabled and not reviewed.schedule_enabled
        await activate(
            session,
            env.identity,
            "fixture-operator",
            "Original fictional local schedule",
            schedule=True,
            interval=60,
        )

    def queue():
        for offset in range(0, 100, 25):
            env.server.responses.append(
                (
                    200,
                    document(config.entity_ids[offset : offset + 25]),
                    {"Content-Type": "application/sparql-results+json"},
                )
            )

    queue()
    env.clock.value = datetime.now(UTC)
    result = (await env.collector.tick())[0]
    assert result["status"] == "succeeded" and result["records_staged"] == 100
    assert len(env.server.requests) == 4
    async with env.factory() as session:
        snapshots = (
            await session.scalars(
                select(SourceRecord).where(SourceRecord.source_id == env.source_id)
            )
        ).all()
        assert len(snapshots) == 100
        assert all(
            s.payload["original"]["concentration"] is None
            and s.processing_state == "pending_review"
            for s in snapshots
        )
        assert (await public(session, demo=True))["data"] == []
    queue()
    again = await env.collector.run(env.identity)
    assert again["records_staged"] == 0 and again["records_unchanged"] == 100
    assert env.clock.now() >= datetime.now(UTC)
