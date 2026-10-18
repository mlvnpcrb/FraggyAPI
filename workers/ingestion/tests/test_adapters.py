import copy
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workers.ingestion.adapters.base import LiveIngestionDisabled
from workers.ingestion.registry import load_registry

FIXTURES = Path(__file__).parent / "fixtures"


class AdapterTests(unittest.TestCase):
    def test_all_seven_adapters_parse_synthetic_records_without_network(self):
        for source in load_registry()["sources"]:
            with self.subTest(source=source["id"]):
                module = importlib.import_module(
                    "workers.ingestion.adapters." + source["adapter"]
                )
                cls = getattr(
                    module,
                    "".join(w.title() for w in source["adapter"].split("_"))
                    + "Adapter",
                )
                adapter = cls()
                fixture = json.loads((FIXTURES / (source["id"] + ".json")).read_text())
                original = copy.deepcopy(fixture)
                with patch(
                    "socket.socket", side_effect=AssertionError("Network forbidden")
                ):
                    record = adapter.parse_fixture(fixture)
                    with self.assertRaises(LiveIngestionDisabled):
                        adapter.collect()
                self.assertEqual(record.source_id, source["id"])
                self.assertEqual(record.payload, fixture["payload"])
                self.assertEqual(record.usage_rights_status, "fixture_only")
                self.assertIsNotNone(record.collected_at.tzinfo)
                self.assertEqual(original, fixture)
                record.payload["notes"]["top"].append("changed")
                self.assertEqual(original, fixture)
                for changes in [
                    {"synthetic": False},
                    {"source_id": "wrong"},
                    {"source_url": source["website"]},
                    {"source_record_id": ""},
                    {"payload": []},
                    {"collected_at": None},
                    {"collected_at": "2026-10-17T00:00:00"},
                ]:
                    with self.assertRaises(ValueError):
                        adapter.parse_fixture({**fixture, **changes})

    def test_registry_rejects_live_configuration(self):
        for changes in [
            {"enabled": True},
            {"authorization_status": "approved"},
            {"licensing_status": "approved"},
            {"permitted_fields": ["name"]},
            {"allowed_collection_methods": ["http"]},
            {"rate_limit": {"requests_per_minute": 10, "max_concurrency": 1}},
        ]:
            with self.subTest(changes=changes), tempfile.TemporaryDirectory() as tmp:
                registry = load_registry()
                registry["sources"][0].update(changes)
                path = Path(tmp) / "sources.json"
                path.write_text(json.dumps(registry))
                with self.assertRaises(ValueError):
                    load_registry(path)

    def test_registry_rejects_duplicate_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = load_registry()
            registry["sources"][1] = registry["sources"][0]
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(registry))
            with self.assertRaises(ValueError):
                load_registry(path)


if __name__ == "__main__":
    unittest.main()
