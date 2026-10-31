"""Sandboxed Sphinx runner (M4-C3, decision 0026 P3).

The limited-subprocess sandbox, mechanically:

- **Minimal environment:** the child process gets a whitelisted env
  (PATH, LC_ALL, PYTHONHASHSEED, HOME inside the workspace). Proxy
  variables, secrets, and anything inherited are structurally absent —
  a whitelisted env, not a stripped one.
- **RLIMITs:** CPU seconds, address-space bytes, file-size bytes, and
  zero core dumps, applied in the child before exec.
- **No network:** the pinned pipeline makes no requests and has no
  credentials to make them with; with a minimal env there is neither a
  proxy nor an endpoint to dial. Honest limitation (disclosed, 0026 +
  technology/sphinx.md): without the container option (ruled out for
  M4), OS-level egress isolation comes *by construction* of the pinned
  stack, not from a kernel namespace.
- **Warning bar:** `-W` — a build is `ok` only when warning-free.

Paths come from env per call (dev/CI overrides via `SC_*`; FHS defaults
are the packaged form). Disclosed micro-default: the interim
`SC_BUILD_PYTHON` default is `sys.executable` (dev/CI convenience) —
production must point it at the isolated build venv (packaging, C4).
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from app.serving.manifest import write_artifact_manifest
from app.sphinx.sourcegen import SitePlan

_BUILD_DIR = "_build"

SANDBOX_ENV_KEYS = ("PATH", "LC_ALL", "PYTHONHASHSEED", "HOME")


def child_env(home: Path) -> dict[str, str]:
    """The whitelisted child environment: inherited keys never enter, ever."""
    return {
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "HOME": str(home),
    }


@dataclass(frozen=True)
class BuildOutcome:
    ok: bool
    log_path: str | None
    artifact_path: str | None


@dataclass(frozen=True)
class BuildConfig:
    artifact_root: Path
    build_root: Path
    build_python: Path
    cpu_seconds: int
    memory_bytes: int
    max_file_bytes: int
    timeout_seconds: int


class RunnerConfigError(RuntimeError):
    """Build configuration is invalid — fail loud, never silent."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RunnerConfigError(f"{name} must be an integer, got {raw!r}") from exc


def build_config() -> BuildConfig:
    return BuildConfig(
        artifact_root=Path(
            os.environ.get("SC_ARTIFACT_ROOT", "/var/lib/scriptorium/artifacts")
        ),
        build_root=Path(os.environ.get("SC_BUILD_ROOT", "/var/lib/scriptorium/builds")),
        build_python=Path(os.environ.get("SC_BUILD_PYTHON", sys.executable)),
        cpu_seconds=_env_int("SC_SPHINX_CPU_SECONDS", 600),
        memory_bytes=_env_int("SC_SPHINX_MEMORY_BYTES", 1_610_612_736),
        max_file_bytes=_env_int("SC_SPHINX_MAX_FILE_BYTES", 536_870_912),
        timeout_seconds=_env_int("SC_SPHINX_TIMEOUT_S", 900),
    )


