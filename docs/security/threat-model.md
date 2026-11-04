# Threat model (initial, Q22 / §10)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

## Primary risk: untrusted content → Sphinx code exec
- Generated-only `conf.py`; extension allowlist (any addition = Rule 4 + record).
- Isolated build venv (M4-C4: 27-pin engine-only lock, `--no-deps`, app-dep
  absence asserted; `/opt/scriptorium/build-venv`); sandbox:
  `NoNewPrivileges`, `PrivateTmp`, CPU/mem/time limits, per-job temp dir;
  single-build-per-project; timeouts. Egress isolation is by construction
  of the pinned stack (no credentials/proxy in the whitelisted env), not
  a kernel namespace — disclosed P3 limitation.
- No remote fetch at build; link-check opt-in with allowlist (SSRF guard).
- Package install: bundled Python 3.14.10 + Redis 8.10.2 are built and
  verified at package-build time; the target host never runs pip or
  fetches code. `config.env`/`redis.conf` are seeded only when absent;
  `postinst` never migrates; worker/web `Requires=scriptorium-redis.service`.

## Serving risks → mitigations (0035)
- **Private artifact disclosure / IDOR:** per-Athenaeum `is_public`
  (private default); serving checks owner or any grimoire membership;
  outsiders get uniform `404`; private responses `private, no-store`,
  `Vary: Cookie`, `X-Robots-Tag: noindex, nofollow`.
- **Browser navigation auth:** a 15-minute HttpOnly `scriptorium_access`
  cookie scoped to `/a` (SameSite=Lax; Secure in production) supplements
  bearer auth for document navigations; API routes still require bearer.
- **Path traversal / symlink escape:** artifact root jail, resolved-path
  containment, published-only numbered lookup, no artifact without a valid
  manifest, missing/traversal → `404`.
- **CSP / inline injection:** strict `default-src 'none'` policy built from
  exact SHA-256 inline-script hashes; `style-src 'self'`, no inline
  `style=`/event handlers/`<style>` blocks; manifest fails the build on
  violations; no remote origins, frames, objects, or workers.
- **Custom CSS as an attack surface:** 64 KiB cap, flat rules only,
  namespaced under `html[data-sd-athenaeum]`, no at-rules/`url()`/`data:`/
  backslash escapes/`expression()`/`behavior`/`position: fixed`; custom CSS
  is an external file, not a template or script hook; changes require a
  rebuild and published artifacts stay immutable.
- **Export portability:** `manifest.json` is the authoritative inventory,
  CSP hash list, and custom-CSS record for a copied artifact; static hosts
  must apply the documented headers themselves.
- **Caching disclosure:** public numbered builds are immutable-cached;
  making a site private later cannot recall copies already cached at
  public numbered URLs (disclosed in 0035). Alias/private responses are
  not cacheable.
- **Alias takeover / namespace confusion (0036):** `public_names` is one
  global namespace keyed by slug; canonical names, aliases, and tombstones
  all occupy it. Old names never become reusable, including after deletion.
  Rename/create/delete serialize on a transaction-scoped advisory lock and
  still rely on the slug PK/unique indexes as the hard guard; collisions
  are `409`, never an implicit takeover. Private aliases authorize the
  current site before redirecting, so an old name cannot leak a private
  site's existence; tombstoned names are uniform `404`.
- **Open redirect / cache poisoning:** alias `Location` values are relative
  and built from the validated canonical slug; path suffix and query are
  preserved, never echoed into a scheme/host. Alias redirects are `308`
  with `no-cache` (public) or `private, no-store` + `Vary: Cookie` +
  `X-Robots-Tag` (private).

## Transport risks → built-in TLS (0040)
- **Plaintext exposure:** there is no plaintext application listener. The
  web tier serves HTTPS only on `SC_TLS_BIND` (default 443); the separate
  port-80 service only returns `308` to HTTPS. Both use
  `CAP_NET_BIND_SERVICE` and run as `scriptorium`, not root.
- **Weak protocol/cipher downgrade:** TLS 1.2 minimum and TLS 1.3 only;
  TLS 1.2 is ECDHE + AEAD (AES-GCM/ChaCha20-Poly1305). CBC, RSA key
  exchange, 3DES, RC4, NULL, compression, renegotiation, and session
  tickets are disabled. SHA-256 or stronger signatures are required.
- **Certificate/key compromise:** the local CA key is `root:root 0600`
  and never leaves the host in normal operation; leaf keys are `0600`;
  fullchains are `0644`; version directories are `0750`. The service
  cannot read the CA key. Back it up only as a root secret.
- **Untrusted imported material:** import validates PEM shape, dates,
  key strength/match, signature hash, `serverAuth` EKU, SAN presence, and
  internal chain links before an atomic install. An imported external
  root is not added to the system trust store; trust remains the
  operator's responsibility.
- **Failed rotation / lockout:** activation reloads `scriptorium-web` and
  restores the previous certificate/state if the reload fails. Rollback
  validates the target version first. Pruning protects the active
  version.
- **Redirect Host injection / open redirect:** the port-80 service never
  reflects an arbitrary `Host`. It honors the header only when it matches
  a current certificate SAN, otherwise `SC_TLS_REDIRECT_HOST`, otherwise
  a certificate SAN, otherwise returns `400`.
