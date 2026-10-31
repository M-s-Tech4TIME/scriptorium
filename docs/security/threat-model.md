# Threat model (initial, Q22 / §10)

Last updated: 2026-10-30 / Ref: stack-upgrade phase (0037)

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

## App risks → mitigations
- XSS (built HTML + editor): output encoding, strict served-artifact CSP
  (0035 E2), editor CSP unchanged, SVG sanitize, upload allowlist + size
  caps.
- Path traversal: slug allowlist `[a-z0-9-]+`, jail to project dir, no `..`.
- IDOR/tenancy: membership check on every project request + tests (M1 gate).
- Auth: Argon2id, lockout, short JWT + rotating refresh (HttpOnly/Secure/SameSite), audit log.
- Secrets: env/file 0600 only; gitleaks blocking; none in repo/brain/logs.
- DoS: queue limits, rate limits, artifact quotas; journald + `/var/log/scriptorium`.
- Supply chain: GPG + SHA256 + CycloneDX SBOM + provenance (Q8); pinned locks; `pip-audit`/`npm audit` + SAST blocking.
- Error handling: no internals to clients; structured logs without sensitive data.

Risks tracked per milestone; M4 gate: malicious-input build stays jailed; M5: full review.
