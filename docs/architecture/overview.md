# Architecture (Q20–Q22, Section 10)

Last updated: 2026-10-28 / Ref: URL-durability phase (0036)

```
[Browser: React19 TipTap3] --REST /api/v1--> [FastAPI 0.143 web@gunicorn+uvicorn]
        |                                          | SQLA 2.1
        |                                          v
        +---- poll build status  +--> [PG18]  [Redis] <-- [Celery 5.6 worker]
                                                     |
                                              snapshot sources
                                                     v
                                   [isolated Sphinx venv 9.1/5.1] (net-off,
                                   NoNewPrivileges, PrivateTmp, limits)
                                                     v
                            /var/lib/scriptorium/artifacts/{athenaeum}/{n}/
                              html/ + build.log + manifest.json
                                                     |
                              FastAPI /a/{public_slug}/... (0035/0036)
                              owner-published latest/stable + numbered builds
                              permanent 308 aliases + tombstones
                              manifest-derived CSP + E2 security headers
```

- **Canonical org model (0020):** native hierarchy `user → Athenaeums (libraries) → categories (sections) → grimoires (books)`; grimoire-level sharing only. Detail in `data-model.md` + `api.md`.
- **Serving (0035):** every successful build is an immutable numbered
  artifact with a manifest. Owners publish a build to `latest` and/or
  `stable`; `/a/{public_slug}/` follows the available pointer and
  `/a/{public_slug}/b/{n}/` is the durable numbered URL. Public/private is
  per Athenaeum (private default); private reads allow owner/member and
  use a short-lived `/a` access cookie for browser navigation. FastAPI
  serves files with a manifest-derived CSP, external-only CSS, no inline
  styles/handlers, and public/private cache policies. **URL durability
  (0036):** the owner may rename the public name; old names are permanent
  `308` aliases after the same access check, and deletion leaves permanent
  tombstones. Page-level path aliases and distribution remain later
  phases.
- **Canonical:** TipTap JSON `tiptap@1`; export RST/MyST deterministic; DB tree `nodes` → `toctree`; `conf.py` generated (allowlisted extensions only).
- **Module boundaries:** `convert/` (pure), `sphinx/` adapter (generation+theming), `worker/` (queue only),
  `routers/` (RBAC per request), `editor/` (schema v1). Third-party behind adapters (Rule 5.4).
- **Future-proof:** tree + `document_history` version-keyed → Phase A adds `versions` without rewrite;
  JSON canonical is Yjs-compatible → Phase B collab.
- **Packaging:** `/opt` code, `/etc` config, `/var/lib` data per Q4; 2 units per Q3.
