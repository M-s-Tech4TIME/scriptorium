"""CLI parser, validation, and live first-run/move regressions (decision 0040)."""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app import cli
from app.backup.manifest import BackupError
from app.models import Athenaeum, User
from tests.conftest import LIVE_DB_URL, app_teardown, needs_db
from tests.test_document_api import _client, _headers, _mk_lib, _run, _seed_users


def test_parser_covers_first_run_and_tls() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(
        ["user", "create", "--email", "a@b.test", "--display", "A"]
    )
    assert args.cmd == "user" and args.user_cmd == "create"
    assert args.email == "a@b.test"
    args = parser.parse_args(
        [
            "tls",
            "generate",
            "--hostname",
            "docs.example.test",
            "--san",
            "IP:192.0.2.5",
            "--no-reload",
        ]
    )
    assert args.cmd == "tls" and args.tls_cmd == "generate"
    assert args.hostname == ["docs.example.test"]
    assert args.san == ["IP:192.0.2.5"]
    assert args.no_reload is True
    args = parser.parse_args(
        ["backup", "export", "--athenaeum", "docs", "--output", "/tmp/x.zip"]
    )
    assert args.mode == "editorial" and args.format == "zip"
    args = parser.parse_args(
        ["restore", "--archive", "/tmp/x.zip", "--owner-email", "a@b.test"]
    )
    assert args.force is False


def test_password_policy() -> None:
    assert cli._validate_password("123456789012") == "123456789012"
    with pytest.raises(cli.CliError, match="at least"):
        cli._validate_password("short")
    with pytest.raises(cli.CliError, match="blank"):
        cli._validate_password("            ")


def test_email_normalization_and_redaction() -> None:
    assert cli._normalize_email(" Owner@Example.TEST ") == "owner@example.test"
    with pytest.raises(cli.CliError):
        cli._normalize_email("not-an-email")
    redacted = cli._redact_url("postgresql+asyncpg://u:secret@db:5432/scriptorium")
    assert "secret" not in redacted
    assert redacted.endswith("/scriptorium")


def test_operator_ids_include_root() -> None:
    assert 0 in cli._operator_ids()


@needs_db
def test_cli_user_create_and_list() -> None:
    email = f"cli-{uuid.uuid4().hex}@example.test"

    async def run() -> None:
        user_id = await cli._user_create(email, "CLI User", "a-long-enough-password")
        rows = await cli._user_list()
        assert any(row[0] == str(user_id) and row[1] == email for row in rows)
        engine = create_async_engine(LIVE_DB_URL)
        try:
            maker = async_sessionmaker(engine, class_=AsyncSession)
            async with maker() as session:
                await session.execute(delete(User).where(User.id == user_id))
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(run())


def _set_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for key, value in {
        "SC_ARTIFACT_ROOT": str(tmp_path / "artifacts"),
        "SC_BUILD_ROOT": str(tmp_path / "builds"),
        "SC_MEDIA_ROOT": str(tmp_path / "media"),
        "SC_BACKUP_ROOT": str(tmp_path / "backups"),
        "SC_BUILD_DISPATCH": "inline",
        "SC_BACKUP_DISPATCH": "inline",
    }.items():
        monkeypatch.setenv(key, value)


@needs_db
def test_cli_export_and_strict_restore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    users = asyncio.run(_seed_users(1))
    me = users[0]

    async def run() -> None:
        _set_paths(monkeypatch, tmp_path)
        async with _client() as client:
            aid = await _mk_lib(client, me, "climove")
            shown = await client.get(f"/api/v1/athenaeums/{aid}", headers=_headers(me))
            public_slug = str(shown.json()["public_slug"])
            archive = tmp_path / "move.zip"
            path, size, digest = await cli._backup_export(
                public_slug, "editorial", "zip", archive
            )
            assert path == archive
            assert size > 0 and len(digest) == 64

            with pytest.raises(cli.CliError, match="already contains"):
                await cli._restore(archive, str(me["email"]), force=False)

            deleted = await client.delete(
                f"/api/v1/athenaeums/{aid}", headers=_headers(me)
            )
            assert deleted.status_code == 204

            restored = await cli._restore(archive, str(me["email"]), force=True)
            assert restored.public_slug == public_slug
            assert restored.warnings == []

            async def inspect(session: AsyncSession) -> None:
                row = await session.get(Athenaeum, restored.athenaeum_id)
                assert row is not None
                assert row.public_slug == public_slug
                assert row.owner_id == uuid.UUID(str(me["id"]))

            engine = create_async_engine(LIVE_DB_URL)
            try:
                maker = async_sessionmaker(engine, class_=AsyncSession)
                async with maker() as session:
                    await inspect(session)
            finally:
                await engine.dispose()

        await app_teardown()

    _run(run())


@needs_db
def test_cli_strict_restore_refuses_foreign_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    users = asyncio.run(_seed_users(2))
    owner, other = users

    async def run() -> None:
        _set_paths(monkeypatch, tmp_path)
        async with _client() as client:
            aid = await _mk_lib(client, owner, "cliforeign")
            shown = await client.get(
                f"/api/v1/athenaeums/{aid}", headers=_headers(owner)
            )
            public_slug = str(shown.json()["public_slug"])
            archive = tmp_path / "foreign.zip"
            await cli._backup_export(public_slug, "editorial", "zip", archive)

            # The source site still owns the live name; strict move must fail.
            with pytest.raises(BackupError, match="conflicts"):
                await cli._restore(archive, str(other["email"]), force=True)

        await app_teardown()

    _run(run())
