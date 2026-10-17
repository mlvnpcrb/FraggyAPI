"""Load the fail-closed Phase 1 source registry."""
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "config" / "sources.json"
SOURCE_IDS = frozenset({"fragrantica", "parfumo", "basenotes", "wikiparfum",
                        "perfume_society", "perfumemaster", "scentbase"})


def load_registry(path: Path = DEFAULT_PATH) -> dict:
    registry = json.loads(path.read_text())
    if registry.get("schema_version") != 1:
        raise ValueError("Unsupported registry schema")
    sources = registry["sources"]
    if len(sources) != len(SOURCE_IDS) or {s["id"] for s in sources} != SOURCE_IDS:
        raise ValueError("Expected exactly the seven configured sources")
    for source in sources:
        if (source["enabled"] is not False
                or source["authorization_status"] != "pending_review"
                or source["licensing_status"] != "pending_review"
                or source["adapter_status"] != "skeleton"
                or source["allowed_collection_methods"]
                or source["permitted_fields"]
                or source["adapter"] != source["id"]
                or source["rate_limit"] != {"requests_per_minute": 0, "max_concurrency": 0}):
            raise ValueError("Phase 1 sources must remain disabled and pending review")
    return registry
