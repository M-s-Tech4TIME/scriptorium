"""Shared configuration loader (decision 0040, Q-SM-M = M1).

Every process — web, worker, and ``scriptorium-admin`` — reads the same
``/etc/scriptorium/config.env`` file. The loader deliberately does **no**
shell evaluation: no variable expansion, no command substitution, no
``source`` semantics. A real environment variable always wins over the
file, so systemd overrides and test/dev environments behave exactly as
before. This is the parity contract the CLI needs to see the same
database, roots, secret, and TLS paths as the services.

The file format is intentionally the same one systemd's
``EnvironmentFile=`` accepts: ``KEY=VALUE`` per line, blank lines and
``#`` comments ignored, optional matching single/double quotes around the
value. Anything else fails loud rather than being silently ignored.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

CONFIG_FILE = "/etc/scriptorium/config.env"

_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class ConfigError(RuntimeError):
    """The configuration file is malformed or a value is invalid."""


def config_file() -> Path:
    return Path(CONFIG_FILE)


def set_config_file(path: str | os.PathLike[str]) -> None:
    """Point the loader at an explicit file (``scriptorium-admin --config``)."""
    global CONFIG_FILE
    CONFIG_FILE = str(path)
    reset_config_cache()


def reset_config_cache() -> None:
    """Drop the parsed-file cache (tests and explicit reloads)."""
    _load_cached.cache_clear()


def _parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return values
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"{path}:{number}: expected KEY=VALUE.")
        key, value = line.split("=", 1)
        key = key.strip()
        if not _KEY_RE.fullmatch(key):
            raise ConfigError(f"{path}:{number}: invalid key {key!r}.")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


@lru_cache(maxsize=8)
def _load_cached(path_text: str, mtime_ns: int, size: int) -> dict[str, str]:
    # mtime/size make the cache self-invalidating when an operator edits the
    # file; the values are part of the key, never read inside the function.
    del mtime_ns, size
    return _parse(Path(path_text))


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, str]:
    """Return the parsed file values (empty when the file does not exist)."""
    target = Path(path) if path is not None else config_file()
    try:
        stat = target.stat()
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ConfigError(f"Cannot stat config file {target}: {exc}") from exc
    return dict(_load_cached(str(target), stat.st_mtime_ns, stat.st_size))


def get_setting(name: str, default: str | None = None) -> str | None:
    """Environment first, then the config file, then ``default``.

    An environment variable that is present but empty still wins — that is
    how an operator explicitly clears a value (and how ``SECRET_KEY=`` fails
    loud instead of silently falling back to a file value).
    """
    if name in os.environ:
        return os.environ[name]
    values = load_config()
    if name in values:
        return values[name]
    return default


def require_setting(name: str) -> str:
    value = get_setting(name)
    if value is None or value == "":
        raise ConfigError(f"{name} is not set (environment or {config_file()}).")
    return value


def get_int_setting(name: str, default: int) -> int:
    raw = get_setting(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}.") from exc


def get_bool_setting(name: str, default: bool = False) -> bool:
    raw = get_setting(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")
