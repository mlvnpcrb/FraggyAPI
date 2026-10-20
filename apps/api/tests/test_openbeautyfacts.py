"""Original data exercising a publisher-documented contract, never a live source."""

import json
from datetime import UTC, datetime

import pytest
from fraggy_api.collection.openbeautyfacts import parse_search
from fraggy_api.collection.policy import CollectionError


def page(**changes):
    product = {
        "code": "1234567890128",
        "product_name": "Invented Orchard EDP",
        "brands": "Original Fictional Studio",
        "categories_tags": ["en:perfumes"],
        "quantity": "50 ml",
        "product_type": "beauty",
        **changes,
    }
    return json.dumps(
        {"page": 1, "page_size": 25, "page_count": 1, "count": 1, "products": [product]}
    ).encode()


def parse(body):
    return parse_search(body, collected_at=datetime(2026, 10, 19, tzinfo=UTC))


def test_official_shape_preserves_raw_provenance_without_inventing_facts():
    observation = parse(page())["observations"][0]
    candidate = observation["proposed_record"]
    assert observation["raw"]["quantity"] == "50 ml"
    assert candidate["bottle_sizes_ml"] == [50]
    assert candidate["gtin"] == "1234567890128"
    assert candidate["fragrance_name"] == "Invented Orchard EDP"
    assert candidate["concentration"] is None  # Title is not a reviewed release.
    assert candidate["release_year"] is None
    assert candidate["notes"] == candidate["perfumers"] == candidate["accords"] == []
    assert observation["provenance"]["brand_name"] == "brands"
    assert not observation["import_authorized"]
    assert not observation["publication_authorized"]


def test_product_identity_and_variants_require_review():
    assert (
        parse(page(categories_tags=["en:soaps"]))["observations"][0]["proposed_record"]
        is None
    )
    assert (
        parse(page(brands="Invented A, Invented B"))["observations"][0][
            "proposed_record"
        ]
        is None
    )
    observation = parse(page(code="2001", quantity="2 x 50 ml"))["observations"][0]
    assert observation["proposed_record"]["gtin"] is None
    assert observation["proposed_record"]["bottle_sizes_ml"] == []
    assert "quantity_requires_variant_review" in observation["review_issues"]


def test_schema_drift_private_fields_and_pagination_fail_closed():
    with pytest.raises(CollectionError, match="unexpected_product_fields"):
        parse(page(image_url="https://example.invalid/not-fetched"))
    envelope = json.loads(page())
    envelope["page_count"] = 2
    with pytest.raises(CollectionError, match="invalid_search_pagination"):
        parse(json.dumps(envelope).encode())
    envelope["products"] *= 2
    envelope["count"] = 2
    with pytest.raises(CollectionError, match="duplicate_product_reference"):
        parse(json.dumps(envelope).encode())
