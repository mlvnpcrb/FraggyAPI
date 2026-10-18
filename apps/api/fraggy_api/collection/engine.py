"""Short transactions, durable fencing leases and atomic page/checkpoint staging."""

import asyncio
import hashlib
import math
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..importing.authorization import actor, check_storage, writer_lock
from ..importing.pipeline import stage
from ..models import CollectionRun, CollectionSource
from ..quality.report import catalog_quality
from .adapters import extract, token
from .policy import CollectionError, Grant, authorize, source_pair
from .quality import assess, combine
from .transport import HTTPTransport, Response

Factory = async_sessionmaker[AsyncSession]


def now() -> datetime:
    return datetime.now(UTC)


async def activate(
    session: AsyncSession,
    identity: UUID,
    reviewer: str,
    reason: str,
    *,
    schedule: bool = False,
    interval: int = 86400,
) -> None:
    actor(reviewer, reason)
    if not 60 <= interval <= 31536000:
        raise CollectionError("invalid_schedule_interval")
    config, source = await source_pair(session, identity, lock=True)
    authorize(config, source, now(), active=False)
    config.enabled = True
    config.schedule_enabled = schedule
    config.interval_seconds = interval
    config.next_due_at = now()
    source.evidence = [
        *source.evidence,
        {
            "kind": "collection_activated",
            "at": now().isoformat(),
            "reviewer": reviewer,
            "reason": reason,
            "configuration_digest": config.configuration_digest,
            "schedule_enabled": schedule,
            "interval_seconds": interval,
        },
    ]


async def revoke_collection(
    session: AsyncSession, identity: UUID, reviewer: str, reason: str
) -> None:
    actor(reviewer, reason)
    config, source = await source_pair(session, identity, lock=True)
    source.evidence = [
        *source.evidence,
        {
            "kind": "collection_revoked",
            "at": now().isoformat(),
            "reviewer": reviewer,
            "reason": reason,
            "configuration_digest": config.configuration_digest,
        },
    ]
    config.enabled = config.schedule_enabled = False
    config.state = "revoked"
    if config.current_run_id:
        run = await session.get(CollectionRun, config.current_run_id)
        if run:
            run.cancel_requested = True


async def cancel(
    session: AsyncSession, identity: UUID, reviewer: str, reason: str
) -> None:
    actor(reviewer, reason)
    # Same lock order as worker transactions: source then run.
    initial = await session.get(CollectionRun, identity)
    if initial is None:
        raise CollectionError("run_not_found")
    _, source = await source_pair(session, initial.collection_id, lock=True)
    run = await session.get(CollectionRun, identity, populate_existing=True)
    assert run is not None
    if run.status == "running":
        run.cancel_requested = True
        source.evidence = [
            *source.evidence,
            {
                "kind": "collection_cancel_requested",
                "at": now().isoformat(),
                "reviewer": reviewer,
                "reason": reason,
                "run_id": str(identity),
            },
        ]


