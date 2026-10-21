"""Worker unit tests (M4-C3) — offline (no PG): celery wiring + sandbox guards."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from app.sphinx.runner import (
    SANDBOX_ENV_KEYS,
    RunnerConfigError,
    build_config,
    child_env,
)


def test_celery_broker_wiring() -> None:
    import os

    from app.worker.celery_app import build_app, reset_app

    reset_app()
    os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/2"
    try:
        instance = build_app()
        assert instance.main == "scriptorium"
        assert instance.conf.task_default_queue == "scriptorium"
    finally:
        os.environ.pop("CELERY_BROKER_URL", None)
        reset_app()


def test_celery_broker_fail_loud_without_url() -> None:
    import os

    from app.worker.celery_app import build_app, reset_app

    reset_app()
    os.environ.pop("CELERY_BROKER_URL", None)
    try:
        with pytest.raises(RuntimeError, match="CELERY_BROKER_URL is not set"):
            build_app()
    finally:
        reset_app()


def test_build_config_fhs_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SC_ARTIFACT_ROOT",
        "SC_BUILD_ROOT",
        "SC_BUILD_PYTHON",
        "SC_SPHINX_CPU_SECONDS",
        "SC_SPHINX_MEMORY_BYTES",
        "SC_SPHINX_MAX_FILE_BYTES",
        "SC_SPHINX_TIMEOUT_S",
    ):
        monkeypatch.delenv(name, raising=False)
    cfg = build_config()
    assert cfg.artifact_root == Path("/var/lib/scriptorium/artifacts")
    assert cfg.build_root == Path("/var/lib/scriptorium/builds")
    assert cfg.build_python == Path(sys.executable)  # dev/CI micro-default
    assert cfg.cpu_seconds == 600
    assert cfg.memory_bytes == 1_610_612_736


def test_env_int_fail_loud(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SC_SPHINX_CPU_SECONDS", "abc")
    with pytest.raises(RunnerConfigError, match="SC_SPHINX_CPU_SECONDS"):
        build_config()


def test_dispatch_mode_whitelist(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.routers import builds as builds_router

    monkeypatch.delenv("SC_BUILD_DISPATCH", raising=False)
    assert builds_router.dispatch_mode() == "celery"  # production default
    monkeypatch.setenv("SC_BUILD_DISPATCH", "inline")
    assert builds_router.dispatch_mode() == "inline"
    monkeypatch.setenv("SC_BUILD_DISPATCH", "warp")
    with pytest.raises(RuntimeError, match="SC_BUILD_DISPATCH"):
        builds_router.dispatch_mode()


def test_build_router_registered() -> None:
    from app.main import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/athenaeums/{athenaeum_id}/builds" in paths
    assert "/api/v1/athenaeums/{athenaeum_id}/builds/{build_id}" in paths


def test_child_env_is_whitelisted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A non-inheritance proof: env pollution must not reach the child."""
    monkeypatch.setenv("GITHUB_TOKEN", "leakme")
    monkeypatch.setenv("HTTP_PROXY", "http://leak.example")
    env = child_env(tmp_path / "home")
    assert set(env) == set(SANDBOX_ENV_KEYS)
    assert "GITHUB_TOKEN" not in env
    assert "HTTP_PROXY" not in env
    assert env["PYTHONHASHSEED"] == "0"
    assert env["HOME"] == str(tmp_path / "home")
