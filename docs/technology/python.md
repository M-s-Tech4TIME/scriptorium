# Technology — Python 3.14.10 (bundled runtime)

- Version: **3.14.10**, the latest 3.14 patch (released 2026-10). Python 3.14
  is the current stable LTS line; support runs to October 2030.
- Distribution: **python-build-standalone** release `20261026`, asset
  `cpython-3.14.10+20261026-<arch>-unknown-linux-gnu-install_only_stripped.tar.gz`.
  `packaging/scripts/fetch-python.sh` pins both architectures and their
  SHA-256 digests, verifies the download, and extracts to
  `packaging/python-runtime`. nfpm installs it at
  `/opt/scriptorium/runtime/python-3.14`.
- Why: removes distro Python skew (Ubuntu 24.04 ships 3.12, Debian 12 ships
  3.11, RHEL 9 older) while keeping one exact, reproducible interpreter for
  the app venv and the isolated Sphinx build venv. 3.15 is deliberately
  deferred until after M5.
- Used:
  - `/opt/scriptorium/backend/.venv` — application venv, built by
    `packaging/scripts/build-app-venv.sh` from
    `backend/requirements.prod.lock` (runtime-only; the dev lock is used by
    CI/dev).
  - `/opt/scriptorium/build-venv` — engine-only Sphinx venv, built by
    `packaging/scripts/build-venv.sh` from
    `packaging/build-requirements.lock`.
  - Both venvs are built at package-build time and relocated to their final
    paths; the installed package never runs pip and never reaches the network.
    The runtime and both venvs ship without pip or bytecode, and the app venv
    uses the runtime-only `requirements.prod.lock` so dev tools stay out of
    the package.
- Verification: local bundled runtime reports `Python 3.14.10`; app and build
  venvs import their pinned stacks; backend suite `114 passed, 40 skipped`
  (2026-10-30). `pip-audit -r backend/requirements.lock` reports no known
  vulnerabilities.
