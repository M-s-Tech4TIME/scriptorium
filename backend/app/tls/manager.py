"""TLS lifecycle: generate, renew, import, rollback, prune, status, verify.

The design is decision 0040 (Q-SM-F = F-A…F-L). Certificate activation is
atomic: a new version directory is fully written and validated, then the
``current`` symlink and state file are replaced together. If a live
``scriptorium-web`` service rejects the graceful reload, the previous
symlink and state are restored automatically (F-F1). Imported certificates
are never auto-renewed (F-D1).
"""

from __future__ import annotations

import grp
import os
import pwd
import shutil
import socket
import stat
import subprocess
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.config import get_setting
from app.tls.crypto import (
    SubjectAltName,
    TlsCryptoError,
    cert_days_left,
    cert_fingerprint,
    cert_issuer,
    cert_pem,
    cert_subject,
    detect_sans,
    generate_ca,
    generate_leaf,
    load_cert_chain,
    load_private_key,
    normalize_ip,
    parse_san,
    private_key_pem,
    sans_from_cert,
    validate_material,
)
from app.tls.state import (
    CA_CERT_NAME,
    CA_KEY_NAME,
    CERT_NAME,
    CURRENT_NAME,
    DEFAULT_TLS_ROOT,
    KEY_NAME,
    VERSIONS_NAME,
    TlsError,
    TlsState,
    VersionMeta,
    _atomic_write_text,
    atomic_write_bytes,
    ca_cert_path,
    ca_key_path,
    cert_path,
    configured_hsts_max_age,
    current_link,
    current_version_dir,
    iso,
    key_path,
    read_meta,
    read_state,
    state_path,
    tls_root,
    utcnow,
    version_dir,
    versions_dir,
    write_meta,
    write_state,
)

RENEW_AT_DAYS = 30
KEEP_VERSIONS = 5


@dataclass(frozen=True)
class TlsFinding:
    level: Literal["error", "warning"]
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class TlsStatus:
    configured: bool
    mode: str
    version: str
    cert_path: str
    key_path: str
    ca_cert_path: str
    subject: str
    issuer: str
    serial: str
    not_before: str
    not_after: str
    days_left: int
    sans: list[str] = field(default_factory=list)
    fingerprint_sha256: str = ""
    hsts: bool = False
    hsts_max_age: int = 31_536_000
    versions: int = 0
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenewResult:
    renewed: bool
    reason: str
    status: TlsStatus | None = None


@dataclass(frozen=True)
class ImportResult:
    version: str
    status: TlsStatus


def _new_version_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def _scriptorium_ids() -> tuple[int, int] | None:
    if os.geteuid() != 0:
        return None
    try:
        user = pwd.getpwnam("scriptorium")
        group = grp.getgrnam("scriptorium")
    except KeyError:
        return None
    return user.pw_uid, group.gr_gid


def _chown(path: Path, *, follow_symlinks: bool = True) -> None:
    ids = _scriptorium_ids()
    if ids is None:
        return
    try:
        os.chown(path, ids[0], ids[1], follow_symlinks=follow_symlinks)
    except OSError:
        pass


def _chown_tree(root: Path) -> None:
    _chown(root)
    for child in root.rglob("*"):
        _chown(child, follow_symlinks=False)


