#!/bin/bash
# 0017 docutils-0.23 probe mechanics.
#
# docutils 0.22.4 is the frozen pin; 0.23 is gated (0003). MyST-Parser
# 5.1.0 still declares an upper bound below 0.23, so the probe forces
# the candidate into an isolated venv with --no-deps and runs the
# converter + real Sphinx-build suites. Run this manually (or via the
# workflow_dispatch job) before proposing a version bump. It is NOT a
# push gate: a red probe means "stay on 0.22.4", not "break dev CI".
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON=${PYTHON:-python3.14}
WORK=$(mktemp -d "${TMPDIR:-/tmp}/scriptorium-docutils-probe.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

"$PYTHON" -m venv "$WORK/venv"
"$WORK/venv/bin/python" -m pip install --no-cache-dir -r "$ROOT/backend/requirements.lock"
"$WORK/venv/bin/python" -m pip install --no-cache-dir --no-deps --upgrade "docutils==0.23"

"$WORK/venv/bin/python" - <<'PY'
import docutils
import myst_parser
import sphinx

print(
    f"probe versions: sphinx={sphinx.__version__} "
    f"docutils={docutils.__version__} myst-parser={myst_parser.__version__}"
)
if docutils.__version__ != "0.23":
    raise SystemExit(f"docutils probe did not install 0.23: {docutils.__version__}")
PY

cd "$ROOT"
"$WORK/venv/bin/python" -m pytest \
  backend/tests/test_roundtrip.py \
  backend/tests/test_sourcegen.py \
  backend/tests/test_theme_build.py \
  -W error -q
