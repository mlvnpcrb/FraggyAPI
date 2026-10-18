"""Only trusted operator review authorizes collection, never downloaded claims."""

import ipaddress
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..importing.authorization import actor, policy, source_for, writer_lock
from ..importing.formats import Manifest, Record, Strict, digest
from ..models import CollectionSource, DataSource
from ..public_rights import reviewed_attribution


class CollectionError(ValueError):
    """Static codes only; never URLs, responses, credentials or input values."""


class Endpoint(Strict):
    url: str = Field(max_length=2048)
    adapter: Literal[
        "rest_json", "json_feed", "csv_feed", "html_json", "wikidata_sparql"
    ]
    entity_ids: list[str] = Field(
        default_factory=list, max_length=300, exclude_if=lambda v: not v
    )
    user_agent: str | None = Field(
        default=None, max_length=250, exclude_if=lambda v: v is None
    )
    field_map: dict[str, str] = Field(default_factory=dict, max_length=30)
    credential_env: str | None = Field(
        default=None, pattern=r"^FRAGGY_COLLECTOR_[A-Z0-9_]{1,70}$"
    )
    minimum_interval_seconds: float = Field(ge=0.01, le=300)
    timeout_seconds: float = Field(default=10, ge=0.1, le=30)
    retries: int = Field(default=2, ge=0, le=4)
    backoff_seconds: float = Field(default=1, ge=0.01, le=30)
    max_pages: int = Field(default=10, ge=1, le=100)
    max_records: int = Field(default=1000, ge=1, le=1000)

    @model_validator(mode="after")
    def wikidata_configuration(self) -> "Endpoint":
        import re

        if self.adapter == "wikidata_sparql":
            if (
                not self.entity_ids
                or len(set(self.entity_ids)) != len(self.entity_ids)
                or any(
                    not re.fullmatch(r"Q[1-9][0-9]{0,15}", i) for i in self.entity_ids
                )
                or self.max_pages < (len(self.entity_ids) + 24) // 25
                or self.max_records < len(self.entity_ids)
                or self.field_map
                or self.credential_env
                or not self.user_agent
                or not re.fullmatch(
                    r"FraggyAPI/[0-9.]+ \(https://github.com/mlvnpcrb/FraggyAPI; [A-Za-z0-9_.+@-]+\)",
                    self.user_agent,
                )
                or (
                    self.url != "https://query.wikidata.org/sparql"
                    and not self.url.startswith("http://127.0.0.1:")
                )
            ):
                raise ValueError(
                    "Reviewed Wikidata IDs and contact User-Agent required"
                )
        elif self.entity_ids or self.user_agent:
            raise ValueError("Source-specific configuration on wrong adapter")
        return self

    @field_validator("field_map")
    @classmethod
    def supported_map(cls, value: dict[str, str]) -> dict[str, str]:
        if (
            (
                value
                and not {"source_record_id", "brand_name", "fragrance_name"}
                <= set(value)
            )
            or not set(value) <= set(Record.model_fields)
            or any(not k or len(k) > 200 for k in value.values())
        ):
            raise ValueError("Unsupported field map")
        return value

    @field_validator("url")
    @classmethod
    def safe_endpoint(cls, value: str) -> str:
        p = urlsplit(value)
        if (
            p.scheme not in {"https", "http"}
            or not p.hostname
            or p.username
            or p.password
            or p.query
            or p.fragment
            or any(ord(c) < 33 for c in value)
        ):
            raise ValueError("Invalid endpoint")
        _ = p.port
        return value


