# Technology — Python 3.12.x

- Version: 3.12.x (latest patch at lock; decision 0003). Released 2023-10, support to Oct 2028.
- Why: max-common across baselines (U24.04 native; D12/RHEL9 via bundled/AppStream 3.12); all deps support it; 3.15 too new, 3.13 needs PPA/source.
- Used: backend + isolated Sphinx venv (`/opt/scriptorium`). **M4-C4:**
  `packaging/scripts/build-venv.sh` builds `/opt/scriptorium/build-venv`
  from `packaging/build-requirements.lock` (engine trio only, no app
  deps); `postinst` verifies it and production sets
  `SC_BUILD_PYTHON` there. Verified: 2026-10-16; build venv created and
  imported 9.1.0/0.22.4/5.1.0 on 2026-10-24.
