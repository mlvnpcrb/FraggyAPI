"""Expose safe JUnit test identifiers through GitHub annotations, never test data."""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1])
    try:
        if path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("Oversized report")
        root = ET.parse(path).getroot()
    except (OSError, ValueError, ET.ParseError):
        print(
            "::error title=Backend test diagnostics::JUnit report unavailable; inspect the failing test step"
        )
        return
    for case in root.iter("testcase"):
        failures = [*case.findall("failure"), *case.findall("error")]
        if not failures:
            continue
        # Parameterized values, assertion text and captured output may contain
        # private inputs. Only static identifiers and allowlisted categories leave.
        name = case.get("name", "unknown").split("[", 1)[0]
        identifier = re.sub(
            r"[^A-Za-z0-9_.-]", "_", case.get("classname", "") + "." + name
        )[:200]
        content = " ".join(
            (item.get("message", "") + " " + (item.text or "")) for item in failures
        )
        category = next(
            (
                kind
                for kind in (
                    "QueryCanceledError",
                    "DBAPIError",
                    "AssertionError",
                    "TimeoutError",
                    "OperationalError",
                    "ImportErrorSafe",
                )
                if kind in content
            ),
            "test_failure",
        )
        print(f"::error title=Backend test failure::{identifier} ({category})")


if __name__ == "__main__":
    main()
