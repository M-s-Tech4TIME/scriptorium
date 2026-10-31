#!/bin/sh
# Fetch the pinned python-build-standalone runtime for package builds.
# Never runs at install time; nfpm packages the extracted tree.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:-"$ROOT/python-runtime"}
PYTHON_VERSION=3.14.10
PBS_RELEASE=20261026

case "$(uname -m)" in
  x86_64)  ARCH=x86_64-unknown-linux-gnu;  SHA256=4d3c16c59ed0802a3d1d34d8bce504b15ceeaff39d62dadecc6a9fa803412aed ;;
  aarch64) ARCH=aarch64-unknown-linux-gnu; SHA256=90f48337bc3dd4ae6eda81e001e4c981236d403b6b5a07778bbdf94ee423dc00 ;;
  *) echo "unsupported architecture: $(uname -m)" >&2; exit 2 ;;
esac

ASSET="cpython-${PYTHON_VERSION}+${PBS_RELEASE}-${ARCH}-install_only_stripped.tar.gz"
ASSET_ENCODED=$(printf '%s' "$ASSET" | sed 's/+/%2B/g')
URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_RELEASE}/${ASSET_ENCODED}"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "$URL" -o "$TMP/python.tar.gz"
printf '%s  %s\n' "$SHA256" "$TMP/python.tar.gz" | sha256sum -c -
rm -rf "$DEST"
mkdir -p "$DEST"
tar -xzf "$TMP/python.tar.gz" -C "$DEST" --strip-components=1
"$DEST/bin/python3.14" --version

# The bundled runtime is a runtime, not a package manager. venv creation
# still works via ensurepip; remove the preinstalled pip payload.
rm -rf "$DEST"/lib/python3.14/site-packages/pip \
  "$DEST"/lib/python3.14/site-packages/pip-*.dist-info
rm -f "$DEST"/bin/pip "$DEST"/bin/pip3 "$DEST"/bin/pip3.14
