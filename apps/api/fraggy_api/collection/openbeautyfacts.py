"""Offline reader for the official Product Opener search contract; no HTTP or writes.

Contract: openfoodfacts/openfoodfacts-server f7f60fb43a8fa54d30d748589265a19f4b27d1d3,
docs/api/ref/responses/search_for_products.yaml and schemas/product_base.yaml.
Using this parser does not authorize access, storage, import or publication.
"""

import json
import re
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from ..importing.formats import MAX_BYTES, Record, bounded, digest
from .policy import CollectionError

SOURCE = "openbeautyfacts"
FIELDS = (
    "code,product_name,brands,brands_tags,categories_tags,quantity,"
    "product_type,last_modified_t"
)


def parse_search(body: bytes, *, collected_at: datetime) -> dict[str, Any]:
    """Keep supplied observations separate from proposed mappings for manual review.

    Accept at most 25 products per page; callers need separate source permission
    before supplying genuine data. No data is fetched, persisted or staged here.
    """
    if collected_at.tzinfo is None or len(body) > MAX_BYTES:
        raise CollectionError("invalid_observation_bounds")
    try:
        payload = json.loads(body)
        bounded(payload)
    except (ValueError, UnicodeError, RecursionError) as error:
        raise CollectionError("malformed_source_response") from error
    if not isinstance(payload, dict):
        raise CollectionError("invalid_search_envelope")
    for field in ("page", "page_size", "page_count", "count"):
        value = payload.get(field)
        if type(value) is not int or value < (
            1 if field in {"page", "page_size"} else 0
        ):
            raise CollectionError("invalid_search_pagination")
    products = payload.get("products")
    if (
        not isinstance(products, list)
        or not 1 <= payload["page_size"] <= 25
        or len(products) > payload["page_size"]
        or payload["page_count"] != len(products)
        or payload["count"] < len(products)
    ):
        raise CollectionError("invalid_search_pagination")
    observations = []
    seen: set[str] = set()
    for product in products:
        if not isinstance(product, dict) or set(product) - set(FIELDS.split(",")):
            # Do not retain unexpected contributor identities or image fields.
            raise CollectionError("unexpected_product_fields")
        code = product.get("code")
        if not isinstance(code, str) or not re.fullmatch(r"[0-9]{1,24}", code):
            raise CollectionError("invalid_product_reference")
        if code in seen:
            raise CollectionError("duplicate_product_reference")
        seen.add(code)
        for field in ("brands_tags", "categories_tags"):
            tags = product.get(field, [])
            if not isinstance(tags, list) or not all(
                isinstance(value, str) for value in tags
            ):
                raise CollectionError("invalid_product_tags")
        for field in ("product_name", "brands", "quantity", "product_type"):
            if field in product and not isinstance(product[field], str):
                raise CollectionError("invalid_product_field")
        if "last_modified_t" in product and (
            type(product["last_modified_t"]) is not int
            or product["last_modified_t"] < 0
        ):
            raise CollectionError("invalid_product_timestamp")
        issues = ["identity_and_release_require_human_review"]
        if product.get("product_type") not in (None, "beauty"):
            issues.append("not_beauty_product")
        if "en:perfumes" not in product.get("categories_tags", []):
            issues.append("fragrance_category_not_confirmed")
        brand = product.get("brands", "").strip()
        name = product.get("product_name", "").strip()
        if not brand or "," in brand:
            issues.append("brand_missing_or_ambiguous")
        if not name:
            issues.append("product_name_missing")
        source_url = f"https://world.openbeautyfacts.org/product/{code}"
        candidate = None
        transformations = []
        if len(issues) == 1:
            values: dict[str, Any] = {
                "source_record_id": code,
                "source_url": source_url,
                "brand_name": brand,
                "fragrance_name": name,
            }
            try:
                Record.model_validate({**values, "gtin": code})
                values["gtin"] = code
                transformations.append(
                    "code_to_gtin_after_length_and_checksum_validation"
                )
            except ValidationError:
                issues.append("internal_or_invalid_gtin_not_promoted")
            quantity = product.get("quantity", "").strip()
            size = re.fullmatch(r"([0-9]+(?:[.,][0-9]{1,3})?)\s*ml", quantity, re.I)
            if size and 0 < float(size[1].replace(",", ".")) <= 999999:
                values["bottle_sizes_ml"] = [float(size[1].replace(",", "."))]
                transformations.append("single_explicit_ml_quantity_to_bottle_size")
            elif quantity:
                issues.append("quantity_requires_variant_review")
            try:
                candidate = Record.model_validate(values).model_dump(mode="json")
            except ValidationError:
                issues.append("canonical_mapping_requires_correction")
        observations.append(
            {
                "source": SOURCE,
                "source_record_id": code,
                "source_url": source_url,
                "collected_at": collected_at.isoformat(),
                "observation_hash": digest(product),
                "raw": product,
                "proposed_record": candidate,
                "provenance": {
                    "brand_name": "brands",
                    "fragrance_name": "product_name",
                    "gtin": "code",
                    "bottle_sizes_ml": "quantity",
                }
                if candidate
                else {},
                "transformations": transformations,
                "review_issues": issues,
                "usage_rights": "pending_source_specific_review",
                "import_authorized": False,
                "publication_authorized": False,
            }
        )
    return {
        "source": SOURCE,
        "page": payload["page"],
        "total_reported": payload["count"],
        "observations": observations,
        "page_hash": digest(payload),
        "network_enabled": False,
        "automatic_merge": False,
    }