- **HSTS lock-in:** HSTS is off by default, has no preload, and should be
  enabled only after clients trust the CA. `tls hsts` reverts state if
  the live reload fails.
- **Proxy-header spoofing:** Uvicorn proxy headers are disabled and
  `X-Forwarded-For` is untrusted; rate limiting keys on the socket peer.
  Do not place an untrusted proxy in front of the app (F-L1).

## Provisioning and move risks (0040)
- **Privilege boundary:** `scriptorium-admin` refuses to run as any user
  other than root or `scriptorium`. `setup`/`verify` are read-only;
  `migrate` is explicit and refuses PG < 18; `postinst` never touches the
  database or generates certificates.
- **Ownership drift:** every Scriptorium-managed path is
  `scriptorium:scriptorium`; the accepted exceptions are systemd unit
  files/package metadata (root), the external PostgreSQL data directory
  (`postgres`), and `ca.key` (`root:root 0600`). `postinst` reapplies the
  recursive ownership and then forces the CA key back to root.
- **First-account bootstrap abuse:** there is no open registration and no
  environment-secret bootstrap. `user create` is a privileged CLI action;
  passwords come from a TTY prompt or `--password-stdin`, never argv;
  hashes are Argon2id; policy is 12–1024 characters with no composition
  rules (B1). `user list` never prints hashes.
- **Move archive exposure:** archives contain all content and media.
  Transfer only over SSH/HTTPS, keep them `0600`, verify SHA-256 on the
  destination, and delete temporary copies. The supported move is
  content-only; users, memberships, refresh tokens, and audit rows are
  never exported. Raw `pg_dump` + filesystem copy is the documented
  ops-only full-fidelity fallback and is treated as a root secret.
- **URL/name integrity on move:** CLI restore is strict: any live name or
  another owner's tombstone that conflicts with the archive fails before
  writes. `--force` bypasses only the empty-target guard, never name
  strictness. The API owner restore retains 0039 auto-suffix behaviour.
- **Restore jail:** the move path reuses the 0039 validation-before-write
  core (manifest/inventory/hashes/sizes, fresh UUIDs, artifact/media
  jails, cleanup on failure); there is no second restore implementation.
- **New-host secret:** generate a new `SECRET_KEY` on the destination;
  refresh tokens are not exported and users re-authenticate. Config is
  one no-shell-evaluation loader shared by CLI and services, with a real
  environment variable winning over the file.

## App risks → mitigations
- XSS (built HTML + editor): output encoding, strict served-artifact CSP
  (0035 E2), editor CSP unchanged, SVG sanitize, upload allowlist + size
  caps. V1 media accepts PNG/JPEG/GIF/WebP/AVIF only; the type is decided
  from magic bytes (never `Content-Type` or the filename), SVG is refused,
  and remote/data image sources are rejected at document save.
- **Media IDOR / storage abuse:** every upload, list, and content read
  re-checks grimoire membership; a media row is owned by exactly one
  grimoire and document saves reject cross-grimoire references. Bytes live
  outside the web root under `SC_MEDIA_ROOT` with generated paths; uploads
  stream with a 10 MiB cap, write atomically, and roll back the file when
  the DB insert fails. Content responses are `nosniff` and private-cached.
- **Build-time media integrity:** referenced assets are resolved from DB
  rows (not user paths), the runner normalizes the canonical leading `/`
  then refuses non-`_static/media/`, traversal, or backslash paths, and
  missing files fail the build loudly.
- **Backup archive attacks (0039):** restore treats every archive as
  untrusted. It rejects absolute/traversal/backslash paths, symlinks,
  hardlinks, devices, duplicate or file/directory-colliding entries,
  encrypted ZIP entries, undeclared/missing entries, hash or size
  mismatches, invalid JSON/rows/FKs/cycles, and media/build payloads that
  do not match their rows. Limits: 8 GiB archive, 16 GiB expanded, 200,000
  entries, 512 MiB per entry. Validation/extraction completes before any
  DB write; filesystem staging is cleaned on failure and the import is one
  transaction. Full archives live outside the web root and download only
  through an owner-scoped job plus a 15-minute HMAC single-use token; files
  are deleted after send/expiry. Export is owner-only; restore always
  creates a fresh site owned by the importer and never exports users,
  memberships, refresh tokens, or audit rows.
- Path traversal: slug allowlist `[a-z0-9-]+`, jail to project dir, no `..`.
- IDOR/tenancy: membership check on every project request + tests (M1 gate).
- Auth: Argon2id, lockout, short JWT + rotating refresh (HttpOnly/Secure/SameSite), audit log.
- Secrets: env/file 0600 only; gitleaks blocking; none in repo/brain/logs.
- DoS: queue limits, rate limits, artifact quotas; journald + `/var/log/scriptorium`.
- Supply chain: GPG + SHA256 + CycloneDX SBOM + provenance (Q8); pinned locks; `pip-audit`/`npm audit` + SAST blocking.
- Error handling: no internals to clients; structured logs without sensitive data.

Risks tracked per milestone; M4 gate: malicious-input build stays jailed; M5: full review.
