"""Redis-backed fixed-window login limiter (decision 0019, Q-002=B).

Fail-closed (fail-loud, 0017): if the limiter cannot talk to Redis, login
refuses with 503 rather than running unchecked. Any limiter error is
surfaced as `LimiterUnavailable`; the router maps it to 503.

X-Forwarded-For is never trusted — the IP dimension is the socket peer
address only (decision 0019).
"""

from __future__ import annotations

import os

import redis.asyncio as redis

LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 900

_CONFIG_FILE = "/etc/scriptorium/config.env"


class LimiterUnavailable(RuntimeError):
    """Redis unreachable/misconfigured — requests keyed on the limiter fail closed."""


def _redis_url() -> str:
    url = os.environ.get("REDIS_URL")
    if not url and os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("REDIS_URL="):
                    url = line.split("=", 1)[1].strip().strip("'\"")
    if not url:
        raise LimiterUnavailable(
            "REDIS_URL is not set (env or /etc/scriptorium/config.env)."
        )
    return url


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise LimiterUnavailable(f"{name} must be an integer, got {raw!r}") from exc


def max_failures() -> int:
    return _env_int("SCRIPTORIUM_RATELIMIT_LOGIN_MAX", LOGIN_MAX_FAILURES)


def window_seconds() -> int:
    return _env_int("SCRIPTORIUM_RATELIMIT_LOGIN_WINDOW_S", LOGIN_WINDOW_SECONDS)


def _ip_key(peer_ip: str) -> str:
    return f"limit:login:ip:{peer_ip}"


def _email_key(email_addr: str) -> str:
    return f"limit:login:email:{email_addr}"


_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(_redis_url(), decode_responses=True)
    return _client


def reset_client() -> None:
    """Drop the cached client (tests use one event loop per test)."""
    global _client
    _client = None


async def dispose_client() -> None:
    """Close the cached client ON the current loop, then clear the cache.

    redis-py sends its sockets through per-loop transports; dropping the
    reference without closing makes GC raise ResourceWarning-style noise
    during a later test (Rule 6 under -W error), so tests close it in the
    loop that owns it (mirror of app.db.dispose_engine).
    """
    global _client
    if _client is not None:
        client, _client = _client, None
        await client.aclose()


async def usage(peer_ip: str, email_addr: str) -> int:
    """Failures used so far under the tighter of the two counters."""
    try:
        client = get_client()
        ip_used = int(await client.get(_ip_key(peer_ip)) or 0)
        email_used = int(await client.get(_email_key(email_addr)) or 0)
        return max(ip_used, email_used)
    except (redis.RedisError, OSError, ValueError) as exc:
        raise LimiterUnavailable(f"Redis limiter unavailable: {exc}") from exc


async def count_failure(peer_ip: str, email_addr: str) -> None:
    """INCR both counters; window anchored at the first failure (SET NX EX + INCR).

    redis-py 6.4.0 has no `keepttl` in its stubs; SET-NX-EX then INCR gives
    identical fixed-window semantics (TTL set at first failure, INCR never
    resets TTL).
    """
    try:
        client = get_client()
        window = window_seconds()
        pipe = client.pipeline()
        pipe.set(_ip_key(peer_ip), 0, ex=window, nx=True)
        pipe.incr(_ip_key(peer_ip))
        pipe.set(_email_key(email_addr), 0, ex=window, nx=True)
        pipe.incr(_email_key(email_addr))
        await pipe.execute()
    except (redis.RedisError, OSError) as exc:
        raise LimiterUnavailable(f"Redis limiter unavailable: {exc}") from exc


async def clear(peer_ip: str, email_addr: str) -> None:
    """Clear both counters (successful login resets the window at once)."""
    try:
        await get_client().delete(_ip_key(peer_ip), _email_key(email_addr))
    except (redis.RedisError, OSError) as exc:
        raise LimiterUnavailable(f"Redis limiter unavailable: {exc}") from exc


async def retry_after(peer_ip: str, email_addr: str) -> int:
    """Remaining seconds on the tighter counter for the Retry-After header."""
    try:
        client = get_client()
        ttls = (
            await client.ttl(_ip_key(peer_ip)),
            await client.ttl(_email_key(email_addr)),
        )
        alive = [t for t in ttls if t > 0]
        return max(alive) if alive else window_seconds()
    except (redis.RedisError, OSError) as exc:
        raise LimiterUnavailable(f"Redis limiter unavailable: {exc}") from exc
