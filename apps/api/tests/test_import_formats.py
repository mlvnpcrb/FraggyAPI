import json
from pathlib import Path

import pytest
from fraggy_api.importing.formats import (
    MAX_BYTES,
    MAX_ROWS,
    ImportErrorSafe,
    Record,
    concentration,
    key,
    manifest_file,
    parse_file,
)

EXAMPLES = Path(__file__).resolve().parents[3] / "data/examples"


@pytest.mark.parametrize("extension", ["csv", "json", "jsonl"])
def test_equivalent_formats(extension: str) -> None:
    rows = parse_file(EXAMPLES / f"fragrances.{extension}")
    assert rows == parse_file(EXAMPLES / "fragrances.json")
    assert rows[0].fragrance_name == "Papier d’Étoiles"
    assert {n.position for n in rows[0].notes} == {"top", "heart", "base", "unknown"}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("EDP", "eau_de_parfum"),
        ("Eau de Toilette", "eau_de_toilette"),
        ("EXTRAIT", "extrait_de_parfum"),
        (None, None),
        ("  ", None),
        ("ＥＤＰ", "eau_de_parfum"),
    ],
)
def test_normalization(value: str | None, expected: str | None) -> None:
    assert concentration(value) == expected
    assert key("  Ｍaison\tÉLAN\n") == "maison élan"


def test_missing_optional_fields_and_unknowns(tmp_path: Path) -> None:
    path = tmp_path / "minimal.csv"
    path.write_text(
        'source_record_id,brand_name,fragrance_name\n1,"Élan, Imaginaire",Unknown\n'
    )
    record = parse_file(path)[0]
    assert record.brand_name == "Élan, Imaginaire"
    assert (
        record.release_year is None
        and record.concentration is None
        and record.notes == []
    )


@pytest.mark.parametrize(
    "content,suffix",
    [
        ('[{"brand_name":"secret"}]', ".json"),
        ("[NaN]", ".json"),
        ('[{"a":1,"a":2}]', ".json"),
        ("{", ".json"),
        ("[]", ".json"),
        ("{}", ".json"),
        ("{}\nnot-json", ".jsonl"),
        ("a,a\n1,2", ".csv"),
        ("a,b\n1,2,3", ".csv"),
        ('a,b\n"open', ".csv"),
        ("x", ".xml"),
        ('["\\u0000"]', ".json"),
        ("[" * 200 + "]" * 200, ".json"),
    ],
)
def test_malformed_sanitized(tmp_path: Path, content: str, suffix: str) -> None:
    path = tmp_path / ("input" + suffix)
    path.write_text(content)
    with pytest.raises(ImportErrorSafe) as exc:
        parse_file(path)
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize(
    "case", ["bytes", "rows", "name", "depth", "duplicate", "encoding", "arrays"]
)
def test_input_bounds(tmp_path: Path, case: str) -> None:
    path = tmp_path / "input.json"
    row = {"source_record_id": "1", "brand_name": "House", "fragrance_name": "Scent"}
    if case == "bytes":
        path.write_bytes(b" " * (MAX_BYTES + 1))
    elif case == "rows":
        path.write_text(json.dumps([row] * (MAX_ROWS + 1)))
    elif case == "name":
        path.write_text(json.dumps([{**row, "brand_name": "x" * 201}]))
    elif case == "depth":
        path.write_text(json.dumps([[[[[[[[row]]]]]]]]))
    elif case == "duplicate":
        path.write_text(json.dumps([row, row]))
    elif case == "encoding":
        path.write_bytes(b"\xff")
    else:
        path.write_text(json.dumps([{**row, "perfumers": ["P"] * 11}]))
    with pytest.raises(ImportErrorSafe):
        parse_file(path)


@pytest.mark.parametrize(
    "updates",
    [
        {"concentration": "mystery"},
        {"brand_name": "  "},
        {"gtin": "123"},
        {"gtin": "12345678", "bottle_sizes_ml": [50, 100]},
        {"bottle_sizes_ml": [float("inf")]},
        {"bottle_sizes_ml": [50.1234]},
        {"source_url": "https://user:password@example.com"},
        {"release_year": 999},
        {"unknown": "field"},
    ],
)
def test_record_validation(updates: dict) -> None:
    with pytest.raises(ValueError):
        Record.model_validate(
            {
                "source_record_id": "1",
                "brand_name": "House",
                "fragrance_name": "Scent",
                **updates,
            }
        )


def test_manifest_needs_explicit_schema(tmp_path: Path) -> None:
    original = manifest_file(EXAMPLES / "source-manifest.json")
    assert original.authorization_status == "approved"  # Still not DB authority.
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps({**original.model_dump(), "license_evidence_references": []})
    )
    with pytest.raises(ImportErrorSafe):
        manifest_file(path)


@pytest.mark.parametrize("gtin,valid", [("12345670", True), ("12345671", False)])
def test_gtin_check_digits(gtin: str, valid: bool) -> None:
    raw = {
        "source_record_id": "1",
        "brand_name": "Fictional",
        "fragrance_name": "Example",
        "gtin": gtin,
    }
    if valid:
        assert Record.model_validate(raw).gtin == gtin
    else:
        with pytest.raises(ValueError):
            Record.model_validate(raw)
