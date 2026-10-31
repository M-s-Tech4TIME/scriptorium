# PROJECT-SUMMARY (brain map, not a copy)

Last updated: 2026-10-31 / Ref: editor/content completion 0038 pushed (`476dfff`), CI ×3 green

- **What:** Scriptorium — self-hosted docs platform. Browser WYSIWYG (TipTap) → valid
  Sphinx source (RST default, MyST opt-in) → sandboxed background build → served HTML.
- **Stack (frozen, Rule 5; 0037):** Python 3.14.10 bundled (PBS 20261026),
  FastAPI 0.162.0, SQLA 2.1.6, Alembic 1.20.1, asyncpg 0.32.0, Celery 5.6.3 +
  redis-py 6.4.0 + bundled Redis 8.10.2, PG 18.6 exclusive, Node 26.13.0 LTS,
  React 19.3.1, TS 7.0.2, TipTap 3.32.1, Vite 8.3.5, Vitest 5.0.5,
  Sphinx 9.2.0, docutils 0.22.4 (0.23 gated), MyST 5.1.0, nfpm 2.x.
- **Arch in brief:** monorepo `frontend/ backend/ packaging/`; `web` + `worker` systemd
  units (user `scriptorium`); FHS `/opt`+`/etc/scriptorium`+`/var/lib|log|cache`;
  TipTap-JSON canonical (`tiptap@1`); DB tree `nodes` drives `toctree`;
  builds = limited-subprocess Sphinx 9.2.0 sandbox, `-W` (0026).
- **Conventions:** Conventional Commits, trunk `main` + `feat/*`, 5 CI gates, Rule 6 zero-skip.
- **Depth:** `docs/architecture/`, `docs/decisions/`, `docs/technology/compatibility-matrix.md`.
- **M2 (conversion) key facts:** docutils 0.22.4 inline markup never nests —
  RST export = one mark per run + fail-loud matrix; MyST carries the editor
  set via HTML paths. See `docs/technology/conversion.md` + 0017.
- **M4 status (as of this sync):** M3 C1–C6 complete, green ×3
  (0021–0025 landed). **M4-C1 + C2 + C3 + C3.5 complete:** 0026
  per-Athenaeum numbered builds, `sourcegen.py` deterministic staging,
  sandbox runner/Celery/`builds` endpoints. The theme is Scriptorium's
  own, from scratch (0027–0034; engine inherited incl. vendored JS,
  first-party search, Inter, feedback batches 0029–0034). **M4-C4
  complete/pushed (`1add6c8`, CI ×3):** isolated
  `/opt/scriptorium/build-venv` from a 27-pin engine-only lock, config
  example/queue/build keys, both units `Requires=scriptorium-redis`/
  `After=scriptorium-redis`, postinst artifacts/config seed/build-venv
  check, manual docutils-0.23 probe (59 passed; pin stays 0.22.4), M4
  report. **Serving phase 0035
  implemented (2026-10-25):** migration head `0007serving`;
  owner-published `latest`/`stable` pointers over immutable numbered
  builds; private-default per-Athenaeum visibility with owner/member
  access; FastAPI `/a/{public_slug}/...`; manifest-derived strict CSP;
  bounded namespaced external custom CSS; `/a` access cookie. Pushed as
  `6169696`; local gates/browser checks green and CI ×3 green.
  **URL-durability phase 0036 implemented (2026-10-28):** migration head
  `0008urldurability`; `public_names` single namespace; owner-only
  public-name rename; permanent `308` aliases after auth; permanent
  tombstones on delete; no rebuild; Option 1 URL shape retained. Pushed as
  `be5af83`; CI ×3 green. **Stack-upgrade phase 0037 implemented
  (2026-10-30):** bundled Python 3.14.10, Node 26.13.0 LTS, Redis 8.10.2
  bundled with `scriptorium-redis.service`, Sphinx 9.2.0, current backend/
  frontend pins, app/build venv relocation, CI/audit gates, support matrix.
  **Editor/content completion 0038 pushed (`476dfff`, 2026-10-31):** V1
  React app, TipTap editor, tree/history/import, image/GIF media
  (`media_assets`, migration 0009), build media copying, `GET /auth/me`;
  frontend typecheck/test/build gates added to CI. CI ×3 green; backend
  ran 159 tests with no skips (live PG18 media/history/migration).
  Page-path aliases, backup/restore, server move/first-run provisioning,
  M5, and the dedicated SEO phase remain later; distribution awaits
  Q-DIST-A…D. Owner ruled the artifact
  to be a portable static website + design mandates (security parity;
  structure locked, skin open). Terminology: "grimoire" everywhere
  (0018). Auth surface = login/refresh/logout + `/auth/me`; serving adds the
  browser access cookie. Live API tests drive the app via
  `httpx.ASGITransport` (starlette.testclient import warns → Rule 6).
- **Config keys:** `SECRET_KEY` (JWT; empty fails loud), `DATABASE_URL`,
  `SCRIPTORIUM_COOKIE_SECURE` (prod sets Secure), `REDIS_URL` (limiter,
  fail-closed when missing), `CELERY_BROKER_URL` (worker), and the
  `SC_BUILD_*` / `SC_SPHINX_*` build paths/limits and `SC_MEDIA_ROOT`
  (media storage); optional
  `SCRIPTORIUM_RATELIMIT_LOGIN_MAX` / `_WINDOW_S` (0019). Packaged
  example at `packaging/config.env.example` (0600 seed).
