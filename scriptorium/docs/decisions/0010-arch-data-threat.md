# 0010 — Arch/data-model/threat Q20–Q22

Status: accepted | Date: 2026-10-16 | Approver: owner
Options: Canonical TipTap JSON + export vs RST-canonical (rejected: fidelity + collab cost); generic ordered-tree nodes vs literal categories/branches tables (rejected: rigid).
Decision: TipTap JSON tiptap@1 canonical; tables users/memberships/projects/nodes/documents/document_history/builds/audit_log; DB drives toctree/conf.py (generated only, allowlisted extensions); Furo-extended theme; sandbox (net-off, NoNewPrivileges, PrivateTmp, limits); JWT access + rotating refresh in HttpOnly Secure SameSite.
Details: `docs/architecture/overview.md`, `data-model.md`, `docs/security/threat-model.md`.
