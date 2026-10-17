#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Keep pnpm's state within the writable project in restricted cloud machines.
export XDG_DATA_HOME="$PWD/.pnpm-store/data"
pnpm install --frozen-lockfile
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements-dev.lock
.venv/bin/python -m pip install --no-deps --no-build-isolation -e apps/api
