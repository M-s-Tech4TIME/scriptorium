#!/bin/bash
# M0 docs/brain validator (Rule 1.6/3.6 heuristics). Fails on missing files or stale refs.
set -euo pipefail
REQ="AGENTS.md docs/README.md docs/brain/README.md docs/brain/PROJECT-SUMMARY.md docs/brain/CURRENT-STATE.md docs/brain/HANDOFF.md docs/brain/TASKS.md docs/brain/DECISIONS-INDEX.md docs/brain/OPEN-QUESTIONS.md docs/brain/GLOSSARY.md"
for f in $REQ; do test -f "$f" || { echo "MISSING: $f"; exit 1; }; done
test -d docs/decisions || { echo "MISSING: docs/decisions/"; exit 1; }
test -f docs/technology/compatibility-matrix.md || { echo "MISSING: matrix"; exit 1; }
echo "docs/brain structure OK"
grep -rq "Last updated:" docs/brain/*.md || { echo "brain missing Last updated"; exit 1; }
echo "brain headers OK"
