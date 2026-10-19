"""Sanitized collector explanations and local response inspection; never fetches."""

import hashlib
from collections import Counter
from typing import Any

from pydantic import ValidationError

from ..importing.formats import Record, digest
from .adapters import extract
from .policy import CollectionError, Endpoint
from .transport import Response


def source_health(events: list[dict[str, Any]]) -> dict[str, Any]:
    if len(events) > 100:
        raise ValueError("Bounded health window required")
    categories = Counter(
        str(event.get("category", "unknown_failure")) for event in events
    )
    blocked = any(
        categories[name]
        for name in (
            "access_restricted",
            "authorization_blocked",
            "schema_or_format_changed",
            "pagination_or_duplicate_failure",
        )
    )
    return {
        "health": "blocked"
        if blocked
        else "degraded"
        if any(name != "healthy" for name in categories)
        else "healthy",
        "categories": dict(categories),
        "samples": len(events),
        "activation_authorized": False,
        "meaning": "derived from supplied recent diagnostics; no automatic recovery/activation or scheduler dispatch",
    }


def explain(code: str | None, status: int | None = None) -> dict[str, Any]:
    category, action = (
        "unknown_failure",
        "Stop and inspect the local sanitized run report.",
    )
    if code is None:
        category, action = "healthy", "Continue only within the reviewed source budget."
    elif code in {"collection_not_authorized", "external_network_disabled"}:
        category, action = (
            "authorization_blocked",
            "Do not dispatch requests; obtain source-specific review and activity approval.",
        )
    elif status in {401, 403}:
        category, action = (
            "access_restricted",
            "Stop. Review authorization; do not bypass login or access controls.",
        )
    elif status == 429:
        category, action = (
            "rate_limited",
            "Honor Retry-After and the existing retry budget; do not increase request volume.",
        )
    elif status and status >= 500:
        category, action = (
            "upstream_unavailable",
            "Use bounded backoff only while authorization remains valid.",
        )
    elif code in {"network_timeout", "network_failure"}:
        category, action = (
            "network_timeout_or_failure",
            "Retry only within the configured budget; never change hosts to evade denial.",
        )
    elif code in {
        "malformed_page",
        "unexpected_content_type",
        "invalid_html_payload",
        "invalid_record",
        "invalid_wikidata_binding",
    }:
        category, action = (
            "schema_or_format_changed",
            "Stop checkpoint advancement; compare an authorized fixture with the reviewed parser contract.",
        )
    elif code in {
        "pagination_cycle",
        "duplicate_response_page",
        "wikidata_incomplete_page",
        "incomplete_pagination",
        "duplicate_page_identity",
    }:
        category, action = (
            "pagination_or_duplicate_failure",
            "Preserve the last successful checkpoint; inspect page identity and completeness.",
        )
    elif code in {"collection_not_authorized", "external_network_disabled"}:
        category, action = (
            "authorization_blocked",
            "Do not dispatch requests; obtain source-specific review and activity approval.",
        )
    # Untrusted exception text never becomes a diagnostic code.
    safe_codes = {
        "network_timeout",
        "network_failure",
        "malformed_page",
        "unexpected_content_type",
        "invalid_html_payload",
        "invalid_record",
        "invalid_wikidata_binding",
        "pagination_cycle",
        "duplicate_response_page",
        "wikidata_incomplete_page",
        "incomplete_pagination",
        "duplicate_page_identity",
        "collection_not_authorized",
        "external_network_disabled",
        "retry_exhausted",
        "http_status_denied",
    }
    return {
        "code": code if code in safe_codes else "collector_failure" if code else None,
        "http_status": status,
        "category": category,
        "action": action,
        "automatic_bypass": False,
    }


def inspect_response(
    response: Response,
    endpoint: Endpoint,
    *,
    seen_pages: set[str] | None = None,
    expected_final_records: int | None = None,
) -> dict[str, Any]:
    """Inspect supplied local response bytes. This is not an HTTP operation."""
    if response.status != 200:
        return {
            "ok": False,
            "diagnostic": explain("http_status_denied", response.status),
        }
    fingerprint = digest({"body_sha": hashlib.sha256(response.body).hexdigest()})
    if seen_pages and fingerprint in seen_pages:
        return {"ok": False, "diagnostic": explain("duplicate_response_page")}
    try:
        page = extract(response.body, endpoint, response.content_type)
        if (
            expected_final_records is not None
            and page.next_cursor is None
            and len(page.records) != expected_final_records
        ):
            raise CollectionError("incomplete_pagination")
        return {
            "ok": True,
            "records": len(page.records),
            "next_cursor": page.next_cursor,
            "page_fingerprint": fingerprint,
            "diagnostic": explain(None),
        }
    except (CollectionError, ValidationError) as error:
        diagnostic = explain(
            str(error) if isinstance(error, CollectionError) else "malformed_page"
        )
        cause = error.__cause__
        if isinstance(cause, ValidationError):
            allowed = set(Record.model_fields) | {"name", "aliases", "position"}
            diagnostic["missing_required_fields"] = sorted(
                {
                    str(item["loc"][-1])
                    for item in cause.errors(
                        include_input=False, include_context=False, include_url=False
                    )
                    if item["type"] == "missing"
                    and item["loc"]
                    and str(item["loc"][-1]) in allowed
                }
            )
            diagnostic["field_paths"] = [
                [
                    str(part)
                    if str(part) in allowed or isinstance(part, int)
                    else "unrecognized_field"
                    for part in item["loc"]
                ]
                for item in cause.errors(
                    include_input=False, include_context=False, include_url=False
                )[:5]
            ]
        return {"ok": False, "diagnostic": diagnostic}
