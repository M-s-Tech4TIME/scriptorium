"""TLS paths, metadata, and atomic state persistence (decision 0040).

All Scriptorium-managed files are owned by ``scriptorium:scriptorium``;
the CA private key is the sole TLS exception and is ``root:root 0600``.
The functions here never decide ownership on their own — the manager
applies it when running as root, and leaves test/dev roots alone.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from app.config import get_int_setting, get_setting

DEFAULT_TLS_ROOT = Path("/etc/scriptorium/tls")
CURRENT_NAME = "current"
VERSIONS_NAME = "versions"
CA_KEY_NAME = "ca.key"
CA_CERT_NAME = "ca.pem"
STATE_NAME = "state.json"
CERT_NAME = "fullchain.pem"
KEY_NAME = "privkey.pem"
META_NAME = "meta.json"


class TlsError(RuntimeError):
    """A TLS operation cannot proceed safely."""


def tls_root() -> Path:
    return Path(get_setting("SC_TLS_ROOT", str(DEFAULT_TLS_ROOT)) or "")


def cert_path() -> Path:
    return Path(
        get_setting("SC_TLS_CERT", str(tls_root() / CURRENT_NAME / CERT_NAME)) or ""
    )


def key_path() -> Path:
    return Path(
        get_setting("SC_TLS_KEY", str(tls_root() / CURRENT_NAME / KEY_NAME)) or ""
    )


def ca_key_path() -> Path:
    return tls_root() / CA_KEY_NAME


def ca_cert_path() -> Path:
    return tls_root() / CA_CERT_NAME


def state_path() -> Path:
    return tls_root() / STATE_NAME


def versions_dir() -> Path:
    return tls_root() / VERSIONS_NAME


def current_link() -> Path:
    return tls_root() / CURRENT_NAME


def current_version_dir() -> Path | None:
    link = current_link()
    try:
        if link.is_symlink():
            return link.resolve(strict=True)
    except OSError:
        return None
    return None


def version_dir(version: str) -> Path:
    if not version or "/" in version or "\\" in version or version in (".", ".."):
        raise TlsError(f"Invalid TLS version id {version!r}.")
    return versions_dir() / version


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def parse_iso(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise TlsError(f"{label} is not an ISO timestamp.")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise TlsError(f"{label} is not an ISO timestamp.") from exc
    if parsed.tzinfo is None:
        raise TlsError(f"{label} must include a timezone.")
    return parsed.astimezone(UTC)


@dataclass
class TlsState:
    mode: Literal["generated", "imported"] = "generated"
    version: str = ""
    activated_at: str = ""
    source: str = ""
    hsts: bool = False
    hsts_max_age: int = 31_536_000
    ca_created_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VersionMeta:
    version: str
    mode: Literal["generated", "imported"]
    created_at: str
    not_before: str
    not_after: str
    sans: list[str] = field(default_factory=list)
    fingerprint_sha256: str = ""
    source: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_state(*, strict: bool = False) -> TlsState:
    path = state_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if strict:
            raise TlsError(f"TLS state file is missing: {path}.") from None
        return TlsState()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        if strict:
            raise TlsError(f"TLS state file is unreadable: {path}.") from exc
        return TlsState()
    if not isinstance(raw, dict):
        if strict:
            raise TlsError(f"TLS state file is not an object: {path}.")
        return TlsState()
    mode = raw.get("mode", "generated")
    if mode not in ("generated", "imported"):
        mode = "generated"
    try:
        hsts_max_age = int(raw.get("hsts_max_age", 31_536_000))
    except TypeError, ValueError:
        hsts_max_age = 31_536_000
    return TlsState(
        mode=mode,
        version=str(raw.get("version", "")),
        activated_at=str(raw.get("activated_at", "")),
        source=str(raw.get("source", "")),
        hsts=bool(raw.get("hsts", False)),
        hsts_max_age=hsts_max_age,
        ca_created_at=(str(raw["ca_created_at"]) if raw.get("ca_created_at") else None),
    )


def write_state(state: TlsState) -> None:
    root = tls_root()
    root.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n"
    _atomic_write_text(state_path(), payload, mode=0o644)


def read_meta(directory: Path) -> VersionMeta:
    path = directory / META_NAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TlsError(f"TLS version metadata is missing: {path}.") from exc
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise TlsError(f"TLS version metadata is unreadable: {path}.") from exc
    if not isinstance(raw, dict):
        raise TlsError(f"TLS version metadata is not an object: {path}.")
    mode = raw.get("mode")
    if mode not in ("generated", "imported"):
        raise TlsError(f"TLS version metadata has an invalid mode: {path}.")
    sans = raw.get("sans", [])
    if not isinstance(sans, list) or not all(isinstance(item, str) for item in sans):
        raise TlsError(f"TLS version metadata has invalid SANs: {path}.")
    return VersionMeta(
        version=str(raw.get("version", directory.name)),
        mode=mode,
        created_at=str(raw.get("created_at", "")),
        not_before=str(raw.get("not_before", "")),
        not_after=str(raw.get("not_after", "")),
        sans=list(sans),
        fingerprint_sha256=str(raw.get("fingerprint_sha256", "")),
        source=str(raw.get("source", "")),
    )


def write_meta(directory: Path, meta: VersionMeta) -> None:
    payload = json.dumps(meta.as_dict(), indent=2, sort_keys=True) + "\n"
    _atomic_write_text(directory / META_NAME, payload, mode=0o644)


def hsts_enabled() -> bool:
    return read_state().hsts


def hsts_max_age() -> int:
    state = read_state()
    return state.hsts_max_age if state.hsts_max_age > 0 else 31_536_000


def configured_hsts_max_age() -> int:
    """Operator override from config; state remains the enable switch."""
    return get_int_setting("SC_TLS_HSTS_MAX_AGE", 31_536_000)


def _atomic_write_text(path: Path, text: str, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def atomic_write_bytes(path: Path, data: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