def _set_mode(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _load_ca() -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = load_private_key(ca_key_path())
    certs = load_cert_chain(ca_cert_path())
    if len(certs) != 1:
        raise TlsError("The local CA certificate file must contain exactly one cert.")
    cert = certs[0]
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise TlsError("The local CA key must be ECDSA P-384.")
    if key.curve.key_size < 384:
        raise TlsError("The local CA key is weaker than P-384.")
    errors = validate_material([cert], key, require_server_auth=False, allow_ca=True)
    if errors:
        raise TlsError("Local CA is invalid: " + "; ".join(errors))
    try:
        basic = cert.extensions.get_extension_for_class(x509.BasicConstraints).value
    except x509.ExtensionNotFound as exc:
        raise TlsError("The local CA certificate has no BasicConstraints.") from exc
    if not basic.ca:
        raise TlsError("The local CA certificate is not a CA.")
    return key, cert


def _ensure_ca() -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key_file = ca_key_path()
    cert_file = ca_cert_path()
    if key_file.exists() != cert_file.exists():
        raise TlsError(
            "The local CA is incomplete (ca.key/ca.pem must exist together)."
        )
    if key_file.exists():
        return _load_ca()
    if os.geteuid() != 0 and tls_root() == DEFAULT_TLS_ROOT:
        raise TlsError(
            "Creating the local CA requires root (the CA private key is "
            "root:root 0600). Re-run with sudo."
        )
    key, cert = generate_ca()
    tls_root().mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(key_file, private_key_pem(key), mode=0o600)
    atomic_write_bytes(cert_file, cert_pem(cert), mode=0o644)
    _chown(cert_file)
    _set_mode(cert_file, 0o644)
    # CA key is the one TLS file that stays root:root 0600 (owner ruling O1).
    if os.geteuid() == 0:
        try:
            os.chown(key_file, 0, 0)
        except OSError:
            pass
    _set_mode(key_file, 0o600)
    return key, cert


def _write_version(
    *,
    cert_chain_pem: bytes,
    key_pem: bytes,
    mode: Literal["generated", "imported"],
    source: str,
    cert: x509.Certificate,
    sans: list[str],
) -> Path:
    root = versions_dir()
    root.mkdir(parents=True, exist_ok=True)
    version = _new_version_id()
    temp = root / f".tmp-{uuid.uuid4().hex}"
    temp.mkdir(mode=0o750)
    try:
        atomic_write_bytes(temp / KEY_NAME, key_pem, mode=0o600)
        atomic_write_bytes(temp / CERT_NAME, cert_chain_pem, mode=0o644)
        write_meta(
            temp,
            VersionMeta(
                version=version,
                mode=mode,
                created_at=iso(utcnow()),
                not_before=iso(cert.not_valid_before_utc),
                not_after=iso(cert.not_valid_after_utc),
                sans=sans,
                fingerprint_sha256=cert_fingerprint(cert),
                source=source,
            ),
        )
        final = root / version
        os.replace(temp, final)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    _chown_tree(final)
    _set_mode(final, 0o750)
    return final


def _read_link_target() -> str | None:
    link = current_link()
    try:
        if link.is_symlink():
            return os.readlink(link)
    except OSError:
        return None
    return None


def _restore_link(target: str | None) -> None:
    link = current_link()
    if target is None:
        try:
            link.unlink()
        except OSError:
            pass
        return
    temp = link.parent / f".{link.name}.restore-{uuid.uuid4().hex}"
    try:
        os.symlink(target, temp)
        os.replace(temp, link)
    except OSError:
        try:
            temp.unlink()
        except OSError:
            pass


def _activate(
    directory: Path,
    *,
    mode: Literal["generated", "imported"],
    source: str,
    reload_service: bool,
) -> TlsState:
    version = directory.name
    old_state = read_state()
    old_target = _read_link_target()
    old_state_bytes: str | None = None
    try:
        old_state_bytes = state_path().read_text(encoding="utf-8")
    except OSError:
        old_state_bytes = None

    link = current_link()
    if link.exists() and not link.is_symlink():
        # A legacy real directory: preserve it as a version before replacing.
        legacy = versions_dir() / f"legacy-{uuid.uuid4().hex[:8]}"
        shutil.move(str(link), legacy)
        _chown_tree(legacy)

    temp_link = link.parent / f".{link.name}.tmp-{uuid.uuid4().hex}"
    try:
        os.symlink(f"{VERSIONS_NAME}/{version}", temp_link)
        os.replace(temp_link, link)
    except OSError as exc:
        try:
            temp_link.unlink()
        except OSError:
            pass
        raise TlsError(f"Cannot activate TLS version: {exc}") from exc

    ca_created = old_state.ca_created_at
    if ca_created is None and mode == "generated":
        try:
            ca_created = iso(load_cert_chain(ca_cert_path())[0].not_valid_before_utc)
        except TlsError, TlsCryptoError:
            ca_created = None
    state = TlsState(
        mode=mode,
        version=version,
        activated_at=iso(utcnow()),
        source=source,
        hsts=old_state.hsts,
        hsts_max_age=old_state.hsts_max_age,
        ca_created_at=ca_created,
    )
    write_state(state)
    _chown(link, follow_symlinks=False)
    _chown(state_path())

    if reload_service:
        ok, detail = reload_web()
        if not ok:
            _restore_link(old_target)
            if old_state_bytes is None:
                try:
                    state_path().unlink()
                except OSError:
                    pass
            else:
                _atomic_write_text(state_path(), old_state_bytes, mode=0o644)
                _chown(state_path())
            raise TlsError(
                "The new certificate was installed but scriptorium-web did not "
                f"reload; the previous certificate was restored ({detail})."
            )
    return state


def reload_web() -> tuple[bool, str]:
    """Gracefully reload a live web service; inactive services are a no-op."""
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return True, "systemctl unavailable (development host)"
    try:
        active = subprocess.run(
            [systemctl, "is-active", "--quiet", "scriptorium-web"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return True, f"service state unknown ({exc})"
    if active.returncode != 0:
        return True, "scriptorium-web is not running"
    try:
        reloaded = subprocess.run(
            [systemctl, "reload", "scriptorium-web"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if reloaded.returncode != 0:
        detail = (reloaded.stderr or reloaded.stdout or "reload failed").strip()
        return False, detail[:500]
    return True, "reloaded"


def _sans_text(sans: list[SubjectAltName]) -> list[str]:
    return [item.text for item in sans]


def _meta_sans(meta: VersionMeta) -> list[SubjectAltName]:
    return [parse_san(item) for item in meta.sans]


def _version_dirs() -> list[Path]:
    root = versions_dir()
    if not root.is_dir():
        return []
    return sorted(
        (
            entry
            for entry in root.iterdir()
            if entry.is_dir() and not entry.name.startswith(".")
        ),
        key=lambda entry: entry.name,
        reverse=True,
    )


def _current_version_name() -> str | None:
    directory = current_version_dir()
    return directory.name if directory is not None else None


def _validate_current(directory: Path) -> tuple[list[x509.Certificate], object]:
    certs = load_cert_chain(directory / CERT_NAME)
    key = load_private_key(directory / KEY_NAME)
    errors = validate_material(certs, key)
    if errors:
        raise TlsError("TLS material is invalid: " + "; ".join(errors))
    return certs, key


def generate(
    *,
    hostnames: list[str] | None = None,
    urls: list[str] | None = None,
    sans: list[str] | None = None,
    reload_service: bool = True,
) -> TlsStatus:
    ca_key, ca_cert = _ensure_ca()
    selected = detect_sans(hostnames, urls, sans)
    leaf_key, leaf_cert = generate_leaf(ca_key, ca_cert, selected)
    chain = cert_pem(leaf_cert) + cert_pem(ca_cert)
    directory = _write_version(
        cert_chain_pem=chain,
        key_pem=private_key_pem(leaf_key),
        mode="generated",
        source="generate",
        cert=leaf_cert,
        sans=_sans_text(selected),
    )
    _activate(
        directory, mode="generated", source="generate", reload_service=reload_service
    )
    prune(keep=KEEP_VERSIONS, reload_service=False)
    return status()


def renew(
    *,
    force: bool = False,
    reload_service: bool = True,
) -> RenewResult:
    state = read_state(strict=True)
    if state.mode == "imported":
        return RenewResult(False, "imported certificates are never auto-renewed")
    directory = current_version_dir()
    if directory is None:
        raise TlsError("No current TLS certificate is installed.")
    certs, _ = _validate_current(directory)
    days = cert_days_left(certs[0])
    if days > RENEW_AT_DAYS and not force:
        return RenewResult(
            False, f"{days} days remaining; renewal starts at {RENEW_AT_DAYS}"
        )
    ca_key, ca_cert = _ensure_ca()
    selected = sans_from_cert(certs[0])
    if not selected:
        raise TlsError("The current certificate has no SANs to renew.")
    leaf_key, leaf_cert = generate_leaf(ca_key, ca_cert, selected)
    chain = cert_pem(leaf_cert) + cert_pem(ca_cert)
    new_dir = _write_version(
        cert_chain_pem=chain,
        key_pem=private_key_pem(leaf_key),
        mode="generated",
        source="renew",
        cert=leaf_cert,
        sans=_sans_text(selected),
    )
    _activate(new_dir, mode="generated", source="renew", reload_service=reload_service)
    prune(keep=KEEP_VERSIONS, reload_service=False)
    return RenewResult(True, "renewed", status())


def import_pair(
    cert_file: Path,
    key_file: Path,
    *,
    reload_service: bool = True,
) -> ImportResult:
    certs = load_cert_chain(cert_file)
    key = load_private_key(key_file)
    errors = validate_material(certs, key)
    if errors:
        raise TlsError("Imported TLS material is invalid: " + "; ".join(errors))
    leaf = certs[0]
    selected = sans_from_cert(leaf)
    raw_chain = cert_file.read_bytes()
    raw_key = key_file.read_bytes()
    directory = _write_version(
        cert_chain_pem=raw_chain,
        key_pem=raw_key,
        mode="imported",
        source="import",
        cert=leaf,
        sans=_sans_text(selected),
    )
    _activate(
        directory, mode="imported", source="import", reload_service=reload_service
    )
    prune(keep=KEEP_VERSIONS, reload_service=False)
    return ImportResult(directory.name, status())


def rollback(
    *,
    version: str | None = None,
    reload_service: bool = True,
) -> TlsStatus:
    current = _current_version_name()
    candidates = _version_dirs()
    if not candidates:
        raise TlsError("No TLS versions are installed.")
    if version is not None:
        chosen = version_dir(version)
        if not chosen.is_dir():
            raise TlsError(f"TLS version {version!r} does not exist.")
    else:
        older = [item for item in candidates if item.name != current]
        if current is not None:
            current_index = next(
                (
                    index
                    for index, item in enumerate(candidates)
                    if item.name == current
                ),
                None,
            )
            older = (
                candidates[current_index + 1 :] if current_index is not None else older
            )
        if not older:
            raise TlsError("There is no older TLS version to roll back to.")
        chosen = older[0]
    meta = read_meta(chosen)
    _validate_current(chosen)
    _activate(
        chosen,
        mode=meta.mode,
        source="rollback",
        reload_service=reload_service,
    )
    return status()


def prune(*, keep: int = KEEP_VERSIONS, reload_service: bool = False) -> list[str]:
    if keep < 1:
        raise TlsError("The retention count must be at least 1.")
    del reload_service  # pruning never changes the active certificate
    current = _current_version_name()
    candidates = _version_dirs()
    protected: set[str] = set()
    if current is not None:
        protected.add(current)
    for item in candidates[:keep]:
        protected.add(item.name)
    removed: list[str] = []
    for item in candidates:
        if item.name in protected:
            continue
        shutil.rmtree(item, ignore_errors=True)
        removed.append(item.name)
    return removed


def history() -> list[dict[str, Any]]:
    current = _current_version_name()
    rows: list[dict[str, Any]] = []
    for directory in _version_dirs():
        try:
            meta = read_meta(directory)
        except TlsError:
            rows.append(
                {
                    "version": directory.name,
                    "current": directory.name == current,
                    "invalid": True,
                }
            )
            continue
        rows.append(
            {
                **meta.as_dict(),
                "current": directory.name == current,
            }
        )
    return rows


def status() -> TlsStatus:
    state = read_state()
    directory = current_version_dir()
    versions = len(_version_dirs())
    if directory is None:
        return TlsStatus(
            configured=False,
            mode=state.mode,
            version="",
            cert_path=str(cert_path()),
            key_path=str(key_path()),
            ca_cert_path=str(ca_cert_path()),
            subject="",
            issuer="",
            serial="",
            not_before="",
            not_after="",
            days_left=0,
            hsts=state.hsts,
            hsts_max_age=state.hsts_max_age,
            versions=versions,
            warnings=["No current TLS certificate is installed."],
        )
    warnings: list[str] = []
    try:
        certs, _ = _validate_current(directory)
    except (TlsError, TlsCryptoError) as exc:
        return TlsStatus(
            configured=False,
            mode=state.mode,
            version=directory.name,
            cert_path=str(cert_path()),
            key_path=str(key_path()),
            ca_cert_path=str(ca_cert_path()),
            subject="",
            issuer="",
            serial="",
            not_before="",
            not_after="",
            days_left=0,
            hsts=state.hsts,
            hsts_max_age=state.hsts_max_age,
            versions=versions,
            warnings=[str(exc)],
        )
    leaf = certs[0]
    days = cert_days_left(leaf)
    if days < RENEW_AT_DAYS:
        warnings.append(
            f"Certificate expires in {days} days; generated certificates renew "
            f"at {RENEW_AT_DAYS} days."
        )
    if state.version and state.version != directory.name:
        warnings.append(
            f"State file names version {state.version!r} but current points at "
            f"{directory.name!r}."
        )
    return TlsStatus(
        configured=True,
        mode=state.mode,
        version=directory.name,
        cert_path=str(cert_path()),
        key_path=str(key_path()),
        ca_cert_path=str(ca_cert_path()),
        subject=cert_subject(leaf),
        issuer=cert_issuer(leaf),
        serial=format(leaf.serial_number, "x"),
        not_before=iso(leaf.not_valid_before_utc),
        not_after=iso(leaf.not_valid_after_utc),
        days_left=days,
        sans=[item.text for item in sans_from_cert(leaf)],
        fingerprint_sha256=cert_fingerprint(leaf),
        hsts=state.hsts,
        hsts_max_age=state.hsts_max_age,
        versions=versions,
        warnings=warnings,
    )


def _permission_findings(
    path: Path, *, expected_mode: int | None, label: str
) -> list[TlsFinding]:
    findings: list[TlsFinding] = []
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
    except OSError as exc:
        findings.append(TlsFinding("error", f"{label} is missing: {exc}"))
        return findings
    if mode & 0o022:
        findings.append(
            TlsFinding("error", f"{label} is group/world writable ({mode:o}).")
        )
    if expected_mode is not None and mode != expected_mode:
        findings.append(
            TlsFinding(
                "warning", f"{label} mode is {mode:o}; expected {expected_mode:o}."
            )
        )
    return findings


def verify() -> list[TlsFinding]:
    findings: list[TlsFinding] = []
    root = tls_root()
    if not root.is_dir():
        findings.append(TlsFinding("error", f"TLS root is missing: {root}."))
        return findings
    state = read_state()
    directory = current_version_dir()
    if directory is None:
        findings.append(TlsFinding("error", "No current TLS certificate is installed."))
        return findings
    if state.version and state.version != directory.name:
        findings.append(
            TlsFinding(
                "error",
                f"State version {state.version!r} does not match current {directory.name!r}.",
            )
        )
    findings.extend(
        _permission_findings(
            directory / KEY_NAME, expected_mode=0o600, label="TLS private key"
        )
    )
    findings.extend(
        _permission_findings(
            directory / CERT_NAME, expected_mode=0o644, label="TLS fullchain"
        )
    )
    try:
        certs, _ = _validate_current(directory)
    except (TlsError, TlsCryptoError) as exc:
        findings.append(TlsFinding("error", str(exc)))
        return findings
    leaf = certs[0]
    days = cert_days_left(leaf)
    if days <= 0:
        findings.append(TlsFinding("error", "The current certificate has expired."))
    elif days < RENEW_AT_DAYS:
        findings.append(
            TlsFinding("warning", f"The current certificate expires in {days} days.")
        )
    if state.mode == "generated":
        if not ca_cert_path().is_file():
            findings.append(
                TlsFinding("error", "Generated mode has no CA certificate.")
            )
        if not ca_key_path().is_file():
            findings.append(
                TlsFinding("error", "Generated mode has no CA private key.")
            )
        if ca_key_path().is_file():
            if os.geteuid() == 0:
                st = ca_key_path().stat()
                if st.st_uid != 0 or st.st_gid != 0:
                    findings.append(
                        TlsFinding("error", "CA private key is not root:root.")
                    )
                if stat.S_IMODE(st.st_mode) != 0o600:
                    findings.append(
                        TlsFinding("error", "CA private key mode is not 0600.")
                    )
            try:
                ca_certs = load_cert_chain(ca_cert_path())
                ca_leaf = ca_certs[0]
                if not any(
                    cert_fingerprint(cert) == cert_fingerprint(ca_leaf)
                    for cert in certs[1:]
                ):
                    findings.append(
                        TlsFinding(
                            "warning",
                            "The current fullchain does not include the local CA certificate.",
                        )
                    )
                certs[-1].verify_directly_issued_by(ca_leaf)
            except (TlsError, TlsCryptoError, ValueError, TypeError) as exc:
                findings.append(
                    TlsFinding(
                        "error",
                        f"Generated chain does not verify to the local CA: {exc}",
                    )
                )
    elif state.mode == "imported":
        if not ca_key_path().exists():
            findings.append(
                TlsFinding(
                    "warning",
                    "Imported mode has no local CA private key (expected).",
                )
            )
    else:
        findings.append(TlsFinding("error", f"Unknown TLS mode {state.mode!r}."))
    if state.hsts and state.hsts_max_age <= 0:
        findings.append(
            TlsFinding("error", "HSTS is enabled with a non-positive max-age.")
        )
    return findings


def hsts(enabled: bool, *, max_age: int | None = None) -> TlsStatus:
    state = read_state()
    state.hsts = enabled
    state.hsts_max_age = max_age if max_age is not None else configured_hsts_max_age()
    if state.hsts_max_age <= 0:
        raise TlsError("HSTS max-age must be positive.")
    write_state(state)
    _chown(state_path())
    return status()


def ca_export_bytes() -> bytes:
    try:
        return ca_cert_path().read_bytes()
    except OSError as exc:
        raise TlsError(f"Cannot read the local CA certificate: {exc}") from exc


def normalize_redirect_host(value: str) -> str:
    try:
        return normalize_ip(value)
    except TlsCryptoError:
        return parse_san(value).value


def _host_port(host: str) -> tuple[str, int | None]:
    raw = host.strip()
    if raw.startswith("["):
        end = raw.find("]")
        if end == -1:
            return raw, None
        name = raw[1:end]
        rest = raw[end + 1 :]
        if rest.startswith(":") and rest[1:].isdigit():
            return name, int(rest[1:])
        return name, None
    if raw.count(":") == 1:
        name, port = raw.rsplit(":", 1)
        if port.isdigit():
            return name, int(port)
    return raw, None


def redirect_target(host_header: str) -> str | None:
    """Return a safe host for the HTTP→HTTPS redirect, or None.

    A Host header is attacker-controlled. The redirect only uses it when it
    matches the current certificate SANs; otherwise it falls back to the
    configured canonical host or the first non-wildcard DNS SAN.
    """
    configured = (get_setting("SC_TLS_REDIRECT_HOST", "") or "").strip()
    if configured:
        try:
            return normalize_redirect_host(configured)
        except TlsCryptoError:
            return None
    host, _ = _host_port(host_header)
    sans: list[SubjectAltName] = []
    directory = current_version_dir()
    if directory is not None:
        try:
            sans = sans_from_cert(load_cert_chain(directory / CERT_NAME)[0])
        except TlsError, TlsCryptoError:
            sans = []
    if host:
        try:
            candidate = normalize_redirect_host(host)
        except TlsCryptoError:
            candidate = ""
        if candidate and any(item.value == candidate for item in sans):
            return candidate
    for item in sans:
        if item.kind == "DNS" and not item.value.startswith("*."):
            return item.value
    for item in sans:
        if item.kind == "IP":
            return item.value
    return None


def socket_peer_host(request_host: str) -> str:
    """Test helper: the normalized host portion of a Host header."""
    host, _ = _host_port(request_host)
    try:
        return normalize_redirect_host(host)
    except TlsCryptoError:
        return ""


def utc_after(days: int) -> datetime:
    return datetime.now(UTC) + timedelta(days=days)


def path_owner(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    return stat_result.st_uid, stat_result.st_gid


def file_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def public_key_pem(cert: x509.Certificate) -> bytes:
    return cert.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _debug_socket_name() -> str:
    return f"{socket.gethostname()}:443"


# Re-exported for the CLI without importing implementation modules directly.
__all__ = [
    "CA_CERT_NAME",
    "CA_KEY_NAME",
    "CURRENT_NAME",
    "KEEP_VERSIONS",
    "RENEW_AT_DAYS",
    "ImportResult",
    "RenewResult",
    "TlsError",
    "TlsFinding",
    "TlsStatus",
    "ca_export_bytes",
    "cert_path",
    "generate",
    "history",
    "hsts",
    "import_pair",
    "key_path",
    "prune",
    "redirect_target",
    "renew",
    "rollback",
    "status",
    "verify",
]
