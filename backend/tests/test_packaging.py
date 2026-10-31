"""M4-C4 packaging/probe regressions (decision 0026 P3; 0003/0017 gate).

These are structural tests, not a package build: they pin the pieces the
package-build and future docutils bump depend on so a refactor cannot
silently drop the isolated build venv, the bundled runtimes, the Redis
ordering, the config keys, or the manual 0.23 probe.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGING = ROOT / "packaging"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_build_lock_is_isolated_and_pinned() -> None:
    lock = (PACKAGING / "build-requirements.lock").read_text(encoding="utf-8")
    assert "sphinx==9.2.0" in lock
    assert "docutils==0.22.4" in lock
    assert "myst-parser==5.1.0" in lock
    for forbidden in ("fastapi", "sqlalchemy", "celery", "asyncpg", "alembic"):
        assert f"\n{forbidden}==" not in f"\n{lock}"


def test_build_venv_script_is_hermetic() -> None:
    script = (PACKAGING / "scripts" / "build-venv.sh").read_text(encoding="utf-8")
    assert "build-requirements.lock" in script
    assert "--no-deps" in script
    assert "--no-compile" in script
    assert "site-packages/pip" in script
    assert "python-runtime/bin/python3.14" in script
    assert "/opt/scriptorium/runtime/python-3.14" in script
    assert "find_spec(forbidden)" in script
    for forbidden in ("fastapi", "sqlalchemy", "celery", "asyncpg", "alembic"):
        assert forbidden in script


def test_prod_lock_excludes_dev_tools() -> None:
    lock = (ROOT / "backend" / "requirements.prod.lock").read_text(encoding="utf-8")
    for runtime in ("fastapi==", "sqlalchemy==", "alembic==", "asyncpg==", "celery=="):
        assert f"\n{runtime}" in f"\n{lock}"
    for dev_only in (
        "pytest==",
        "ruff==",
        "mypy==",
        "pip-audit==",
        "httpx==",
        "types-pygments==",
    ):
        assert f"\n{dev_only}" not in f"\n{lock}"


def test_app_venv_script_is_pinned_and_relocatable() -> None:
    script = (PACKAGING / "scripts" / "build-app-venv.sh").read_text(encoding="utf-8")
    assert "backend/requirements.prod.lock" in script
    assert "--no-deps" in script
    assert "--no-compile" in script
    assert "site-packages/pip" in script
    assert "scriptorium-admin" in script
    assert "sys.path.insert" in script
    assert "relocate-venv.sh" in script
    assert "/opt/scriptorium/backend/.venv" in script
    for pinned in ("fastapi", "sqlalchemy", "alembic", "asyncpg", "celery", "pydantic"):
        assert pinned in script


def test_python_runtime_is_pinned_with_checksums() -> None:
    script = (PACKAGING / "scripts" / "fetch-python.sh").read_text(encoding="utf-8")
    assert "PYTHON_VERSION=3.14.10" in script
    assert "PBS_RELEASE=20261026" in script
    assert "4d3c16c59ed0802a3d1d34d8bce504b15ceeaff39d62dadecc6a9fa803412aed" in script
    assert "90f48337bc3dd4ae6eda81e001e4c981236d403b6b5a07778bbdf94ee423dc00" in script
    assert "sha256sum -c -" in script
    assert "install_only_stripped" in script
    assert "site-packages/pip" in script


def test_redis_runtime_is_pinned_with_checksum() -> None:
    script = (PACKAGING / "scripts" / "build-redis.sh").read_text(encoding="utf-8")
    assert "REDIS_VERSION=8.10.2" in script
    assert "b9ffee226b5eecdba98a679260dad764b2a4ebd90dce4ad5ac9e9f3eef9c02b3" in script
    assert "sha256sum -c -" in script
    assert "BUILD_TLS=no" in script


def test_systemd_units_start_after_bundled_redis() -> None:
    for name in ("scriptorium-web.service", "scriptorium-worker.service"):
        lines = _lines(PACKAGING / "systemd" / name)
        assert "Requires=scriptorium-redis.service" in lines
        after = next(line for line in lines if line.startswith("After="))
        assert "scriptorium-redis.service" in after.split("=", 1)[1].split()

    redis = _lines(PACKAGING / "systemd" / "scriptorium-redis.service")
    assert any(
        line.startswith("ExecStart=/opt/scriptorium/redis/bin/redis-server")
        for line in redis
    )
    assert "Type=notify" in redis


def test_config_example_has_build_and_queue_keys() -> None:
    values: dict[str, str] = {}
    for line in _lines(PACKAGING / "config.env.example"):
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value
    assert values["CELERY_BROKER_URL"].startswith("redis://")
    assert values["REDIS_URL"].startswith("redis://")
    assert values["SC_BUILD_DISPATCH"] == "celery"
    assert values["SC_BUILD_PYTHON"] == "/opt/scriptorium/build-venv/bin/python"
    assert values["SC_ARTIFACT_ROOT"] == "/var/lib/scriptorium/artifacts"
    assert values["SC_BUILD_ROOT"] == "/var/lib/scriptorium/builds"
    assert values["SECRET_KEY"] == ""  # fail loud until the admin generates one
    assert "CHANGE_ME" in values["DATABASE_URL"]


def test_nfpm_packages_bundled_runtimes_and_config() -> None:
    nfpm = (PACKAGING / "nfpm.yaml").read_text(encoding="utf-8")
    for src, dst in (
        ("backend/app", "/opt/scriptorium/backend/app"),
        (
            "backend/requirements.prod.lock",
            "/opt/scriptorium/backend/requirements.prod.lock",
        ),
        ("packaging/python-runtime", "/opt/scriptorium/runtime/python-3.14"),
        ("packaging/app-venv", "/opt/scriptorium/backend/.venv"),
        ("packaging/build-venv", "/opt/scriptorium/build-venv"),
        ("packaging/redis-runtime", "/opt/scriptorium/redis"),
        (
            "packaging/config.env.example",
            "/usr/share/doc/scriptorium/config.env.example",
        ),
        (
            "packaging/redis.conf.example",
            "/usr/share/doc/scriptorium/redis.conf.example",
        ),
        (
            "packaging/systemd/scriptorium-redis.service",
            "/lib/systemd/system/scriptorium-redis.service",
        ),
    ):
        assert f"src: {src}" in nfpm
        assert f"dst: {dst}" in nfpm
    assert '"redis"' not in nfpm
    assert "python3.12" not in nfpm


def test_postinst_creates_runtime_dirs_and_seeds_configs() -> None:
    postinst = (PACKAGING / "scripts" / "postinst.sh").read_text(encoding="utf-8")
    assert "/var/lib/scriptorium/artifacts" in postinst
    assert "/var/lib/scriptorium/redis" in postinst
    assert "/usr/share/doc/scriptorium/config.env.example" in postinst
    assert "/usr/share/doc/scriptorium/redis.conf.example" in postinst
    assert "install -m 0600" in postinst
    for runtime in (
        "/opt/scriptorium/runtime/python-3.14/bin/python3.14",
        "/opt/scriptorium/backend/.venv/bin/python",
        "/opt/scriptorium/backend/.venv/bin/scriptorium-admin",
        "/opt/scriptorium/build-venv/bin/python",
        "/opt/scriptorium/redis/bin/redis-server",
    ):
        assert runtime in postinst


def test_docutils_probe_is_manual_and_forced() -> None:
    probe = (ROOT / "scripts" / "probe-docutils-023.sh").read_text(encoding="utf-8")
    assert "docutils==0.23" in probe
    assert "--no-deps" in probe
    assert "test_roundtrip.py" in probe
    assert "test_sourcegen.py" in probe
    assert "test_theme_build.py" in probe
    assert "-W error" in probe

    workflow = (ROOT / ".github" / "workflows" / "docutils-probe.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
    assert "probe-docutils-023.sh" in workflow
    assert "push:" not in workflow