def _child_limits(cfg: BuildConfig) -> None:
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (cfg.cpu_seconds, cfg.cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS, (cfg.memory_bytes, cfg.memory_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (cfg.max_file_bytes, cfg.max_file_bytes))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


_THEME_DIR = Path(__file__).resolve().parent / "theme" / "scriptorium"
# Vendored engine assets (0027/0028 mechanics): three scripts + the two
# `.jinja` static templates (documentation_options / language_data).
# `searchtools.js` remains in the vendored set (0027 contract) although
# the 0032 first-party search no longer loads it on any page.
# The vision of the theme's `inherit = none`: the basic theme chain
# breaks, so the builder would never reach the engine's own statics;
# vendoring the `.jinja` templates into the staged theme makes the
# builder render them from its own global context — the engine-emitted
# path, materialized from the pinned distribution, zero network.
_ENGINE_ASSETS = (
    "doctools.js",
    "searchtools.js",
    "sphinx_highlight.js",
    "documentation_options.js.jinja",
    "language_data.js.jinja",
)


def _sphinx_static_dir(build_python: Path) -> Path:
    """Locate the build interpreter's own Sphinx — the pinned engine.

    Business rule (0027/0028): vendored engine assets must come from the
    SAME Sphinx distribution the build runs on, never from the app venv's
    (they may differ once the isolated build venv exists, C4).
    """
    probe = subprocess.run(
        [
            str(build_python),
            "-c",
            (
                "import sphinx; from pathlib import Path;"
                " print(Path(sphinx.__file__).resolve().parent)"
            ),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        raise RunnerConfigError(
            f"SC_BUILD_PYTHON ({build_python}) cannot import Sphinx: "
            f"{probe.stderr.strip()}"
        )
    return Path(probe.stdout.strip()) / "themes" / "basic" / "static"


def _materialize(
    workspace: Path,
    plan: SitePlan,
    build_python: Path,
    media: Mapping[str, Path] | None = None,
) -> None:
    """Write the staged site, the theme, the style module, vendored JS.

    - theme → `workspace/theme/scriptorium` (conf's `html_theme_path`);
      the builder auto-copies its `static/` into the artifact `_static/`.
    - the Pygments style module beside `conf.py` (the dotted
      `scriptorium_style.ScriptoriumStyle` reference imports it from the
      workspace root — sys.path is seeded in the staged conf).
    - engine JS vendored from the build interpreter's pinned Sphinx into
      the staged theme `static/` (0027 "vendored, never fetched"):
      `doctools.js` + `sphinx_highlight.js` reach pages via the builder's
      asset auto-list; `searchtools.js` stays in the vendored asset set
      for the 0027 contract but no page loads it after the 0032
      first-party search takeover; `language_data.js` is build-emitted
      and supplies stopwords/stemmer to the first-party core. A missing
      engine file means the engine distribution changed shape → fail
      loud, engine/theme contracts bump together (0027).
    """
    workspace.mkdir(parents=True, exist_ok=False)
    (workspace / ".home").mkdir()
    (workspace / "_static").mkdir()
    for relpath, text in plan.files.items():
        path = workspace / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    for relpath, source in (media or {}).items():
        # The URL is generated from an asset UUID; refuse anything that
        # could escape the staged static directory.
        if not relpath.startswith("_static/media/") or ".." in Path(relpath).parts:
            raise RunnerConfigError(f"unsafe media path: {relpath!r}")
        if not source.is_file():
            raise RunnerConfigError(f"media file missing: {source}")
        target = workspace / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(source, target)

    theme_target = workspace / "theme" / "scriptorium"
    shutil.copytree(_THEME_DIR, theme_target)
    shutil.copy(_THEME_DIR / "style.py", workspace / "scriptorium_style.py")

    static_dir = _sphinx_static_dir(build_python)
    for name in _ENGINE_ASSETS:
        source = static_dir / name
        if not source.is_file():
            raise RunnerConfigError(
                f"pinned Sphinx ({static_dir}) is missing {name} — "
                "engine/theme DOM contracts bump together (0027)"
            )
        shutil.copy(source, theme_target / "static" / name)


def _log_text(
    notes: tuple[str, ...],
    stdout: str,
    stderr: str,
    exit_code: int | str,
    cmd: list[str],
) -> str:
    lines = [
        "Scriptorium build log (0026)",
        f"command: {shlex.join(cmd)}",
        *[f"note: {note}" for note in notes],
        "--- stdout ---",
        stdout,
        "--- stderr ---",
        stderr,
        f"--- exit: {exit_code} ---",
    ]
    return "\n".join(lines)


def run_build(
    plan: SitePlan,
    build_id: uuid.UUID,
    athenaeum_id: uuid.UUID,
    build_number: int,
    site_id: str = "",
    media: Mapping[str, Path] | None = None,
) -> BuildOutcome:
    """Materialize the plan, run the sandboxed build, move the artifact."""
    cfg = build_config()
    workspace = cfg.build_root / str(build_id)
    artifact_dir = cfg.artifact_root / str(athenaeum_id) / str(build_number)

    shutil.rmtree(workspace, ignore_errors=True)
    _materialize(workspace, plan, cfg.build_python, media)

    cmd = [
        str(cfg.build_python),
        "-m",
        "sphinx",
        "-W",
        "-b",
        "html",
        ".",
        str(workspace / _BUILD_DIR / "html"),
    ]
    env = child_env(workspace / ".home")

    timed_out = False
    exit_code: int | str = 0
    stdout = ""
    stderr = ""
    try:
        proc = subprocess.run(
            cmd,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=cfg.timeout_seconds,
            check=False,
            preexec_fn=lambda: _child_limits(cfg),
        )
        stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode(errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        exit_code = "timeout"

    ok = (not timed_out) and exit_code == 0
    log = _log_text(plan.notes, stdout, stderr, exit_code, cmd)

    if ok:
        shutil.copytree(workspace / _BUILD_DIR / "html", artifact_dir / "html")
        (artifact_dir / "build.log").write_text(log, encoding="utf-8")
        # E2: the manifest is part of the immutable artifact. It records
        # the file inventory, inline-script hashes for strict CSP, and the
        # custom-CSS hash. A manifest failure fails the build.
        write_artifact_manifest(
            artifact_dir,
            athenaeum_id=athenaeum_id,
            build_number=build_number,
            site_id=site_id,
        )
        # staging was ephemeral by design (0026): sources are DB-derived.
        shutil.rmtree(workspace, ignore_errors=True)
        return BuildOutcome(True, str(artifact_dir / "build.log"), str(artifact_dir))

    log_path = workspace / "build.log"
    log_path.write_text(log, encoding="utf-8")
    # failed builds keep their workspace for inspection; the retention
    # decision belongs to the serving phase (0026 P4).
    return BuildOutcome(False, str(log_path), None)