class Grant(Strict):
    manifest: Manifest
    endpoint: Endpoint
    automated_access: Literal[True]
    database_storage: Literal[True]
    commercial_reuse: Literal[True]
    api_redistribution: Literal[True]
    attribution_accepted: Literal[True]
    access_restrictions: Annotated[list[str], Field(min_length=1, max_length=20)]
    evidence: dict[str, str]
    reviewed_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def complete(self) -> "Grant":
        required = {
            "automated_access",
            "database_storage",
            "commercial_reuse",
            "api_redistribution",
            "attribution",
            "rate_limits",
            "access_restrictions",
        }
        if set(self.evidence) != required or any(
            not v.strip() or len(v) > 1000 for v in self.evidence.values()
        ):
            raise ValueError("Complete collection evidence required")
        if (
            not self.reviewed_at.tzinfo
            or not self.expires_at.tzinfo
            or self.expires_at <= self.reviewed_at
        ):
            raise ValueError("Invalid review dates")
        if (
            not self.manifest.storage_permissions
            or not self.manifest.redistribution_permissions
            or self.manifest.redistribution_conditions
        ):
            raise ValueError("Inconsistent manifest permissions")
        if not all(v.strip() and len(v) <= 1000 for v in self.access_restrictions):
            raise ValueError("Invalid access restrictions")
        p = urlsplit(self.endpoint.url)
        if self.manifest.synthetic:
            if (
                p.scheme != "http"
                or p.hostname != "127.0.0.1"
                or self.endpoint.credential_env
            ):
                raise ValueError(
                    "Synthetic HTTP requires literal loopback without credentials"
                )
        elif p.scheme != "https":
            raise ValueError("External collection requires HTTPS")
        elif (
            self.endpoint.adapter == "wikidata_sparql"
            and self.endpoint.minimum_interval_seconds < 1
        ):
            raise ValueError(
                "External Wikidata pilot requires at least one second between requests"
            )
        return self


def authorize(
    config: CollectionSource, source: DataSource, now: datetime, *, active: bool = True
) -> Grant:
    try:
        grant = Grant.model_validate(config.configuration)
        event = config.review
        body = grant.model_dump(mode="json")
        if (
            config.state != "approved"
            or (active and not config.enabled)
            or config.configuration_digest != digest(body)
            or event.get("configuration_digest") != digest(body)
            or not event.get("reviewer")
            or not event.get("reason")
            or grant.reviewed_at > now
            or grant.expires_at <= now
            or grant.manifest.source_id != source.key
            or source.source_type
            != ("synthetic_file_import" if grant.manifest.synthetic else "file_import")
            or source.authorization_status
            != ("synthetic" if grant.manifest.synthetic else "approved")
            or source.licensing_status != source.authorization_status
            or not policy(source, grant.manifest)
            or not reviewed_attribution(source)[0]
        ):
            raise CollectionError("collection_not_authorized")
        return grant
    except (ValueError, TypeError, KeyError) as exc:
        raise CollectionError("collection_not_authorized") from exc


async def review_collection(
    session: AsyncSession, grant: Grant, reviewer: str, reason: str
) -> CollectionSource:
    actor(reviewer, reason)
    await writer_lock(session)
    source = await source_for(session, grant.manifest)
    if source is None:
        raise CollectionError("storage_review_required")
    existing = await session.scalar(
        select(CollectionSource)
        .where(CollectionSource.source_id == source.id)
        .with_for_update()
    )
    if existing is not None and existing.current_run_id is not None:
        raise CollectionError("stop_active_run_before_review")
    body = grant.model_dump(mode="json")
    config = existing or CollectionSource(id=uuid4(), source_id=source.id)
    config.configuration = body
    config.configuration_digest = digest(body)
    # Keep bounded private review history; never emit this through monitoring.
    history: list[Any] = (
        list(config.review.get("history", []))[-19:] if existing else []
    )
    if existing:
        history.append({k: v for k, v in config.review.items() if k != "history"})
    config.review = {
        "reviewer": reviewer,
        "reason": reason,
        "at": datetime.now(UTC).isoformat(),
        "configuration_digest": digest(body),
        "history": history,
    }
    source.evidence = [
        *source.evidence,
        {
            "kind": "operator_collection_review",
            "configuration": body,
            **{k: v for k, v in config.review.items() if k != "history"},
        },
    ]
    config.state = "approved"
    config.enabled = False
    config.schedule_enabled = False
    config.interval_seconds = 86400
    # A changed endpoint/manifest starts a new cycle; old import snapshots persist.
    config.checkpoint = {}
    session.add(config)
    authorize(config, source, datetime.now(UTC), active=False)
    await session.flush()
    return config


def public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return address.is_global and not address.is_multicast


async def source_pair(
    session: AsyncSession, identity: UUID, *, lock: bool = False
) -> tuple[CollectionSource, DataSource]:
    query = select(CollectionSource).where(CollectionSource.id == identity)
    if lock:
        query = query.with_for_update()
    config = await session.scalar(query)
    if config is None:
        raise CollectionError("collection_not_found")
    source = await session.get(DataSource, config.source_id, populate_existing=True)
    if source is None:
        raise CollectionError("source_not_found")
    return config, source
