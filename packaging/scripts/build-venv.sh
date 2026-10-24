#!/bin/sh
# Create the isolated Sphinx build venv (decision 0026 P3).
#
# Run at PACKAGE-BUILD time, before nfpm packages ./build-venv. The
# installed tree must never run pip or reach the network. The lock is
# constrained by the app lock so shared transitive pins cannot drift.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:-"$ROOT/build-venv"}
PYTHON=${PYTHON:-python3.12}

case "$DEST" in
  "" | "/")
    echo "refusing unsafe build-venv destination: $DEST" >&2
    exit 2
    ;;
esac

"$PYTHON" -m venv --clear "$DEST"
"$DEST/bin/python" -m pip install --no-cache-dir --no-deps \
  -r "$ROOT/build-requirements.lock"

# Hermeticity proof: the pinned engine trio is present, app deps are not.
"$DEST/bin/python" - <<'PY'
import importlib.util
import sys

import docutils
import myst_parser
import sphinx

expected = {
    "sphinx": "9.1.0",
    "docutils": "0.22.4",
    "myst-parser": "5.1.0",
}
actual = {
    "sphinx": sphinx.__version__,
    "docutils": docutils.__version__,
    "myst-parser": myst_parser.__version__,
}
if actual != expected:
    raise SystemExit(f"build venv version mismatch: {actual!r} != {expected!r}")
for forbidden in ("fastapi", "sqlalchemy", "celery", "asyncpg", "alembic"):
    if importlib.util.find_spec(forbidden) is not None:
        raise SystemExit(f"build venv is not isolated: {forbidden} is installed")
print(f"build venv ready: {sys.executable}")
PY
