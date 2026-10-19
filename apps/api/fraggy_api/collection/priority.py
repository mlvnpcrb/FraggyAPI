"""Pure offline priority/budget planner. It cannot lease jobs or send requests."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from ..importing.formats import Strict


class Task(Strict):
    id: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    source: str = Field(pattern=r"^[a-z0-9-]{1,80}$")
    fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")
    priority: int = Field(default=0, ge=0, le=9)
    due_at: datetime
    attempt: int = Field(default=0, ge=0, le=4)
    retry_limit: int = Field(default=1, ge=0, le=4)
    synthetic: Literal[True] = True

    @model_validator(mode="after")
    def dated(self) -> "Task":
        if self.due_at.tzinfo is None:
            raise ValueError("Timezone required")
        return self


class Budget(Strict):
    remaining: int = Field(ge=0, le=100)
    next_request_at: datetime
    health: Literal["healthy", "degraded", "blocked"] = "healthy"

    @model_validator(mode="after")
    def dated(self) -> "Budget":
        if self.next_request_at.tzinfo is None:
            raise ValueError("Timezone required")
        return self


def backoff(attempt: int, retry_after: float = 0) -> float:
    import math

    if (
        not 0 <= attempt <= 4
        or not math.isfinite(retry_after)
        or not 0 <= retry_after <= 300
    ):
        raise ValueError("Retry exceeds offline budget")
    return float(max(min(30, 2**attempt), retry_after))


def plan(
    tasks: list[Task], budgets: dict[str, Budget], now: datetime
) -> dict[str, object]:
    if now.tzinfo is None or len(tasks) > 1000 or len(budgets) > 100:
        raise ValueError("Invalid planning bounds")
    if len({task.id for task in tasks}) != len(tasks):
        raise ValueError("Duplicate task ID")
    chosen = []
    deferred = []
    seen: set[tuple[str, str]] = set()
    sources: set[str] = set()
    for task in sorted(tasks, key=lambda t: (-t.priority, t.due_at, t.id)):
        budget = budgets.get(task.source)
        reason = None
        if (task.source, task.fingerprint) in seen:
            reason = "duplicate_request"
        elif task.attempt > task.retry_limit:
            reason = "retry_budget_exhausted"
        elif budget is None or budget.health == "blocked":
            reason = "source_unavailable"
        elif task.due_at > now or budget.next_request_at > now:
            reason = "not_due"
        elif budget.remaining == 0:
            reason = "source_budget_exhausted"
        elif task.source in sources:
            reason = "one_inflight_per_source"
        if reason:
            deferred.append({"id": task.id, "reason": reason})
        else:
            seen.add((task.source, task.fingerprint))
            sources.add(task.source)
            chosen.append(task.id)
    return {
        "offline_only": True,
        "would_dispatch": chosen,
        "deferred": deferred,
        "dispatch_allowed": False,
        "schedule_enabled": False,
        "meaning": "unsigned simulation; actual authorization, leases and rate limits remain with the existing Collector",
    }
