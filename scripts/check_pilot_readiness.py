"""Validate a disabled offline proposal. Never approves or collects data."""

import argparse
import json
from pathlib import Path

from fraggy_api.importing.formats import loads, read_text
from fraggy_api.pilot_readiness import PilotProposal


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("proposal", type=Path)
    args = parser.parse_args()
    try:
        report = PilotProposal.model_validate(loads(read_text(args.proposal))).report()
    except (ValueError, OSError):
        parser.exit(1, "Invalid or enabled proposal; offline review only.\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
