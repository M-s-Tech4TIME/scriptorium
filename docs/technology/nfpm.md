# Technology — nfpm 2.x (packaging)

- Version: 2.x; the 2026-10-30 validation build used **nfpm 2.48.0**.
  M5 pins the exact release in the signed-package pipeline (Rule 5.2).
- Why: single YAML → `.deb` + `.rpm`, zero-dep Go binary, CI-friendly (decision 0001/Q2).
  `lintian` + `rpmlint` gates catch non-compliance.
- Used: `packaging/nfpm.yaml` + `systemd/` + `scripts/` (postinst/prerm never touch DB).
- **Bundled runtime contract:** `nfpm.yaml` packages the application code,
  the Python 3.14.10 runtime (`fetch-python.sh`), the app venv from
  `backend/requirements.prod.lock` (`build-app-venv.sh`), the isolated
  `/opt/scriptorium/build-venv`
  (`build-venv.sh`), the Redis 8.10.2 runtime (`build-redis.sh`), the
  `config.env.example`, `redis.conf.example`, and all three systemd units.
  `postinst` seeds both configs only when absent, creates `artifacts/` and
  the Redis data dir, and fails loud if any runtime is missing. The package
  no longer depends on distro Python or Redis packages.
- CI: the `packaging` workflow pins the new scripts, runtime versions,
  checksums, nfpm contents, Redis ordering and compose image. The actual
  signed package build remains M5.
- Verified: 2026-10-30 (goreleaser/nfpm; runtime build scripts exercised
  locally). Exact nfpm pin at M5 with matrix entry.
