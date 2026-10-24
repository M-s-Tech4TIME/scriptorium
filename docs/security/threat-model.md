# Threat model (initial, Q22 / §10)

Last updated: 2026-10-24 / Ref: M4-C4 packaging contract

## Primary risk: untrusted content → Sphinx code exec
- Generated-only `conf.py`; extension allowlist (any addition = Rule 4 + record).
- Isolated build venv (M4-C4: 27-pin engine-only lock, `--no-deps`, app-dep
  absence asserted; `/opt/scriptorium/build-venv`); sandbox:
  `NoNewPrivileges`, `PrivateTmp`, CPU/mem/time limits, per-job temp dir;
  single-build-per-project; timeouts. Egress isolation is by construction
  of the pinned stack (no credentials/proxy in the whitelisted env), not
  a kernel namespace — disclosed P3 limitation.
- No remote fetch at build; link-check opt-in with allowlist (SSRF guard).
- Package install: `config.env` seeded 0600 only when absent; `postinst`
  never migrates or fetches; worker/web `Requires=redis.service`.

## App risks → mitigations
- XSS (built HTML + editor): output encoding, CSP `default-src 'self'`, SVG sanitize, upload allowlist + size caps.
- Path traversal: slug allowlist `[a-z0-9-]+`, jail to project dir, no `..`.
- IDOR/tenancy: membership check on every project request + tests (M1 gate).
- Auth: Argon2id, lockout, short JWT + rotating refresh (HttpOnly/Secure/SameSite), audit log.
- Secrets: env/file 0600 only; gitleaks blocking; none in repo/brain/logs.
- DoS: queue limits, rate limits, artifact quotas; journald + `/var/log/scriptorium`.
- Supply chain: GPG + SHA256 + CycloneDX SBOM + provenance (Q8); pinned locks; `pip-audit`/`npm audit` + SAST blocking.
- Error handling: no internals to clients; structured logs without sensitive data.

Risks tracked per milestone; M4 gate: malicious-input build stays jailed; M5: full review.
