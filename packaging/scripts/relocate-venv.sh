#!/bin/sh
# Make a build-host venv relocatable to its installed path.
# Usage: relocate-venv.sh <venv> <final-venv> <final-python-runtime>
set -eu

VENV=$1
FINAL_VENV=$2
FINAL_RUNTIME=$3

[ -f "$VENV/pyvenv.cfg" ] || { echo "not a venv: $VENV" >&2; exit 2; }

sed -i "s|^home = .*|home = $FINAL_RUNTIME/bin|" "$VENV/pyvenv.cfg"
sed -i "s|^executable = .*|executable = $FINAL_RUNTIME/bin/python3.14|" "$VENV/pyvenv.cfg"

for name in python python3 python3.14; do
  rm -f "$VENV/bin/$name"
  ln -s "$FINAL_RUNTIME/bin/python3.14" "$VENV/bin/$name"
done

for f in "$VENV"/bin/*; do
  [ -f "$f" ] || continue
  if head -n 1 "$f" | grep -q '^#!'; then
    sed -i "1s|^#!.*|#!$FINAL_VENV/bin/python|" "$f"
  fi
done
