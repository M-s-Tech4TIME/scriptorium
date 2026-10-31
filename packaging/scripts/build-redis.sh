#!/bin/sh
# Build the pinned Redis server from source at package-build time.
# The installed package never compiles or fetches code.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEST=${1:-"$ROOT/redis-runtime"}
REDIS_VERSION=8.10.2
SHA256=b9ffee226b5eecdba98a679260dad764b2a4ebd90dce4ad5ac9e9f3eef9c02b3

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

curl -fsSL "https://download.redis.io/releases/redis-${REDIS_VERSION}.tar.gz" \
  -o "$TMP/redis.tar.gz"
printf '%s  %s\n' "$SHA256" "$TMP/redis.tar.gz" | sha256sum -c -
tar -xzf "$TMP/redis.tar.gz" -C "$TMP"
# Core server only: the Redis 8.10.2 default build also compiles optional
# modules that need extra build-only headers. Scriptorium uses core Redis.
make -C "$TMP/redis-${REDIS_VERSION}/src" -j"$(nproc)" \
  BUILD_TLS=no MALLOC=libc redis-server redis-cli
rm -rf "$DEST"
mkdir -p "$DEST/bin"
install -m 0755 "$TMP/redis-${REDIS_VERSION}/src/redis-server" "$DEST/bin/redis-server"
install -m 0755 "$TMP/redis-${REDIS_VERSION}/src/redis-cli" "$DEST/bin/redis-cli"
"$DEST/bin/redis-server" --version
