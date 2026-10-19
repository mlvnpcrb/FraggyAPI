"""Offline Phase 2J report only. No live mode or external-access argument."""

import argparse
import json
from pathlib import Path

from fraggy_api.importing.formats import bounded, loads, read_text
from fraggy_api.pilot_preparation import PilotPlan, dry_run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("config/phase-2j-pilot.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    try:
        body = loads(read_text(args.plan))
        bounded(body)
        plan = PilotPlan.model_validate(body)
        result = dry_run(plan) if args.dry_run else plan.report()
    except Exception:
        print(json.dumps({"error": "offline_pilot_preparation_failed"}))
        raise SystemExit(1) from None
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
