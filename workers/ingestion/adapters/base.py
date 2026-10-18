"""Phase 1 contracts. This module has no network implementation."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import Any


class LiveIngestionDisabled(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    source_record_id: str
    source_url: str
    collected_at: datetime
    payload: Mapping[str, Any]
    usage_rights_status: str = "fixture_only"


class SourceAdapter(ABC):
    source_id: str

    def collect(self, *args: Any, **kwargs: Any) -> None:
        # Deliberately unconditional: registry edits cannot activate skeletons.
        raise LiveIngestionDisabled(
            f"{self.source_id}: live ingestion is unavailable in Phase 1"
        )

    @abstractmethod
    def parse_fixture(self, fixture: Mapping[str, Any]) -> SourceRecord:
        """Read synthetic local fixture data; never fetch referenced URLs."""

    def _parse_fixture(self, fixture: Mapping[str, Any]) -> SourceRecord:
        if fixture.get("synthetic") is not True:
            raise ValueError("Only explicitly synthetic fixtures are supported")
        if fixture.get("source_id") != self.source_id:
            raise ValueError("Fixture source does not match adapter")
        record_id = fixture.get("source_record_id")
        url = fixture.get("source_url")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Missing source record ID")
        if not isinstance(url, str) or not url.startswith("https://example.invalid/"):
            raise ValueError("Fixtures must use reserved example.invalid URLs")
        timestamp_value = fixture.get("collected_at")
        if not isinstance(timestamp_value, str):
            raise ValueError("Collection timestamp must be an ISO string")
        timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("Collection timestamp must include a timezone")
        payload = fixture.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Fixture payload must be an object")
        return SourceRecord(
            self.source_id, record_id, url, timestamp, deepcopy(payload)
        )
