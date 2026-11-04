# Technology — built-in TLS (cryptography 50.0.2 + uvicorn-worker 0.4.0)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

- **Versions (locked):** `cryptography==50.0.2`,
  `uvicorn-worker==0.4.0`; Python's standard `ssl` module and the OpenSSL
  it is built against. No new OS package: the bundled Python 3.14.10
  runtime supplies both.
- **Why:** Scriptorium V1 terminates HTTPS itself (F-A1). The app must
  generate a local trust anchor, issue short-lived leaves, validate
  imported PEM material, and install a hardened server context without an
  external reverse proxy. `cryptography` provides X.509 generation and
  validation; `uvicorn-worker` supplies the Gunicorn-compatible worker
  class the TLS worker extends.
- **Used:** `backend/app/tls/`:
  - `state.py` — TLS root paths, `state.json`, per-version `meta.json`,
    atomic writes, HSTS defaults;
  - `crypto.py` — CA/leaf generation, SAN normalization/detection,
    import validation, and `create_server_context`;
  - `manager.py` — lifecycle: generate, renew, import, rollback, prune,
    history, status, verify, HSTS, activation, reload/rollback;
  - `worker.py` — `TlsUvicornWorker`, the Gunicorn worker class;
  - `redirect.py` — HTTP→HTTPS `308` ASGI app;
  - `middleware.py` — HSTS response middleware.
- **CLI:** `scriptorium-admin tls …` wraps the manager; the daily
  `scriptorium-tls-renew.timer` runs `tls renew` as root.
- **Locks:** `backend/requirements.lock` (dev/test/full) and
  `backend/requirements.prod.lock` (runtime) are regenerated together;
  `packaging/scripts/build-app-venv.sh` installs only the prod lock.
- **Typing:** `uvicorn-worker` ships no `py.typed`, so
  `backend/typings/uvicorn_worker/__init__.pyi` is a local minimal stub and
  `backend/pyproject.toml` sets `mypy_path = "typings"`. This is a typing
  stub, not a runtime dependency or a suppression.

## Generated profile (F-B1)

| Material | Algorithm | Lifetime | Notes |
|---|---|---|---|
| Local CA | ECDSA P-384, SHA-384 | 10 years (3650 days) | `BasicConstraints(ca=True, path_length=0)`, `keyCertSign`/`cRLSign`, key `root:root 0600` |
| Leaf | ECDSA P-256, SHA-256 | 90 days | `BasicConstraints(ca=False)`, `serverAuth` EKU, DNS/IP SANs, key `0600` |

- Serial numbers are 128 random bits, never zero.
- Certificates are backdated five minutes to tolerate small clock skew.
- The full chain written to `fullchain.pem` is leaf first, then the local
  CA.
- The CA private key is the only Scriptorium-managed secret that is not
  `scriptorium:scriptorium`; it stays `root:root 0600` (O1).
- Trust the CA once; leaf renewal under the same CA needs no client
  re-trust.

## Imported material (F-F1)

`tls import --cert fullchain.pem --key privkey.pem` validates before
installation:

- valid PEM certificate chain and an unencrypted private key (PKCS#8 or
  traditional PEM);
- leaf currently valid, not a CA;
- RSA key ≥ 2048 bits, or ECDSA P-256 or stronger (Ed25519 keys are
  accepted by the PEM loader; the approved strength floor is P-256/RSA
  2048);
- private key matches the leaf public key;
- leaf signature hash is SHA-256 or stronger;
- `serverAuth` EKU and at least one DNS/IP SAN;
- each certificate in the supplied chain is directly issued by the next.

Imported certificates are never auto-renewed; `tls renew` reports that
and changes nothing. The external root is the operator's trust
responsibility — the CLI does not add it to the system store.

## Protocol and cipher policy (F-E1)

`create_server_context` builds a `ssl.SSLContext(PROTOCOL_TLS_SERVER)`:

- minimum TLS 1.2, maximum TLS 1.3;
- TLS 1.2 cipher list (ECDHE + AEAD only):
  - `ECDHE-ECDSA-AES256-GCM-SHA384`
  - `ECDHE-RSA-AES256-GCM-SHA384`
  - `ECDHE-ECDSA-CHACHA20-POLY1305`
  - `ECDHE-RSA-CHACHA20-POLY1305`
  - `ECDHE-ECDSA-AES128-GCM-SHA256`
  - `ECDHE-RSA-AES128-GCM-SHA256`
- `OP_NO_COMPRESSION`, `OP_NO_RENEGOTIATION`, `OP_NO_TICKET`,
  `OP_CIPHER_SERVER_PREFERENCE`;
- `post_handshake_auth = False`; `num_tickets = 0` (TLS 1.3 session
  tickets off);
- certificate chain loaded from the active `fullchain.pem`/`privkey.pem`.

Forbidden: CBC suites, RSA key exchange, 3DES, RC4, NULL ciphers,
compression, renegotiation, and session tickets. RSA suites remain only
for imported RSA certificates; RSA **key exchange** is never enabled.
SHA-256 or stronger is required for certificate signatures.

## Worker and listener contract

- `TlsUvicornWorker` subclasses `uvicorn_worker.UvicornWorker`; it
  requires Gunicorn `--certfile`/`--keyfile` and refuses to start without
  them. After the base worker initializes its Uvicorn config, the worker
  sets `ssl_context_factory` to `create_server_context`.
- Uvicorn proxy headers are disabled (`--no-proxy-headers`); the
  `X-Forwarded-For` header is untrusted (F-L1).
- `scriptorium-redirect.service` runs `app.tls.redirect:app` on port 80
  and returns `308` for every request. The `Host` header is honored only
  when it matches an active certificate SAN; otherwise the app falls back
  to `SC_TLS_REDIRECT_HOST`, then a certificate SAN, then `400`.
- Both listeners bind privileged ports through
  `CAP_NET_BIND_SERVICE`; the processes run as `scriptorium`, never root.

## Lifecycle and storage

```text
/etc/scriptorium/tls/
├── ca.pem                 # local CA certificate
├── ca.key                 # local CA private key, root:root 0600
├── state.json             # active mode/version/HSTS
├── current -> versions/<version-id>
└── versions/<UTC-microseconds>-<8 hex>/
    ├── fullchain.pem
    ├── privkey.pem
    └── meta.json
```

- Version IDs include UTC microseconds plus 8 random hex characters, so
  ordering is deterministic.
- Activation validates the version, writes the complete directory,
  swaps `current` and `state.json` atomically, then gracefully reloads
  `scriptorium-web`; a failed reload restores the previous symlink/state
  and exits non-zero.
- Renewal runs daily, renews at ≤ 30 days remaining, reuses the active
  certificate's SANs and CA, and prunes to the newest 5 versions while
  protecting the active one.
- `rollback` validates and activates an older version; `prune --keep N`
  never removes the active version.
- HSTS is off by default with no preload; `tls hsts on` writes state and
  reloads, reverting on failure. The middleware adds
  `Strict-Transport-Security: max-age=<n>` only to HTTPS responses.

## Verified

- Lock resolution 2026-11-04 (`cryptography 50.0.2`,
  `uvicorn-worker 0.4.0`).
- TLS lifecycle smoke test in `/tmp/opencode/tls-smoke`; unit and
  redirect regressions in `backend/tests/test_tls.py` and
  `test_tls_redirect.py`; packaging contract in `test_packaging.py`.
- Operator runbook: `docs/operations/tls.md`; decision 0040.
