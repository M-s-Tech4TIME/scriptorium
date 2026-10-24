"""M4-C4 packaging/probe regressions (decision 0026 P3; 0003/0017 gate).

These are structural tests, not a package build: they pin the pieces the
package-build and future docutils bump depend on so a refactor cannot
silently drop the isolated build venv, the Redis ordering, the config
keys, or the manual 0.23 probe.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGING = ROOT / "packaging"


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def test_build_lock_is_isolated_and_pinned() -> None:
    lock = (PACKAGING / "build-requirements.lock").read_text(encoding="utf-8")
    assert "sphinx==9.1.0" in lock
    assert "docutils==0.22.4" in lock
    assert "myst-parser==5.1.0" in lock
    for forbidden in ("fastapi", "sqlalchemy", "celery", "asyncpg", "alembic"):
        assert f"\n{forbidden}==" not in f"\n{lock}"


def test_build_venv_script_is_hermetic() -> None:
    script = (PACKAGING / "scripts" / "build-venv.sh").read_text(encoding="utf-8")
    assert "build-requirements.lock" in script
    assert "--no-deps" in script
    assert "find_spec(forbidden)" in script
    for forbidden in ("fastapi", "sqlalchemy", "celery", "asyncpg", "alembic"):
        assert forbidden in script


def test_systemd_units_start_after_redis() -> None:
    for name in ("scriptorium-web.service", "scriptorium-worker.service"):
        lines = _lines(PACKAGING / "systemd" / name)
        assert "Requires=redis.service" in lines
        after = next(line for line in lines if line.startswith("After="))
        assert "redis.service" in after.split("=", 1)[1].split()


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


def test_nfpm_packages_build_venv_and_config_example() -> None:
    nfpm = (PACKAGING / "nfpm.yaml").read_text(encoding="utf-8")
    assert "src: ./build-venv" in nfpm
    assert "dst: /opt/scriptorium/build-venv" in nfpm
    assert "src: ./config.env.example" in nfpm
    assert "dst: /usr/share/doc/scriptorium/config.env.example" in nfpm
    assert '"redis"' in nfpm


def test_postinst_creates_artifacts_and_seeds_config() -> None:
    postinst = (PACKAGING / "scripts" / "postinst.sh").read_text(encoding="utf-8")
    assert "/var/lib/scriptorium/artifacts" in postinst
    assert "/usr/share/doc/scriptorium/config.env.example" in postinst
    assert "install -m 0600" in postinst
    assert "/opt/scriptorium/build-venv/bin/python" in postinst


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
