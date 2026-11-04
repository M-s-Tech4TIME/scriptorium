"""scriptorium-admin — first-run, move, verify, and built-in TLS (0040).

Commands are intentionally small wrappers around the same application
modules the web/worker use, so a CLI move cannot diverge from the API's
validated backup core. ``postinst`` still never touches the database
(Q6/0001): migrations, first-account creation, restores, and TLS are
explicit operator actions.

Security: the CLI refuses to run as an arbitrary local account. Only root
or the ``scriptorium`` service user may operate it (F-I1); the config file
and all Scriptorium-managed state are owned by ``scriptorium:scriptorium``.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import pwd
import re
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import hash_password
from app.backup.export import archive_name, export_archive_sync
from app.backup.manifest import BackupError, backup_root
from app.backup.restore import RestoreResult, restore_archive_sync
from app.config import (
    ConfigError,
    config_file,
    get_setting,
    set_config_file,
)
from app.db import get_database_url
from app.media import get_media_root
from app.models import Athenaeum, Build, MediaAsset, PublicName, User
from app.serving.manifest import read_artifact_manifest
from app.sphinx.runner import build_config
from app.tls import (
    TlsError,
    TlsStatus,
    ca_export_bytes,
    generate,
    history,
    hsts,
    import_pair,
    prune,
    renew,
    rollback,
    status,
    verify,
)
from app.tls.crypto import cert_fingerprint, load_cert_chain
from app.tls.manager import reload_web
from app.tls.state import ca_cert_path, read_state

MIN_SERVER_VERSION_NUM = 180000
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class CliError(RuntimeError):
    """An operator action cannot proceed; the message is user-facing."""


def _operator_ids() -> set[int]:
    ids = {0}
    try:
        ids.add(pwd.getpwnam("scriptorium").pw_uid)
    except KeyError:
        pass
    return ids


def _require_operator() -> None:
    if os.geteuid() not in _operator_ids():
        raise CliError(
            "This command must run as root (sudo) or as the scriptorium "
            "service user; the configuration and state are not world-readable."
        )


def _redact_url(url: str) -> str:
    try:
        from urllib.parse import urlsplit

        parts = urlsplit(url)
    except ValueError:
        return "<unparseable DATABASE_URL>"
    host = parts.hostname or "?"
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}{parts.path}"


async def _server_version_num(url: str) -> int:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            value = await conn.scalar(text("SHOW server_version_num"))
        return int(str(value))
    finally:
        await engine.dispose()


def _alembic_head(alembic_ini: str) -> str | None:
    cfg = Config(alembic_ini)
    script = ScriptDirectory.from_config(cfg)
    return script.get_current_head()


async def _alembic_current(url: str) -> str | None:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            try:
                value = await conn.scalar(
                    text("SELECT version_num FROM alembic_version")
                )
            except SQLAlchemyError:
                return None
        return str(value) if value is not None else None
    finally:
        await engine.dispose()


async def _migrate(url: str, alembic_ini: str) -> int:
    version = await _server_version_num(url)
    if version < MIN_SERVER_VERSION_NUM:
        print(
            f"REFUSED: PostgreSQL server is version_num={version}; "
            f"Scriptorium requires PG 18+ (num>={MIN_SERVER_VERSION_NUM}). "
            "Install via PGDG; see docs/operations/install.md.",
            file=sys.stderr,
        )
        return 2
    cfg = Config(alembic_ini)
    cfg.set_main_option("sqlalchemy.url", url)
    from alembic import command

    await asyncio.to_thread(command.upgrade, cfg, "head")
    print("migrate: database at head.")
    return 0


def _root_status(label: str, path: Path, *, writable: bool) -> tuple[bool, str]:
    if not path.exists():
        return False, f"{label} is missing: {path}"
    if writable and not os.access(path, os.W_OK):
        return False, f"{label} is not writable by this account: {path}"
    return True, f"{label}: {path}"


async def _setup(url: str | None, alembic_ini: str) -> int:
    """Read-only first-run preflight (Q-SM-E = E1); never mutates state."""
    errors: list[str] = []
    warnings: list[str] = []

    cfg = config_file()
    if cfg.is_file():
        print(f"setup: config file present: {cfg}")
    else:
        errors.append(f"config file is missing: {cfg}")

    if get_setting("SECRET_KEY"):
        print("setup: SECRET_KEY is set.")
    else:
        errors.append("SECRET_KEY is not set in the environment or config file.")

    if url is None:
        errors.append(
            "DATABASE_URL is not set (environment or /etc/scriptorium/config.env)."
        )
    else:
        print(f"setup: database target: {_redact_url(url)}")
        try:
            version = await _server_version_num(url)
        except (SQLAlchemyError, OSError, ValueError) as exc:
            errors.append(f"database is not reachable: {exc}")
        else:
            print(f"setup: database reachable (server_version_num={version}).")
            if version < MIN_SERVER_VERSION_NUM:
                errors.append(
                    f"PostgreSQL {version} is older than 18 "
                    f"({MIN_SERVER_VERSION_NUM}); migrate will refuse."
                )
            try:
                head = _alembic_head(alembic_ini)
            except (CommandError, OSError, ValueError) as exc:
                warnings.append(f"cannot read Alembic head from {alembic_ini}: {exc}")
            else:
                current = await _alembic_current(url)
                if head is None:
                    warnings.append("Alembic has no head revision.")
                elif current == head:
                    print(f"setup: database at Alembic head ({head}).")
                else:
                    warnings.append(
                        f"database revision {current or '<none>'} is behind head "
                        f"{head}; run `scriptorium-admin migrate`."
                    )

    artifact_root = Path(
        get_setting("SC_ARTIFACT_ROOT", "/var/lib/scriptorium/artifacts") or ""
    )
    media_root = Path(get_setting("SC_MEDIA_ROOT", "/var/lib/scriptorium/media") or "")
    build_root = Path(get_setting("SC_BUILD_ROOT", "/var/lib/scriptorium/builds") or "")
    for label, path in (
        ("artifact root", artifact_root),
        ("media root", media_root),
        ("build root", build_root),
        ("backup root", backup_root()),
    ):
        ok, message = _root_status(label, path, writable=True)
        print(f"setup: {message}")
        if not ok:
            errors.append(message)

    build_python = Path(
        get_setting("SC_BUILD_PYTHON", "/opt/scriptorium/build-venv/bin/python") or ""
    )
    if build_python.is_file() and os.access(build_python, os.X_OK):
        print(f"setup: build python: {build_python}")
    else:
        errors.append(f"build python is missing or not executable: {build_python}")

    tls = status()
    if tls.configured:
        print(
            f"setup: TLS configured ({tls.mode}, {tls.days_left} days left, "
            f"{len(tls.sans)} SANs)."
        )
        warnings.extend(tls.warnings)
    else:
        errors.append(
            "TLS is not configured; run `scriptorium-admin tls generate` "
            "before enabling the web service."
        )

    for warning in warnings:
        print(f"setup: WARNING — {warning}", file=sys.stderr)
    if errors:
        for error in errors:
            print(f"setup: ERROR — {error}", file=sys.stderr)
        print("setup: not ready.", file=sys.stderr)
        return 2
    print("setup: ready.")
    print(
        "setup: next — run `scriptorium-admin migrate`, "
        "`scriptorium-admin user create`, then enable services."
    )
    return 0


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if not _EMAIL_RE.fullmatch(email) or len(email) > 320:
        raise CliError(f"Invalid email address: {value!r}.")
    return email


def _validate_password(password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise CliError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise CliError(f"Password must be at most {MAX_PASSWORD_LENGTH} characters.")
    if not password.strip():
        raise CliError("Password may not be blank.")
    return password


def _read_password(password_stdin: bool) -> str:
    if password_stdin:
        line = sys.stdin.readline()
        if not line:
            raise CliError("--password-stdin was set but stdin was empty.")
        return _validate_password(line.rstrip("\n"))
    if not sys.stdin.isatty():
        raise CliError(
            "No TTY for a password prompt; pass --password-stdin for automation."
        )
    first = getpass.getpass("Password: ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        raise CliError("Passwords do not match.")
    return _validate_password(first)


async def _user_create(email: str, display: str, password: str) -> uuid.UUID:
    normalized = _normalize_email(email)
    display = display.strip()
    if not display or len(display) > 120:
        raise CliError("Display name must be 1–120 characters.")
    _validate_password(password)
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            existing = await session.scalar(
                select(User.id).where(User.email == normalized)
            )
            if existing is not None:
                raise CliError(f"A user with email {normalized} already exists.")
            user = User(
                email=normalized,
                pw_hash=hash_password(password),
                display=display,
            )
            session.add(user)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise CliError(
                    f"A user with email {normalized} already exists."
                ) from exc
            return user.id
    finally:
        await engine.dispose()


async def _user_list() -> list[tuple[str, str, str]]:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            rows = list(
                (await session.execute(select(User).order_by(User.email))).scalars()
            )
            return [(str(user.id), user.email, user.display) for user in rows]
    finally:
        await engine.dispose()


async def _resolve_athenaeum(session: AsyncSession, reference: str) -> Athenaeum:
    try:
        athenaeum_id = uuid.UUID(reference)
    except ValueError:
        athenaeum_id = None
    row: Athenaeum | None
    if athenaeum_id is not None:
        row = await session.get(Athenaeum, athenaeum_id)
    else:
        row = await session.scalar(
            select(Athenaeum).where(Athenaeum.public_slug == reference)
        )
    if row is None:
        raise CliError(
            f"No Athenaeum matches {reference!r} (use its UUID or current public name)."
        )
    return row


async def _backup_export(
    reference: str, mode: str, container: str, destination: Path
) -> tuple[Path, int, str]:
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            athenaeum = await _resolve_athenaeum(session, reference)
            athenaeum_id = athenaeum.id
            public_slug = athenaeum.public_slug
    finally:
        await engine.dispose()
    if destination.is_dir():
        destination = destination / archive_name(public_slug, mode, container)
    result = await asyncio.to_thread(
        export_archive_sync,
        str(athenaeum_id),
        mode,
        container,
        str(destination),
    )
    return result.path, result.size_bytes, result.sha256


async def _restore(archive: Path, owner_email: str, *, force: bool) -> RestoreResult:
    if not archive.is_file():
        raise CliError(f"Archive does not exist: {archive}")
    normalized = _normalize_email(owner_email)
    engine = create_async_engine(get_database_url(), pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            owner = await session.scalar(select(User).where(User.email == normalized))
            if owner is None:
                raise CliError(f"No user with email {normalized}; create it first.")
            owner_id = owner.id
            count = await session.scalar(select(func.count()).select_from(Athenaeum))
            if (count or 0) > 0 and not force:
                raise CliError(
                    "The target database already contains Athenaeums; "
                    "pass --force to restore additively."
                )
    finally:
        await engine.dispose()

    root = backup_root() / "tmp"
    root.mkdir(parents=True, exist_ok=True)
    workdir = Path(tempfile.mkdtemp(prefix="scriptorium-restore-", dir=root))
    try:
        return await asyncio.to_thread(
            restore_archive_sync,
            str(archive),
            str(owner_id),
            str(workdir),
            strict_names=True,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@dataclass
class VerifyReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: int = 0

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.errors.append(message)

    def warn(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.warnings.append(message)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def _verify_database(url: str, alembic_ini: str) -> VerifyReport:
    report = VerifyReport()
    try:
        version = await _server_version_num(url)
    except (SQLAlchemyError, OSError, ValueError) as exc:
        report.errors.append(f"database is not reachable: {exc}")
        return report
    report.check(
        version >= MIN_SERVER_VERSION_NUM,
        f"PostgreSQL version_num={version} is below 18.",
    )
    try:
        head = _alembic_head(alembic_ini)
    except (CommandError, OSError, ValueError) as exc:
        report.errors.append(f"cannot read Alembic head: {exc}")
        head = None
    current = await _alembic_current(url)
    report.check(
        head is not None and current == head,
        f"database revision {current or '<none>'} is not Alembic head {head}.",
    )

    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with maker() as session:
            athenaeums = (await session.execute(select(Athenaeum))).scalars().all()
            for athenaeum in athenaeums:
                prefix = f"Athenaeum {athenaeum.public_slug} ({athenaeum.id})"
                name_row = await session.get(PublicName, athenaeum.public_slug)
                report.check(
                    name_row is not None
                    and name_row.athenaeum_id == athenaeum.id
                    and name_row.is_current,
                    f"{prefix}: current public name row is missing or mismatched.",
                )
                for label, build_id in (
                    ("latest", athenaeum.latest_build_id),
                    ("stable", athenaeum.stable_build_id),
                ):
                    if build_id is None:
                        continue
                    build = await session.get(Build, build_id)
                    report.check(
                        build is not None and build.athenaeum_id == athenaeum.id,
                        f"{prefix}: {label} build pointer is invalid.",
                    )
                builds = (
                    await session.execute(
                        select(Build).where(Build.athenaeum_id == athenaeum.id)
                    )
                ).scalars()
                for build in builds:
                    if build.artifact_path is None:
                        continue
                    artifact = Path(build.artifact_path)
                    report.check(
                        artifact.is_dir(),
                        f"{prefix}: build #{build.build_number} artifact is missing.",
                    )
                    if not artifact.is_dir():
                        continue
                    try:
                        artifact.resolve().relative_to(
                            build_config().artifact_root.resolve()
                        )
                    except ValueError:
                        report.errors.append(
                            f"{prefix}: build #{build.build_number} artifact "
                            "escapes the artifact root."
                        )
                        continue
                    manifest = read_artifact_manifest(artifact)
                    report.check(
                        manifest is not None,
                        f"{prefix}: build #{build.build_number} manifest is invalid.",
                    )
                    if manifest is not None:
                        report.check(
                            manifest.get("build_number") == build.build_number,
                            f"{prefix}: build #{build.build_number} manifest number "
                            "does not match.",
                        )
            media = (await session.execute(select(MediaAsset))).scalars().all()
            for asset in media:
                path = get_media_root() / asset.storage_path
                report.check(
                    path.is_file(),
                    f"Media {asset.id}: file is missing ({path}).",
                )
                if path.is_file():
                    report.check(
                        path.stat().st_size == asset.size_bytes,
                        f"Media {asset.id}: size does not match the row.",
                    )
                    report.check(
                        _sha256_file(path) == asset.sha256,
                        f"Media {asset.id}: SHA-256 does not match the row.",
                    )
    finally:
        await engine.dispose()
    return report


async def _verify_all(url: str | None, alembic_ini: str) -> VerifyReport:
    report = VerifyReport()
    report.check(config_file().is_file(), f"config file is missing: {config_file()}.")
    report.check(bool(get_setting("SECRET_KEY")), "SECRET_KEY is not set.")
    if url is None:
        report.errors.append("DATABASE_URL is not set.")
        return report
    db_report = await _verify_database(url, alembic_ini)
    report.errors.extend(db_report.errors)
    report.warnings.extend(db_report.warnings)
    report.checks += db_report.checks

    tls = status()
    report.check(tls.configured, "TLS is not configured.")
    if tls.configured:
        report.check(not tls.warnings, "TLS has warnings: " + "; ".join(tls.warnings))
    findings = verify()
    for finding in findings:
        if finding.level == "error":
            report.errors.append(f"TLS: {finding.message}")
        else:
            report.warnings.append(f"TLS: {finding.message}")
        report.checks += 1
    return report


def _print_status(value: TlsStatus) -> None:
    print(json.dumps(value.as_dict(), indent=2, sort_keys=True))


def _tls_status(args: argparse.Namespace) -> int:
    value = status()
    if args.json:
        _print_status(value)
    else:
        print(f"configured: {'yes' if value.configured else 'no'}")
        print(f"mode: {value.mode}")
        print(f"version: {value.version or '-'}")
        print(f"certificate: {value.cert_path}")
        print(f"private key: {value.key_path}")
        print(f"CA certificate: {value.ca_cert_path}")
        if value.configured:
            print(f"subject: {value.subject}")
            print(f"issuer: {value.issuer}")
            print(f"valid: {value.not_before} → {value.not_after}")
            print(f"days left: {value.days_left}")
            print(f"SHA-256: {value.fingerprint_sha256}")
            print(f"SANs: {', '.join(value.sans)}")
        print(f"HSTS: {'on' if value.hsts else 'off'} (max-age {value.hsts_max_age})")
        print(f"retained versions: {value.versions}")
        for warning in value.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0


def _tls_generate(args: argparse.Namespace) -> int:
    value = generate(
        hostnames=args.hostname,
        urls=args.url,
        sans=args.san,
        reload_service=not args.no_reload,
    )
    _print_status(value)
    return 0


def _tls_renew(args: argparse.Namespace) -> int:
    result = renew(force=args.force, reload_service=not args.no_reload)
    print(result.reason)
    if result.status is not None:
        _print_status(result.status)
    return 0


def _tls_import(args: argparse.Namespace) -> int:
    result = import_pair(
        Path(args.cert),
        Path(args.key),
        reload_service=not args.no_reload,
    )
    print(f"imported TLS version {result.version}")
    _print_status(result.status)
    return 0


def _tls_rollback(args: argparse.Namespace) -> int:
    value = rollback(version=args.version, reload_service=not args.no_reload)
    _print_status(value)
    return 0


def _tls_prune(args: argparse.Namespace) -> int:
    removed = prune(keep=args.keep)
    if removed:
        print("removed: " + ", ".join(removed))
    else:
        print("nothing to prune")
    return 0


def _tls_history(args: argparse.Namespace) -> int:
    rows = history()
    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
    else:
        for row in rows:
            marker = "*" if row.get("current") else " "
            print(
                f"{marker} {row.get('version', '-')}  "
                f"{row.get('mode', '-')}  {row.get('not_after', '-')}"
            )
    return 0


def _tls_verify(args: argparse.Namespace) -> int:
    findings = verify()
    if args.json:
        print(
            json.dumps(
                [finding.as_dict() for finding in findings],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        for finding in findings:
            print(f"{finding.level.upper()}: {finding.message}")
        if not findings:
            print("TLS verify: no findings.")
    return 1 if any(finding.level == "error" for finding in findings) else 0


def _tls_hsts(args: argparse.Namespace) -> int:
    before = read_state()
    value = hsts(args.state == "on", max_age=args.max_age)
    ok, detail = reload_web()
    if not ok:
        hsts(before.hsts, max_age=before.hsts_max_age)
        raise CliError(
            f"scriptorium-web did not reload; HSTS was not changed ({detail})."
        )
    print(
        f"HSTS {'enabled' if value.hsts else 'disabled'} (max-age {value.hsts_max_age})."
    )
    if detail != "reloaded":
        print(f"note: {detail}")
    return 0


def _tls_ca(args: argparse.Namespace) -> int:
    cert_file = ca_cert_path()
    if not cert_file.is_file():
        raise CliError(
            "No local CA certificate exists; run `scriptorium-admin tls generate` "
            "or import an external certificate."
        )
    if args.export:
        destination = Path(args.export)
        if destination.is_dir():
            destination = destination / "scriptorium-ca.pem"
        destination.write_bytes(ca_export_bytes())
        os.chmod(destination, 0o644)
        print(f"exported: {destination}")
    cert = load_cert_chain(cert_file)[0]
    print(f"CA certificate: {cert_file}")
    print(f"SHA-256: {cert_fingerprint(cert)}")
    print(
        "Trust this CA once on client devices; the leaf renews automatically "
        "without changing the trust anchor."
    )
    return 0


def _tls_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Install without reloading scriptorium-web (offline/testing).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scriptorium-admin")
    parser.add_argument(
        "--config", help="Config file (default /etc/scriptorium/config.env)."
    )
    parser.add_argument("--alembic-ini", default="/opt/scriptorium/backend/alembic.ini")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("setup", help="Read-only first-run preflight.")
    sub.add_parser("migrate", help="Apply idempotent migrations (refuses PG<18).")
    sub.add_parser("verify", help="Read-only post-move/health verification.")

    user = sub.add_parser("user", help="First-run user management.")
    user_sub = user.add_subparsers(dest="user_cmd", required=True)
    user_create = user_sub.add_parser(
        "create", help="Create one user (no open registration)."
    )
    user_create.add_argument("--email", required=True)
    user_create.add_argument("--display", required=True)
    user_create.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from one stdin line (automation).",
    )
    user_sub.add_parser("list", help="List users (id, email, display).")

    backup = sub.add_parser("backup", help="Headless export using the 0039 core.")
    backup_sub = backup.add_subparsers(dest="backup_cmd", required=True)
    backup_export = backup_sub.add_parser("export", help="Export one Athenaeum.")
    backup_export.add_argument(
        "--athenaeum", required=True, help="Athenaeum UUID or current public name."
    )
    backup_export.add_argument(
        "--mode", choices=("editorial", "full"), default="editorial"
    )
    backup_export.add_argument("--format", choices=("zip", "tar.gz"), default="zip")
    backup_export.add_argument(
        "--output", required=True, help="Archive path or destination directory."
    )

    restore = sub.add_parser("restore", help="Strict-name restore using the 0039 core.")
    restore.add_argument("--archive", required=True)
    restore.add_argument("--owner-email", required=True)
    restore.add_argument(
        "--force",
        action="store_true",
        help="Allow restoring into a database that already has Athenaeums.",
    )

    tls = sub.add_parser("tls", help="Built-in TLS lifecycle.")
    tls_sub = tls.add_subparsers(dest="tls_cmd", required=True)

    tls_generate = tls_sub.add_parser(
        "generate", help="Generate CA + leaf and activate."
    )
    tls_generate.add_argument("--hostname", action="append", default=[])
    tls_generate.add_argument("--url", action="append", default=[])
    tls_generate.add_argument("--san", action="append", default=[])
    _tls_common(tls_generate)

    tls_renew = tls_sub.add_parser("renew", help="Renew a generated certificate.")
    tls_renew.add_argument("--force", action="store_true")
    _tls_common(tls_renew)

    tls_import = tls_sub.add_parser(
        "import", help="Import fullchain.pem + privkey.pem."
    )
    tls_import.add_argument("--cert", required=True)
    tls_import.add_argument("--key", required=True)
    _tls_common(tls_import)

    tls_rollback = tls_sub.add_parser("rollback", help="Reactivate an older version.")
    tls_rollback.add_argument("version", nargs="?")
    _tls_common(tls_rollback)

    tls_prune = tls_sub.add_parser("prune", help="Delete old retained versions.")
    tls_prune.add_argument("--keep", type=int, default=5)

    tls_history = tls_sub.add_parser("history", help="List retained versions.")
    tls_history.add_argument("--json", action="store_true")

    tls_status = tls_sub.add_parser("status", help="Show the active certificate.")
    tls_status.add_argument("--json", action="store_true")

    tls_verify = tls_sub.add_parser("verify", help="Validate the active material.")
    tls_verify.add_argument("--json", action="store_true")

    tls_hsts = tls_sub.add_parser("hsts", help="Enable/disable HSTS.")
    tls_hsts.add_argument("state", choices=("on", "off"))
    tls_hsts.add_argument("--max-age", type=int, default=None)

    tls_ca = tls_sub.add_parser("ca", help="Show/export the local CA certificate.")
    tls_ca.add_argument("--export", help="Write the CA PEM to this path.")

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    if args.cmd == "setup":
        try:
            url = get_database_url()
        except RuntimeError:
            url = None
        return asyncio.run(_setup(url, args.alembic_ini))
    if args.cmd == "migrate":
        return asyncio.run(_migrate(get_database_url(), args.alembic_ini))
    if args.cmd == "verify":
        try:
            url = get_database_url()
        except RuntimeError:
            url = None
        report = asyncio.run(_verify_all(url, args.alembic_ini))
        for warning in report.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        for error in report.errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if report.errors:
            print(
                f"verify: {len(report.errors)} error(s), "
                f"{len(report.warnings)} warning(s), {report.checks} checks."
            )
            return 1
        print(
            f"verify: ok ({report.checks} checks, {len(report.warnings)} warning(s))."
        )
        return 0
    if args.cmd == "user":
        if args.user_cmd == "create":
            password = _read_password(args.password_stdin)
            created_id = asyncio.run(_user_create(args.email, args.display, password))
            print(f"created user {created_id} {_normalize_email(args.email)}")
            return 0
        rows = asyncio.run(_user_list())
        for user_id, email, display in rows:
            print(f"{user_id}\t{email}\t{display}")
        return 0
    if args.cmd == "backup":
        path, size, digest = asyncio.run(
            _backup_export(
                args.athenaeum,
                args.mode,
                args.format,
                Path(args.output),
            )
        )
        print(f"exported: {path}")
        print(f"bytes: {size}")
        print(f"sha256: {digest}")
        return 0
    if args.cmd == "restore":
        result = asyncio.run(
            _restore(Path(args.archive), args.owner_email, force=args.force)
        )
        print(f"restored: {result.athenaeum_id}")
        print(f"title: {result.title}")
        print(f"public name: {result.public_slug}")
        print(f"mode: {result.mode}")
        for warning in result.warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
        return 0
    if args.cmd == "tls":
        if args.tls_cmd == "generate":
            return _tls_generate(args)
        if args.tls_cmd == "renew":
            return _tls_renew(args)
        if args.tls_cmd == "import":
            return _tls_import(args)
        if args.tls_cmd == "rollback":
            return _tls_rollback(args)
        if args.tls_cmd == "prune":
            return _tls_prune(args)
        if args.tls_cmd == "history":
            return _tls_history(args)
        if args.tls_cmd == "status":
            return _tls_status(args)
        if args.tls_cmd == "verify":
            return _tls_verify(args)
        if args.tls_cmd == "hsts":
            return _tls_hsts(args)
        if args.tls_cmd == "ca":
            return _tls_ca(args)
    raise CliError(f"Unknown command: {args.cmd}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _require_operator()
        if args.config:
            set_config_file(args.config)
        return _dispatch(args)
    except (CliError, ConfigError, TlsError, BackupError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
