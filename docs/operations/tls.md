# Operations — built-in TLS (decision 0040)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS tranche

Scriptorium terminates HTTPS itself. There is no reverse proxy in the V1
contract and no plaintext application listener: Gunicorn/Uvicorn serves the
app on `SC_TLS_BIND` (default `0.0.0.0:443`) with a hardened TLS context,
and a separate tiny service answers HTTP on port 80 with a `308` redirect
to HTTPS. This page is the operator runbook for the whole certificate
lifecycle.

## At a glance

| Item | Value |
|---|---|
| HTTPS listener | `scriptorium-web.service` → `app.tls.worker.TlsUvicornWorker` |
| HTTP listener | `scriptorium-redirect.service` → `app.tls.redirect:app` |
| Default binds | `SC_TLS_BIND=0.0.0.0:443`, `SC_HTTP_HOST=0.0.0.0`, `SC_HTTP_PORT=80` |
| Privileged ports | `CAP_NET_BIND_SERVICE` on both units; no root process |
| TLS root | `SC_TLS_ROOT` (default `/etc/scriptorium/tls`) |
| Active certificate | `$SC_TLS_ROOT/current/fullchain.pem` |
| Active private key | `$SC_TLS_ROOT/current/privkey.pem` |
| Local CA certificate | `$SC_TLS_ROOT/ca.pem` |
| Local CA private key | `$SC_TLS_ROOT/ca.key` — `root:root 0600` |
| Renewal | daily timer; renews at 30 days remaining |
| Retention | last 5 versions (current + newest protected) |
| HSTS | off by default; no preload |

## File layout and ownership

```text
/etc/scriptorium/tls/
├── ca.pem                 # local CA certificate, 0644 scriptorium:scriptorium
├── ca.key                 # local CA private key, 0600 root:root (O1 exception)
├── state.json             # active mode/version/HSTS, 0644
├── current -> versions/<version-id>
└── versions/
    └── <UTC-microseconds>-<8 hex>/
        ├── fullchain.pem  # leaf first, then the local CA, 0644
        ├── privkey.pem    # leaf private key, 0600
        └── meta.json      # mode, SANs, dates, SHA-256 fingerprint
```

Every Scriptorium-managed path is `scriptorium:scriptorium` except the CA
private key. The accepted ownership exceptions are the systemd unit files
and package metadata (root-owned), the external PostgreSQL data directory
(`postgres`), and `ca.key` (`root:root 0600`). `postinst` applies the
recursive ownership and then forces `ca.key` back to root.

## Cryptographic profile

Generated material follows the owner-approved F-B1/F-E1 profile:

- **Local CA:** ECDSA P-384, SHA-384, 10-year lifetime, CA path length 0,
  key usage `keyCertSign`/`cRLSign`.
- **Leaf:** ECDSA P-256, SHA-256, 90-day lifetime, `serverAuth` EKU,
  DNS/IP subject alternative names.
- **Protocols:** TLS 1.2 minimum, TLS 1.3 enabled.
- **TLS 1.2 suites:** ECDHE + AEAD only —
  `ECDHE-ECDSA-AES256-GCM-SHA384`, `ECDHE-RSA-AES256-GCM-SHA384`,
  `ECDHE-ECDSA-CHACHA20-POLY1305`, `ECDHE-RSA-CHACHA20-POLY1305`,
  `ECDHE-ECDSA-AES128-GCM-SHA256`, `ECDHE-RSA-AES128-GCM-SHA256`.
  The RSA suites exist for imported RSA certificates; RSA **key exchange**
  is never enabled.
- **Forbidden:** CBC, RSA key exchange, 3DES, RC4, NULL ciphers,
  compression, renegotiation, and session tickets (TLS 1.3 tickets
  disabled with `num_tickets=0`).
- **Hashes:** SHA-256 or stronger for certificate signatures.

Imported material is checked against the same strength rules before it is
installed.

## Subject alternative names

`tls generate` auto-detects `localhost`, the machine hostname/FQDN, their
resolved addresses, `127.0.0.1`, and `::1`. Add public names explicitly:

```bash
sudo scriptorium-admin tls generate \
  --hostname docs.example.com \
  --url https://www.example.com/docs \
  --san IP:192.0.2.10
```

- `--hostname` accepts a DNS name or IP.
- `--url` extracts the host from a URL (credentials are rejected).
- `--san` accepts `DNS:name`, `IP:addr`, or a bare name/address.
- DNS names are lowercased and IDNA-normalized; trailing dots are removed.
- IPv6 is normalized; brackets are accepted.
- A wildcard is allowed only as the leftmost label (`*.example.com`), and
  only when it has at least two labels.

Renewal reuses the SANs recorded on the active certificate, so changing a
hostname requires a fresh `tls generate` with the new names (or importing a
certificate that contains them).

## First run: generated certificate

