#!/usr/bin/env sh
set -eu

echo "[cliperry] running pytestâ€¦"
pytest -q --maxfail=1 "$@"
