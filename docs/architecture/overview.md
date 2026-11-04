# Architecture (Q20–Q22, Section 10)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

```
[HTTP :80] --308--> [HTTPS :443, built-in TLS] <--REST /api/v1-- [Browser: React 19.3 + TipTap 3.32]
                         |
                         v
             [FastAPI 0.162 web @ gunicorn+uvicorn]
                         | SQLA 2.1
                         v
             [PG18]  [Redis] <-- [Celery 5.6 worker]
                         |
                  snapshot sources
                         v
       [isolated Sphinx venv 9.2/MyST 5.1] (net-off,
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

- **Built-in TLS (0040):** the web tier terminates HTTPS itself with
  `TlsUvicornWorker` on `SC_TLS_BIND` (default `0.0.0.0:443`) and a
  hardened ECDHE+AEAD context; `scriptorium-redirect.service` answers
  port 80 with `308` only. There is no plaintext application listener
  and no reverse proxy in V1. A local ECDSA P-384 CA issues ECDSA P-256
  leaves (90 days); the daily timer renews at 30 days, keeps 5 versions,
  and supports import/rollback/prune/HSTS. The CA key is `root:root
  0600`; every other app path is `scriptorium:scriptorium` (0040 O1).
- **First run / server move (0040):** `scriptorium-admin` provides
  `setup` (read-only preflight), `migrate`, `user create/list`,
  `backup export`, `restore`, `verify`, and the full `tls` lifecycle. A
  move is a maintenance-window, content-only export/restore per
  Athenaeum using the 0039 archive core; CLI restore is strict on public
  names, preserves numbered `/b/{n}/` URLs, and `verify` checks DB/head,
  names/pointers, artifacts/manifests, media hashes, and TLS before
  cutover. CLI and services share one no-shell-evaluation config loader.
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
- **Canonical:** TipTap JSON `tiptap@1`; export RST/MyST deterministic; DB tree `nodes` → `toctree`; `conf.py` generated (allowlisted extensions only). V1 media is images/GIF only: uploads are sniffed, stored under `SC_MEDIA_ROOT`, referenced as `/_static/media/{uuid}.{ext}`, validated against the owning grimoire on save, and copied into each build artifact. Video/audio/attachments and bulk import are later.
- **Backup/restore (0039):** owners export one Athenaeum as a self-contained
  ZIP or `.tar.gz` in **Editorial** (content, media, names, every
  ever-published successful build + artifact) or **Full** (adds failed
  builds, logs, and artifacts for every successful build) mode. Editorial
  streams synchronously; Full runs as a Celery job with a 15-minute
  single-use signed download. Restore validates the whole archive before
  any write, creates a fresh Athenaeum owned by the importer, preserves
  build numbers/pointers and reclaimable public names, nulls unmatched
  identities, and rewrites media URLs to fresh asset UUIDs. Archives are
  untrusted input with strict traversal/inventory/hash/size checks.
- **Module boundaries:** `convert/` (pure), `sphinx/` adapter (generation+theming), `worker/` (queue only),
  `routers/` (RBAC per request), `editor/` (schema v1). Third-party behind adapters (Rule 5.4).
- **Future-proof:** tree + `document_history` version-keyed → Phase A adds `versions` without rewrite;
  JSON canonical is Yjs-compatible → Phase B collab.
- **Packaging:** `/opt` code, `/etc` config, `/var/lib` data per Q4; 2 units per Q3.