class Collector:
    def __init__(
        self,
        factory: Factory,
        transport: HTTPTransport | None = None,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], datetime] = now,
    ) -> None:
        self.factory = factory
        self.transport = transport or HTTPTransport()
        self.sleep = sleep
        self.clock = clock

    async def claim(self, identity: UUID, *, scheduled: bool = False) -> UUID | None:
        async with self.factory.begin() as session:
            config = await session.scalar(
                select(CollectionSource)
                .where(CollectionSource.id == identity)
                .with_for_update(skip_locked=True)
            )
            if config is None:
                return None
            _, source = await source_pair(session, identity)
            authorize(config, source, self.clock())
            if (
                config.next_request_at
                and (config.next_request_at - self.clock()).total_seconds() > 300
            ):
                return None
            if scheduled and (
                not config.schedule_enabled
                or (config.next_due_at and config.next_due_at > self.clock())
            ):
                return None
            if config.current_run_id:
                if config.lease_until and config.lease_until > self.clock():
                    return None
                old = await session.get(CollectionRun, config.current_run_id)
                if old and old.status == "running":
                    old.status = "interrupted"
                    old.finished_at = self.clock()
                    old.errors = [*old.errors[-9:], {"code": "lease_expired"}]
                    await session.flush()
            run = CollectionRun(
                id=uuid4(),
                collection_id=identity,
                configuration_digest=config.configuration_digest,
                status="running",
                started_at=self.clock(),
                checkpoint=dict(config.checkpoint),
            )
            session.add(run)
            config.current_run_id = run.id
            config.lease_until = self.clock() + timedelta(seconds=60)
            await session.flush()
            return run.id

    async def guarded(
        self, session: AsyncSession, identity: UUID, run_id: UUID
    ) -> tuple[CollectionSource, CollectionRun, Grant]:
        config, source = await source_pair(session, identity, lock=True)
        run = await session.get(CollectionRun, run_id, populate_existing=True)
        if (
            run is None
            or config.current_run_id != run_id
            or run.status != "running"
            or not config.lease_until
            or config.lease_until <= self.clock()
        ):
            raise CollectionError("lease_lost")
        if run.cancel_requested:
            raise CollectionError("cancelled")
        return config, run, authorize(config, source, self.clock())

    async def wait(self, identity: UUID, run_id: UUID, delay: float) -> None:
        # Poll cancellation and authorization while waiting, never hold a DB
        # connection across sleep/network work. Clock injection is for tests only.
        remaining = delay
        while remaining > 0:
            step = min(remaining, 1.0)
            await self.sleep(step)
            remaining -= step
            async with self.factory.begin() as session:
                await self.guarded(session, identity, run_id)

    async def finish(
        self, identity: UUID, run_id: UUID, status: str, code: str | None = None
    ) -> None:
        async with self.factory.begin() as session:
            await writer_lock(session)
            config, source = await source_pair(session, identity, lock=True)
            run = await session.get(CollectionRun, run_id)
            if (
                run is None
                or config.current_run_id != run_id
                or run.status != "running"
            ):
                return
            if status == "succeeded":
                try:
                    authorize(config, source, self.clock())
                    if run.cancel_requested:
                        status, code = "cancelled", "cancelled"
                    else:
                        source.last_successful_sync = self.clock()
                except CollectionError:
                    status, code = "failed", "collection_not_authorized"
            run.status = status
            run.finished_at = self.clock()
            if code:
                run.errors = [*run.errors[-9:], {"code": code}]
            config.current_run_id = None
            config.lease_until = None
            config.next_due_at = max(
                self.clock() + timedelta(seconds=config.interval_seconds),
                config.next_request_at or self.clock(),
            )

    async def execute(self, identity: UUID, run_id: UUID) -> dict[str, Any]:
        status = "partial"
        code: str | None = None
        visited: set[str | None] = set()
        total = 0
        try:
            for _page in range(100):
                async with self.factory.begin() as session:
                    config, run, grant = await self.guarded(session, identity, run_id)
                    checkpoint = dict(config.checkpoint)
                    cursor = token(checkpoint.get("cursor"))
                    since = token(checkpoint.get("since"))
                    if cursor in visited:
                        raise CollectionError("pagination_cycle")
                    visited.add(cursor)
                    if run.pages >= grant.endpoint.max_pages:
                        break
                response = None
                for attempt in range(grant.endpoint.retries + 1):
                    async with self.factory.begin() as session:
                        config, run, grant = await self.guarded(
                            session, identity, run_id
                        )
                        delay = (
                            max(
                                0.0,
                                (config.next_request_at - self.clock()).total_seconds(),
                            )
                            if config.next_request_at
                            else 0.0
                        )
                        request_at = self.clock() + timedelta(seconds=delay)
                        config.next_request_at = request_at + timedelta(
                            seconds=grant.endpoint.minimum_interval_seconds
                        )
                        config.lease_until = request_at + timedelta(
                            seconds=grant.endpoint.timeout_seconds + 60
                        )
                        run.attempts += 1
                    await self.wait(identity, run_id, delay)
                    # Last gate immediately before invoking a transport, including
                    # retries. Default transport denies external DNS/socket work.
                    async with self.factory.begin() as session:
                        _, _, grant = await self.guarded(session, identity, run_id)
                    retry_after = 0.0
                    try:
                        received: Response = await asyncio.wait_for(
                            self.transport.fetch(
                                grant,
                                cursor,
                                since,
                                checkpoint.get("etag")
                                if cursor is None
                                and checkpoint.get("etag_since") == since
                                else None,
                            ),
                            timeout=grant.endpoint.timeout_seconds + 0.5,
                        )
                        response = received
                        if received.status not in {429, 500, 502, 503, 504}:
                            break
                        if received.retry_after:
                            try:
                                retry_after = float(received.retry_after)
                            except ValueError:
                                try:
                                    retry_at = parsedate_to_datetime(
                                        received.retry_after
                                    )
                                    retry_after = max(
                                        0.0, (retry_at - self.clock()).total_seconds()
                                    )
                                except (ValueError, TypeError, OverflowError):
                                    raise CollectionError(
                                        "unsupported_retry_after"
                                    ) from None
                            if not math.isfinite(retry_after) or retry_after > 31536000:
                                raise CollectionError("retry_after_exceeds_budget")
                            retry_after = max(0.0, retry_after)
                            async with self.factory.begin() as session:
                                config, _, _ = await self.guarded(
                                    session, identity, run_id
                                )
                                config.next_request_at = max(
                                    config.next_request_at or self.clock(),
                                    self.clock() + timedelta(seconds=retry_after),
                                )
                            if retry_after > 300:
                                raise CollectionError("retry_after_exceeds_budget")
                    except (TimeoutError, CollectionError) as error:
                        if (
                            isinstance(error, CollectionError)
                            and str(error) != "network_failure"
                        ):
                            raise
                        response = None
                    if attempt == grant.endpoint.retries:
                        raise CollectionError("retry_exhausted")
                    backoff = max(
                        retry_after,
                        min(30.0, grant.endpoint.backoff_seconds * 2**attempt),
                    )
                    async with self.factory.begin() as session:
                        config, run, _ = await self.guarded(session, identity, run_id)
                        config.lease_until = self.clock() + timedelta(
                            seconds=backoff + grant.endpoint.timeout_seconds + 60
                        )
                        run.errors = [
                            *run.errors[-9:],
                            {"code": "transient_retry", "attempt": attempt + 1},
                        ]
                    await self.wait(identity, run_id, backoff)
                if response is None:
                    raise CollectionError("network_failure")
                if response.status == 304:
                    if (
                        cursor is not None
                        or not checkpoint.get("etag")
                        or checkpoint.get("etag_since") != since
                    ):
                        raise CollectionError("unexpected_not_modified")
                    status = "succeeded"
                    break
                if response.status != 200:
                    raise CollectionError("http_status_denied")
                page = extract(response.body, grant.endpoint, response.content_type)
                if page.next_cursor in visited and page.next_cursor is not None:
                    raise CollectionError("pagination_cycle")
                assessment = assess(page.records)
                total += len(page.records)
                if total > grant.endpoint.max_records:
                    # No partial page writes and no checkpoint movement.
                    raise CollectionError("run_record_budget_exceeded")
                async with self.factory.begin() as session:
                    # Serialize with source storage/publication review/revocation.
                    await writer_lock(session)
                    config, run, grant = await self.guarded(session, identity, run_id)
                    _, source = await source_pair(session, identity)
                    if any(
                        not check_storage(source, grant.manifest, record)
                        for record in page.records
                    ):
                        raise CollectionError("storage_not_authorized")
                    result = await stage(session, page.records, grant.manifest)
                    next_checkpoint: dict[str, Any] = {
                        "cursor": page.next_cursor,
                        "since": since,
                        "pending_since": page.watermark
                        or checkpoint.get("pending_since"),
                    }
                    if page.next_cursor is None:
                        next_checkpoint["since"] = (
                            next_checkpoint.pop("pending_since") or since
                        )
                        if response.etag and run.pages == 0:
                            if len(response.etag) > 256 or any(
                                ord(c) < 32 or ord(c) > 126 for c in response.etag
                            ):
                                raise CollectionError("invalid_etag")
                            next_checkpoint["etag"] = response.etag
                            next_checkpoint["etag_since"] = since
                    config.checkpoint = next_checkpoint
                    run.checkpoint = next_checkpoint
                    run.ingestion_run_ids = [*run.ingestion_run_ids, result["run_id"]]
                    run.response_digests = [
                        *run.response_digests,
                        hashlib.sha256(response.body).hexdigest(),
                    ]
                    run.quality = combine(run.quality, assessment)
                    run.pages += 1
                    run.records_seen += len(page.records)
                    run.records_staged += result["inserted"]
                    run.records_unchanged += result["skipped"]
                    config.lease_until = self.clock() + timedelta(seconds=60)
                if page.next_cursor is None:
                    status = "succeeded"
                    break
        except asyncio.CancelledError:
            await asyncio.shield(
                self.finish(identity, run_id, "cancelled", "worker_cancelled")
            )
            raise
        except CollectionError as error:
            code = str(error)
            status = "cancelled" if code == "cancelled" else "failed"
        except Exception:
            # Unknown exceptions never expose SQL, URLs, bodies or credentials.
            status, code = "failed", "internal_failure"
        await self.finish(identity, run_id, status, code)
        return await self.summary(run_id)

    async def summary(self, run_id: UUID) -> dict[str, Any]:
        async with self.factory() as session:
            run = await session.get(CollectionRun, run_id)
            if run is None:
                raise CollectionError("run_not_found")
            return {
                "run_id": str(run.id),
                "collection_id": str(run.collection_id),
                "status": run.status,
                "pages": run.pages,
                "records_seen": run.records_seen,
                "records_staged": run.records_staged,
                "records_unchanged": run.records_unchanged,
                "attempts": run.attempts,
                "errors": run.errors,
                "quality": run.quality,
                "ingestion_run_ids": run.ingestion_run_ids,
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            }

    async def run(self, identity: UUID, *, scheduled: bool = False) -> dict[str, Any]:
        try:
            run_id = await self.claim(identity, scheduled=scheduled)
        except CollectionError:
            async with self.factory.begin() as session:
                config = await session.get(CollectionSource, identity)
                if config is not None:
                    session.add(
                        CollectionRun(
                            id=uuid4(),
                            collection_id=identity,
                            configuration_digest=config.configuration_digest,
                            status="failed",
                            started_at=self.clock(),
                            finished_at=self.clock(),
                            errors=[{"code": "collection_not_authorized"}],
                        )
                    )
            raise
        if run_id is None:
            return {"status": "not_claimed"}
        return await self.execute(identity, run_id)

    async def tick(self) -> list[dict[str, Any]]:
        async with self.factory() as session:
            ids = list(
                (
                    await session.scalars(
                        select(CollectionSource.id)
                        .where(
                            CollectionSource.enabled.is_(True),
                            CollectionSource.schedule_enabled.is_(True),
                            CollectionSource.state == "approved",
                            CollectionSource.next_due_at <= self.clock(),
                        )
                        .order_by(CollectionSource.next_due_at, CollectionSource.id)
                        .limit(100)
                    )
                ).all()
            )
        results = []
        for identity in ids:
            try:
                results.append(await self.run(identity, scheduled=True))
            except CollectionError:
                results.append({"collection_id": str(identity), "status": "denied"})
        return results

    async def quality(self) -> dict[str, Any]:
        from sqlalchemy import text

        async with self.factory() as session:
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            report = await catalog_quality(session)
            await session.rollback()
            return report