```bash
# 1. Generate the CA (first time only) and leaf, activate, reload web.
sudo scriptorium-admin tls generate --hostname docs.example.com

# 2. Inspect what was installed.
sudo scriptorium-admin tls status
sudo scriptorium-admin tls verify

# 3. Export the CA certificate and trust it once on client devices.
sudo scriptorium-admin tls ca --export /tmp/scriptorium-ca.pem
```

The first `tls generate` creates the CA private key. That step requires
root because the key is `root:root 0600`. Renewal also needs the CA
private key to sign the new leaf, so the packaged timer runs as root;
the `scriptorium` account cannot read `ca.key` and cannot renew a
default-root generated certificate. A non-default `SC_TLS_ROOT` used for
tests/staging can be renewed unprivileged because its key ownership and
mode are local to that tree.

Trust the exported `ca.pem` in the OS/browser trust store of every client
that should see a trusted padlock. Trusting the CA once covers every leaf
issued by it; renewals do not require re-trusting anything.

If `scriptorium-web` is running, activation performs a graceful reload and
checks the live service. If the reload fails, the previous certificate and
state are restored automatically and the command exits non-zero.

## Importing an external certificate

Use PEM files: the full chain with the leaf certificate first, and the
matching unencrypted private key (PKCS#8 or traditional PEM).

```bash
sudo scriptorium-admin tls import \
  --cert /path/to/fullchain.pem \
  --key /path/to/privkey.pem
```

Before installation, the CLI validates:

- certificate and key are valid PEM and the key is unencrypted;
- the leaf is currently valid and not a CA certificate;
- RSA keys are at least 2048 bits; ECDSA keys are at least P-256;
- the private key matches the leaf public key;
- the leaf signature uses SHA-256 or stronger;
- the leaf has the `serverAuth` EKU and at least one DNS/IP SAN;
- every certificate in the supplied chain is directly issued by the next.

The pair is written to a new version directory, activated atomically, and
the web service is gracefully reloaded. A failed reload restores the
previous version. **Imported certificates are never auto-renewed**;
`tls renew` reports that and exits successfully without changing anything.
Replace them with a new `tls import` before expiry.

Trust for an imported chain is the operator's responsibility: the CLI
validates the chain's internal links, but it does not add an external root
to the system trust store.

## Renewal, history, rollback, and pruning

```bash
sudo scriptorium-admin tls renew            # renew only if <= 30 days remain
sudo scriptorium-admin tls renew --force    # renew now (generated mode)
sudo scriptorium-admin tls history          # newest first; * = active
sudo scriptorium-admin tls rollback         # activate the previous version
sudo scriptorium-admin tls rollback VERSION # activate a specific version
sudo scriptorium-admin tls prune --keep 5   # delete older retained versions
```

- `scriptorium-tls-renew.timer` runs daily with a randomized delay. It
  invokes `scriptorium-admin tls renew` as root.
- Renewal creates a new leaf under the same CA and SAN set, activates it,
  reloads the web service, and prunes to the newest 5 versions.
- `prune` always protects the active version and the newest `--keep`
  versions; it never removes the certificate currently in use.
- Rollback validates the chosen version before activating it and uses the
  same reload/rollback safety as generate/import.
- Version IDs include UTC microseconds, so history ordering is stable even
  when two operations happen in the same second.

## HSTS

HSTS is **off by default** and has no preload. Enable it only after the CA
is trusted by clients, otherwise browsers will pin an untrusted HTTPS
endpoint:

```bash
sudo scriptorium-admin tls hsts on
sudo scriptorium-admin tls hsts on --max-age 31536000
sudo scriptorium-admin tls hsts off
```

`tls hsts` writes the state file, reloads `scriptorium-web`, and reverts
the state if the reload fails. The middleware adds
`Strict-Transport-Security: max-age=<n>` only to HTTPS responses. The
default max-age is one year; the optional `SC_TLS_HSTS_MAX_AGE` config key
sets the value used when `--max-age` is omitted. A non-positive max-age is
rejected.

## HTTP → HTTPS redirect

`scriptorium-redirect.service` runs `app.tls.redirect:app` on port 80 and
returns `308 Permanent Redirect` for every HTTP request, preserving the
path and query string.

The `Host` header is attacker-controlled, so it is used only when it
matches a SAN on the active certificate. Otherwise the redirect falls back
to `SC_TLS_REDIRECT_HOST` (if configured) or the first non-wildcard DNS SAN
on the certificate. If no safe host can be determined, the redirect
service returns a plain `400` instead of reflecting an untrusted host.

```ini
# /etc/scriptorium/config.env
SC_TLS_REDIRECT_HOST=docs.example.com
```

## CLI reference

| Command | Purpose |
|---|---|
| `tls generate [--hostname H] [--url U] [--san S] [--no-reload]` | Create the CA if needed, issue a leaf, activate it |
| `tls renew [--force] [--no-reload]` | Renew a generated certificate at/under 30 days (or force) |
| `tls import --cert PEM --key PEM [--no-reload]` | Validate and install an external pair |
| `tls rollback [VERSION] [--no-reload]` | Reactivate an older version |
| `tls prune [--keep N]` | Delete old versions, protecting active + newest N |
| `tls history [--json]` | List retained versions |
| `tls status [--json]` | Show mode, dates, SANs, fingerprint, HSTS, warnings |
| `tls verify [--json]` | Validate files, modes, chain, expiry, CA key ownership |
| `tls hsts on\|off [--max-age N]` | Toggle HSTS and reload |
| `tls ca [--export PATH]` | Show/export the local CA certificate |

`--no-reload` installs without contacting systemd; it is intended for
offline tests and staging. Do not use it on a live host unless the web
service is stopped.

## Configuration keys

```ini
SC_TLS_BIND=0.0.0.0:443          # Gunicorn bind for HTTPS
SC_HTTP_HOST=0.0.0.0             # redirect listener bind
SC_HTTP_PORT=80
SC_TLS_ROOT=/etc/scriptorium/tls
# SC_TLS_CERT=/etc/scriptorium/tls/current/fullchain.pem
# SC_TLS_KEY=/etc/scriptorium/tls/current/privkey.pem
# SC_TLS_REDIRECT_HOST=docs.example.com
# SC_TLS_HSTS_MAX_AGE=31536000
```

`SC_TLS_CERT`/`SC_TLS_KEY` override the active paths only when an operator
deliberately points them elsewhere; the CLI still manages versions under
`SC_TLS_ROOT`. The shared config loader reads the file without shell
evaluation, and a real environment variable wins over the file (decision
0040 M1).

For IPv6, set an IPv6 bind explicitly, for example
`SC_TLS_BIND=[::]:443` and `SC_HTTP_HOST=::`. The default is IPv4.

## Verification checklist

```bash
# Installed files, permissions, chain, expiry, CA key ownership
sudo scriptorium-admin tls verify

# Full host preflight (config, DB, roots, build python, TLS)
sudo scriptorium-admin setup

# Post-move/health verification
sudo scriptorium-admin verify

# Protocol/cipher check
openssl s_client -connect docs.example.com:443 -servername docs.example.com \
  -tls1_2 </dev/null 2>/dev/null | grep -E 'Protocol|Cipher'

# Redirect check
curl -sSI http://docs.example.com/some/path?q=1 | grep -E 'HTTP/|Location'

# Fingerprint comparison
openssl x509 -in /etc/scriptorium/tls/current/fullchain.pem -noout -fingerprint -sha256
```

`tls verify` exits non-zero on errors. It warns when the certificate is
inside the 30-day renewal window and checks the CA key is `root:root 0600`
when run as root.

## Security notes

- The application never accepts plaintext HTTP; port 80 exists only for the
  redirect listener.
- Uvicorn proxy headers are disabled and `X-Forwarded-For` is untrusted.
  Rate limiting uses the socket peer address, so do not put an untrusted
  proxy in front of the app.
- The CA private key never leaves the host in normal operation and is
  readable only by root. Back it up as a root secret if the trust anchor
  must survive a host loss; otherwise generate a new CA and re-trust it.
- Private keys are `0600`; fullchains are `0644`; version directories are
  `0750`.
- Imported keys must be unencrypted because the service cannot prompt for a
  passphrase at boot. Protect the source files and delete temporary copies.
- HSTS is deliberately opt-in and has no preload. Enabling it before the CA
  is trusted can lock clients out of the site.

## Troubleshooting

| Symptom | Cause / action |
|---|---|
| `Creating the local CA requires root` | Run the first generate with `sudo`; the CA key is root-only. |
| `scriptorium-web` fails to start: certificate missing | Run `tls generate` or `tls import` before enabling the unit. |
| `scriptorium-web did not reload` | The previous version was restored; check `systemctl status scriptorium-web` and `journalctl -u scriptorium-web`. |
| Browser still shows an old certificate | Confirm `tls status` fingerprint, then hard-refresh/restart the browser; clients cache TLS sessions. |
| HTTP redirect goes to an unexpected host | Set `SC_TLS_REDIRECT_HOST`; the request Host is only honored when it matches a certificate SAN. |
| `tls renew` says imported certificates are never auto-renewed | Expected; import a replacement pair. |
| `tls verify` reports the CA key is not `root:root` | `chown root:root /etc/scriptorium/tls/ca.key && chmod 0600 …`; `postinst` enforces this on upgrade. |
| Certificate expires in <30 days but no renewal happened | Check `systemctl status scriptorium-tls-renew.timer` and the service journal; run `tls renew --force` to test. |

## Out of scope (V1)

No ACME/Let's Encrypt client, no reverse-proxy termination, no plaintext
application listener, no HSTS preload, and no automatic renewal of imported
certificates. Those are later decisions, not configuration gaps.
