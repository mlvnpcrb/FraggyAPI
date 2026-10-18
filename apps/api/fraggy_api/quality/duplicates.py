"""Conservative candidate labels. None of these decisions authorizes a merge."""

from typing import Any

from ..importing.formats import key


def classify_pair(left: dict[str, Any], right: dict[str, Any]) -> str:
    if not key(left.get("brand", "")) or not key(right.get("brand", "")):
        return "incomplete_identity"
    if key(left.get("brand", "")) != key(right.get("brand", "")):
        return "different_brand"
    a, b = key(left.get("name", "")), key(right.get("name", ""))
    if not a or not b:
        return "incomplete_identity"
    if a != b:
        return (
            "related_name_review" if a.split()[0] == b.split()[0] else "different_name"
        )
    if (
        left.get("version")
        or right.get("version")
        or left.get("reformulation")
        or right.get("reformulation")
    ):
        return "distinct_version_review"
    c, d = left.get("concentration"), right.get("concentration")
    if c and d and c != d:
        return "distinct_concentration"
    y, z = left.get("year"), right.get("year")
    if y and z and y != z:
        return "distinct_year_review"
    if not c or not d or y is None or z is None:
        return "incomplete_identity"
    return "possible_duplicate"
