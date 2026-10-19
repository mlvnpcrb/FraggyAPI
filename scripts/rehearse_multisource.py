"""Read synthetic local fixture pages; never fetch, import, schedule or publish."""

import argparse
import json
from pathlib import Path

from fraggy_api.collection.multisource import Checkpoint, rehearse
from fraggy_api.collection.offline_sources import FixturePage
from fraggy_api.importing.formats import loads, read_text


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixtures", nargs="*", type=Path)
    parser.add_argument("--resume-report", type=Path)
    args = parser.parse_args()
    try:
        checkpoint = None
        if args.resume_report:
            with args.resume_report.open("rb") as handle:
                body = handle.read(16 * 1024 * 1024 + 1)
            if len(body) > 16 * 1024 * 1024:
                raise ValueError("Checkpoint report too large")
            checkpoint = Checkpoint.model_validate(loads(body.decode())["checkpoint"])
        paths = args.fixtures or sorted(
            Path("data/examples/multisource").glob("*.json")
        )
        if not paths or len(paths) > 100:
            raise ValueError("Bounded fixture pages required")
        pages = (FixturePage.model_validate(loads(read_text(path))) for path in paths)
        result = rehearse(pages, checkpoint)
    except Exception:
        print(json.dumps({"error": "offline_multisource_rehearsal_failed"}))
        raise SystemExit(1) from None
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
