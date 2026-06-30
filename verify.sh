#!/usr/bin/env bash
# Local pre-push check: rebuild data (+ guard), then run both test suites.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> build data (reconstruction guard)"
python3 build_data.py

echo "==> committed site/data.js is up to date"
git diff --quiet site/data.js || { echo "  site/data.js changed — commit the regenerated file"; exit 1; }

echo "==> data-integrity tests"
PYTEST="python3 -m pytest"; [ -x .venv/bin/pytest ] && PYTEST=".venv/bin/pytest"
$PYTEST tests/test_build_data.py -q

echo "==> browser/layout tests"
npx playwright test

echo "✓ all checks passed"
