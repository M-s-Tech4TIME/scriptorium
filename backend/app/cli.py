"""scriptorium-admin: setup + migrate. postinst never touches the DB (Q6/0001).

migrate refuses PG <18 (decision 0004) and runs idempotent Alembic upgrades.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import get_database_url

MIN_SERVER_VERSION_NUM = 180000


async def _server_version_num(url: str) -> int:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            value = await conn.scalar(text("SHOW server_version_num"))
        return int(str(value))
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


async def _setup(url: str) -> int:
    version = await _server_version_num(url)
    print(f"setup: database reachable (server_version_num={version}).")
    if version < MIN_SERVER_VERSION_NUM:
        print(
            "setup: WARNING — server is older than PG 18; migrate will refuse.",
            file=sys.stderr,
        )
    print("setup: next — run `scriptorium-admin migrate`, then enable services.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scriptorium-admin")
    parser.add_argument("--alembic-ini", default="/opt/scriptorium/backend/alembic.ini")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="Check DB reachability and print next steps.")
    sub.add_parser("migrate", help="Apply idempotent migrations (refuses PG<18).")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        url = get_database_url()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if args.cmd == "setup":
        return asyncio.run(_setup(url))
    return asyncio.run(_migrate(url, args.alembic_ini))


if __name__ == "__main__":
    raise SystemExit(main())
