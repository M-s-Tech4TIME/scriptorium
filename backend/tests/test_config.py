"""Shared config loader regressions (decision 0040 Q-SM-M = M1)."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest

from app import config


@pytest.fixture(autouse=True)
def _restore_config() -> Generator[None]:
    config.set_config_file("/etc/scriptorium/config.env")
    yield
    config.set_config_file("/etc/scriptorium/config.env")


def test_file_values_and_quotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.env"
    path.write_text(
        "# comment\n\nDATABASE_URL='postgresql+asyncpg://u:p@h/db'\n"
        'SC_MEDIA_ROOT="/var/lib/scriptorium/media"\n',
        encoding="utf-8",
    )
    config.set_config_file(path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SC_MEDIA_ROOT", raising=False)
    assert config.get_setting("DATABASE_URL") == "postgresql+asyncpg://u:p@h/db"
    assert config.get_setting("SC_MEDIA_ROOT") == "/var/lib/scriptorium/media"


def test_environment_wins(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.env"
    path.write_text("SECRET_KEY=file-value\n", encoding="utf-8")
    config.set_config_file(path)
    monkeypatch.setenv("SECRET_KEY", "env-value")
    assert config.get_setting("SECRET_KEY") == "env-value"


def test_empty_environment_value_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.env"
    path.write_text("SECRET_KEY=file-value\n", encoding="utf-8")
    config.set_config_file(path)
    monkeypatch.setenv("SECRET_KEY", "")
    assert config.get_setting("SECRET_KEY") == ""
    with pytest.raises(config.ConfigError):
        config.require_setting("SECRET_KEY")


def test_malformed_file_fails_loud(tmp_path: Path) -> None:
    path = tmp_path / "config.env"
    path.write_text("NOT A SETTING\n", encoding="utf-8")
    config.set_config_file(path)
    with pytest.raises(config.ConfigError):
        config.load_config()


def test_cache_invalidates_on_file_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config.env"
    path.write_text("SC_BUILD_DISPATCH=inline\n", encoding="utf-8")
    config.set_config_file(path)
    monkeypatch.delenv("SC_BUILD_DISPATCH", raising=False)
    assert config.get_setting("SC_BUILD_DISPATCH") == "inline"
    path.write_text("SC_BUILD_DISPATCH=celery\n# size changes\n", encoding="utf-8")
    assert config.get_setting("SC_BUILD_DISPATCH") == "celery"


def test_missing_file_is_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SC_BUILD_DISPATCH", raising=False)
    config.set_config_file(tmp_path / "missing.env")
    assert config.load_config() == {}
    assert config.get_setting("SC_BUILD_DISPATCH", "inline") == "inline"


def test_typed_getters(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.env"
    path.write_text("SC_SPHINX_CPU_SECONDS=42\nSCRIPTORIUM_COOKIE_SECURE=on\n")
    config.set_config_file(path)
    monkeypatch.delenv("SC_SPHINX_CPU_SECONDS", raising=False)
    monkeypatch.delenv("SCRIPTORIUM_COOKIE_SECURE", raising=False)
    assert config.get_int_setting("SC_SPHINX_CPU_SECONDS", 1) == 42
    assert config.get_bool_setting("SCRIPTORIUM_COOKIE_SECURE") is True
    path.write_text("SC_SPHINX_CPU_SECONDS=not-an-int\n", encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.get_int_setting("SC_SPHINX_CPU_SECONDS", 1)


def test_default_config_path_is_absolute() -> None:
    assert os.path.isabs(config.CONFIG_FILE)
