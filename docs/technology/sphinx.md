# Technology — Sphinx 9.1.0 + docutils 0.22.4 + MyST-Parser 5.1.0

- Versions (locked): Sphinx 9.1.0 (2025-12-31), docutils 0.22.4 (0.23 gated —
  MyST 5.x upper-bounds docutils; verify in CI before bump, decision 0003),
  MyST-Parser 5.1.0 (2026-05-13, needs Sphinx ≥8<10, markdown-it-py ~4.2).
- Why: documentation engine core; RST default + MyST opt-in per project (§5).
- Used: isolated build venv only (never app deps, Rule 5.4); `backend/app/sphinx/`;
  generated-only `conf.py`, allowlisted extensions (threat model).
- Verified: 2026-10-16 (sphinx-doc.org/PyPI; lock resolved 2026-10-16).
