#!/usr/bin/env bash
# Local pre-push check: rebuild data (+ guard), then run both test suites.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> build data (reconstruction guard)"
python3 build_data.py

echo "==> rebuild similarity artifacts from canonical data"
PYTHON="python3"; [ -x .venv/bin/python ] && PYTHON=".venv/bin/python"
$PYTHON analysis/path_features.py
$PYTHON analysis/similarity.py >/dev/null
$PYTHON analysis/cluster_map.py >/dev/null

echo "==> committed generated artifacts are up to date"
# diff against HEAD (not the index) so a stale-but-staged data.js still fails
git diff --quiet HEAD -- site/data.js site/data.json site/skill-events.json site/kor.json site/kor-detail.json site/similarity.js site/clusters.js || {
  echo "  generated artifacts changed — commit the regenerated files"; exit 1;
}

echo "==> pytest checks"
PYTEST="python3 -m pytest"; [ -x .venv/bin/pytest ] && PYTEST=".venv/bin/pytest"
$PYTEST -q

echo "==> browser/layout tests"
npx playwright test

echo "✓ all checks passed"
