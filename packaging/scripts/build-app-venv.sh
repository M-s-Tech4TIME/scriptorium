#!/bin/sh
# Build the application venv at package-build time from the pinned runtime.
# Never installs packages on the target host.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:-"$ROOT/app-venv"}
PYTHON=${PYTHON:-"$ROOT/python-runtime/bin/python3.14"}

case "$DEST" in
  "" | "/")
    echo "refusing unsafe app-venv destination: $DEST" >&2
    exit 2
    ;;
esac

if [ ! -x "$PYTHON" ]; then
  echo "missing bundled Python runtime: $PYTHON (run fetch-python.sh first)" >&2
  exit 2
fi

"$PYTHON" -m venv --copies --clear "$DEST"
"$DEST/bin/python" -m pip install --no-cache-dir --no-compile --no-deps \
  -r "$ROOT/../backend/requirements.prod.lock"

"$DEST/bin/python" - <<'PY'
import sys

import alembic
import asyncpg
import celery
import fastapi
import pydantic
import sqlalchemy

expected = {
    "fastapi": "0.162.0",
    "sqlalchemy": "2.1.6",
    "alembic": "1.20.1",
    "asyncpg": "0.32.0",
    "celery": "5.6.3",
    "pydantic": "2.14.1",
}
actual = {
    "fastapi": fastapi.__version__,
    "sqlalchemy": sqlalchemy.__version__,
    "alembic": alembic.__version__,
    "asyncpg": asyncpg.__version__,
    "celery": celery.__version__,
    "pydantic": pydantic.__version__,
}
if actual != expected:
    raise SystemExit(f"app venv version mismatch: {actual!r} != {expected!r}")
print(f"app venv ready: {sys.executable}")
PY

# The package installs application code outside the venv, so provide the
# console entry point explicitly. relocate-venv.sh rewrites the shebang.
cat > "$DEST/bin/scriptorium-admin" <<'PY'
#!/opt/scriptorium/backend/.venv/bin/python
import sys

sys.path.insert(0, "/opt/scriptorium/backend")

from app.cli import main

raise SystemExit(main())
PY
chmod 0755 "$DEST/bin/scriptorium-admin"

# The installed venv is a runtime, not a package manager. Drop pip and
# bytecode to keep the package small; target hosts never install packages.
rm -rf "$DEST"/lib/python3.14/site-packages/pip \
  "$DEST"/lib/python3.14/site-packages/pip-*.dist-info
rm -f "$DEST"/bin/pip "$DEST"/bin/pip3 "$DEST"/bin/pip3.14
find "$DEST" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$DEST" -type f -name '*.pyc' -delete

"$ROOT/scripts/relocate-venv.sh" "$DEST" /opt/scriptorium/backend/.venv \
  /opt/scriptorium/runtime/python-3.14
