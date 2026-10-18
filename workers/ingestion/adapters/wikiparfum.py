"""Wikiparfum skeleton; no live collection or site parser is implemented."""

from collections.abc import Mapping
from typing import Any

from .base import SourceAdapter, SourceRecord


class WikiparfumAdapter(SourceAdapter):
    source_id = "wikiparfum"

    def parse_fixture(self, fixture: Mapping[str, Any]) -> SourceRecord:
        return self._parse_fixture(fixture)
