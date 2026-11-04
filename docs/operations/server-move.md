# Operations — server move and first-run provisioning (decision 0040)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS tranche

This runbook takes a fresh host from package install to a working
Scriptorium instance, and moves an existing Athenaeum to it with its
public name and numbered `/b/{n}/` URLs preserved. It implements the
owner-approved rulings A1/B1/C1/D2/E1/G1/H1/I1/J2/K1/L1 and the built-in
TLS contract F-A1…F-L1 (decision 0040).

## Scope and fidelity

- The supported move unit is **one Athenaeum per 0039 archive**. Repeat
  export/restore for each site on a multi-Athenaeum instance.
- A move is **content-only**: users, memberships, refresh tokens, and
  audit rows are never exported. The importer owns every restored site;
  memberships are re-granted through the existing API after the move.
  There is no owner-transfer endpoint.
- `Full` mode is the move archive: it adds failed builds, logs, and
  artifacts for every successful build to the Editorial contents. Both
  modes preserve every ever-published successful build and its numbered
  URL.
- Global public-name tombstones for **deleted** Athenaeums are not carried
  by a per-site archive. If that full-fidelity case matters, use the
  ops-only raw `pg_dump` + filesystem copy fallback below, not the
  supported CLI move.
- The move is a **maintenance-window** cutover (G1). Zero-downtime,
  replication, dual-write, and live migration are out of scope.

## Prerequisites

- Target host: supported distro, PostgreSQL 18.6 reachable, the
  Scriptorium package installed, and the same or newer package version
  than the source. Downgrades are unsupported.
- Free disk for the archive, extracted payload, restored media, and
  artifacts. Check `df -h` on both hosts.
- The archive is a secret: it contains all content and media. Transfer it
  over SSH/HTTPS, keep it `0600`, and delete temporary copies after
  verification.
- Lower DNS TTL at least 24 hours before cutover.
- Decide the TLS strategy for the new host:
  - **New local CA (recommended for host separation):** generate on the
    new host and re-trust the new CA on clients once.
  - **Import an external certificate:** use the organisation's existing
    certificate for the hostname.
  - **Reuse the old local CA:** copy `/etc/scriptorium/tls` as a root
    secret so clients keep the existing trust anchor. This requires
    securely transferring `ca.key`; treat it as a root-only secret.
- Generate a **new** `SECRET_KEY` on the new host (H1). Do not copy the
  old key; refresh tokens are not exported and users re-authenticate.

## A. First-run on the new host

Perform these steps before starting the web tier.

1. **Install and configure.**

   ```bash
   sudo apt install ./scriptorium_<version>_amd64.deb   # or the RPM
   sudoedit /etc/scriptorium/config.env
   ```

   Set at least:

   ```ini
   DATABASE_URL=postgresql+asyncpg://scriptorium:…@127.0.0.1:5432/scriptorium
   SECRET_KEY=<fresh 48-byte URL-safe token>
   SCRIPTORIUM_COOKIE_SECURE=true
   SC_TLS_BIND=0.0.0.0:443
   SC_HTTP_HOST=0.0.0.0
   SC_HTTP_PORT=80
   SC_TLS_ROOT=/etc/scriptorium/tls
   ```

   Keep `config.env` `0600 scriptorium:scriptorium`. The CLI and services
   read it through the same no-shell-evaluation loader; environment
   variables win over file values.

2. **Issue TLS before enabling the web unit.**

   ```bash
   # Generated local CA + leaf (first generate needs root for ca.key):
   sudo scriptorium-admin tls generate --hostname docs.example.com

   # Or import an existing PEM pair:
   sudo scriptorium-admin tls import --cert /root/fullchain.pem --key /root/privkey.pem

   sudo scriptorium-admin tls verify
   ```

3. **Preflight.**

   ```bash
   sudo scriptorium-admin setup
   ```

   `setup` is read-only. It checks the config file, `SECRET_KEY`, database
   reachability and PG18, Alembic head/pending, writable artifact/media/
   build/backup roots, the build Python, and TLS status. It prints the next
   commands and exits non-zero if the host is not ready.

4. **Migrate.**

   ```bash
   sudo scriptorium-admin migrate
   ```

   `migrate` refuses PostgreSQL below 18 and applies idempotent Alembic
   upgrades. `postinst` never touches the database.

5. **Create the first account.**

   ```bash
   sudo scriptorium-admin user create \
     --email owner@example.com --display "Owner"
   # Automation:
   printf '%s\n' "$PASSWORD" | sudo scriptorium-admin user create \
     --email owner@example.com --display "Owner" --password-stdin
   ```

   Passwords are never accepted as argv. The policy is 12–1024 characters,
   no composition rules; hashes are Argon2id. `user list` shows id, email,
   and display only.

6. **Restore content before starting services (move only).** See section C.
   For a brand-new instance, skip to section D and create the first
   Athenaeum after login.

## B. Freeze and export on the old host

1. **Preflight.** Confirm the archive format version, free disk, a recent
   PostgreSQL backup, and that the old host is healthy.

2. **Freeze writes.**

   ```bash
   sudo systemctl stop scriptorium-web scriptorium-worker
   ```

   Keep PostgreSQL and Redis running for the export. No builds, uploads,
   or document saves can occur while the web/worker units are stopped.

3. **Export with the CLI (no web/worker/Redis/Celery required).**

   ```bash
   sudo scriptorium-admin backup export \
     --athenaeum <UUID-or-current-public-name> \
     --mode full --format tar.gz \
     --output /var/lib/scriptorium/backups/incoming/
   ```

   The command prints the archive path, byte size, and SHA-256. Use
   `--format zip` if preferred; restore auto-detects the container. The
   CLI shares the 0039 export core with the API, so the archive is
   byte-compatible with the existing restore path.

   The API/UI path remains available while the web tier is running, but the
   CLI is the recommended move path because it has no 8 GiB upload/proxy
   limit and no dependency on Redis or Celery.

4. **Record integrity data.**

   ```bash
   sha256sum /var/lib/scriptorium/backups/incoming/scriptorium-*.tar.gz \
     | tee /root/move.sha256
   ```

5. **Transfer.**

   ```bash
   scp /var/lib/scriptorium/backups/incoming/scriptorium-*.tar.gz \
     new-host:/var/lib/scriptorium/backups/incoming/
   scp /root/move.sha256 new-host:/root/move.sha256
   ```

   On the new host, verify before restoring:

   ```bash
   cd /var/lib/scriptorium/backups/incoming
   sha256sum -c /root/move.sha256
   chmod 0600 scriptorium-*.tar.gz
   ```

## C. Restore on the new host

The web/worker units must stay stopped until the restore and verification
finish.

1. **Confirm the target is empty.** The CLI refuses if any Athenaeum
   already exists unless `--force` is passed (K1). `--force` bypasses only
   this empty-target guard; it does **not** relax public-name strictness.

2. **Restore as the importer.**

   ```bash
   sudo scriptorium-admin restore \
     --archive /var/lib/scriptorium/backups/incoming/scriptorium-….tar.gz \
     --owner-email owner@example.com
   ```

   The owner email must already exist (`user create` above). The restore:

   - validates the whole manifest/inventory/hashes/sizes before any write;
   - creates a fresh Athenaeum owned by the importer;
   - preserves every imported build number, `latest`/`stable` pointer, and
     numbered `/b/{n}/` URL;
   - rewrites media URLs to the new asset UUIDs and re-homes artifacts
     under `{SC_ARTIFACT_ROOT}/{new_athenaeum_id}/{n}/`;
   - nulls unmatched user references (the importer owns the site);
   - uses **strict names** (I1): a current name or alias that conflicts
     with another live site or another owner's tombstone fails the restore
     instead of being auto-suffixed or silently dropped.

   If a name conflict is reported, resolve it deliberately: rename or
   retire the conflicting name on the target, or use the API owner-restore
   path (which keeps 0039 E1 auto-suffix behaviour) when a changed URL is
   acceptable. Do not use `--force` to paper over a name conflict.

3. **Inspect the result.** The command prints the new Athenaeum UUID, title,
   public name, mode, and any warnings. Warnings are not errors; read them.

## D. Verify before cutover

Run the automated checks:

```bash
sudo scriptorium-admin verify
sudo scriptorium-admin tls verify
```

`verify` is read-only and exits non-zero on errors. It checks:

- config file and `SECRET_KEY`;
- PostgreSQL 18+ and Alembic head;
- every Athenaeum has a matching current `public_names` row;
- `latest`/`stable` pointers reference builds of the same Athenaeum;
- artifact directories exist, stay inside the artifact root, and carry a
  valid manifest with the matching build number;
- every media row has a file whose size and SHA-256 match;
- TLS is configured and its material validates.

Then complete the manual checklist:

- [ ] Log in as the owner; the dashboard lists the restored Athenaeum.
- [ ] The current public URL works: `/a/{public_slug}/`.
- [ ] Every historical alias redirects (`308`) to the current name.
- [ ] `/a/{public_slug}/b/{n}/` serves the same numbered build as the old
      host; compare a known page and asset byte-for-byte if possible.
- [ ] `latest` and `stable` resolve to the expected builds.
- [ ] Media renders from `/_static/media/…`; spot-check a large image.
- [ ] Custom CSS, private/public visibility, and member access behave as
      before.
- [ ] Search and internal links work in the restored artifact.
- [ ] Build manifests are present and the build log (Full mode) is
      readable.
- [ ] Counts in the UI match the source (categories, grimoires, folios,
      documents, media, builds).
- [ ] `http://…` redirects to `https://…` with path and query preserved.
- [ ] `openssl s_client` shows TLS 1.2/1.3 and the expected certificate
      fingerprint.

## E. Cutover

1. Start the services:

   ```bash
   sudo systemctl enable --now scriptorium-redis scriptorium-redirect \
     scriptorium-web scriptorium-worker
   sudo systemctl enable --now scriptorium-tls-renew.timer
   ```

2. Point DNS at the new host.
3. Monitor `journalctl -u scriptorium-web -u scriptorium-worker -u
   scriptorium-redirect`, the login flow, a build, and a media read.
4. Enable HSTS only after clients trust the new CA:

   ```bash
   sudo scriptorium-admin tls hsts on
   ```

## F. Rollback

The old host is untouched after the freeze and remains the rollback
target.

1. Point DNS back to the old host.
2. Restart its web/worker units.
3. Keep the old PostgreSQL data and filesystem intact.

Writes made on the new host after cutover are lost on rollback. Record the
cutover time and the accepted data-loss window before starting. Do not
decommission the old host until that window has passed and the owner signs
off.

## G. Decommission

After the agreed rollback window:

1. Take a final backup if the new host is authoritative.
2. Destroy the old host and its temporary archive copies.
3. Delete transfer staging and `/root/move.sha256` on both hosts.
4. If the old local CA was reused, keep its `ca.key` only where the new
   host needs it; otherwise retire it.

## Multi-Athenaeum moves

Repeat sections B–C once per Athenaeum. Every restored site is owned by
the importer; re-grant memberships through the API. Former owners either
become members of the importer's site or are recreated as users and
re-granted access. There is no owner-transfer endpoint in V1.

## Ops-only full-fidelity fallback

If the move must preserve users, memberships, audit rows, or tombstones
for deleted Athenaeums, use a raw PostgreSQL dump plus a filesystem copy.
This is **not** the supported move path:

```bash
# Old host, writes stopped:
pg_dump -Fc -d scriptorium -f /root/scriptorium.dump
rsync -a /var/lib/scriptorium/ /backup/scriptorium-data/

# New host, same PG major, empty database:
pg_restore -d scriptorium /root/scriptorium.dump
rsync -a /backup/scriptorium-data/ /var/lib/scriptorium/
```

It bypasses the archive validation, is version-coupled, and requires the
same package/schema generation. Restore the database before starting the
app, run `scriptorium-admin migrate` only if the package is newer, then
`scriptorium-admin verify`. Treat the dump as a root secret.

## Security checklist

- [ ] `config.env` is `0600 scriptorium:scriptorium`.
- [ ] `ca.key` is `root:root 0600`; the TLS root is
      `scriptorium:scriptorium`.
- [ ] The archive was transferred over SSH/HTTPS, checked against its
      SHA-256, and deleted after verification.
- [ ] `SECRET_KEY` is new and unique to the host.
- [ ] No plaintext HTTP application listener exists; port 80 only
      redirects.
- [ ] Uvicorn proxy headers are disabled; no untrusted proxy sits in
      front.
- [ ] HSTS stays off until the CA is trusted.
- [ ] The old host is preserved for rollback and its credentials are
      rotated/retired after decommission.

## Troubleshooting

| Symptom | Action |
|---|---|
| `setup` says database revision is behind head | Run `scriptorium-admin migrate`. |
| `setup` says TLS is not configured | Run `tls generate` or `tls import` before enabling web. |
| `restore` refuses because the target has Athenaeums | Use a genuinely empty target; `--force` is only for an intentional additive restore. |
| `restore` fails with a public-name conflict | Resolve the name on the target deliberately; strict move mode never renames a URL. |
| `restore` says the owner email does not exist | Create the importer with `user create` first. |
| `verify` reports a missing artifact or media hash mismatch | Re-transfer/re-export; do not cut over. |
| `scriptorium-web` will not start | Check the certificate paths and `systemctl status`; the worker refuses to run without `--certfile`/`--keyfile`. |
| HTTP redirect returns 400 | The request Host is not a certificate SAN and no fallback host is configured; set `SC_TLS_REDIRECT_HOST`. |

## Acceptance

- A clean host reaches first login using only documented commands.
- A Full archive restores into an empty target with the same current
  public name, aliases, numbered `/b/{n}/` URLs, `latest`/`stable`
  pointers, media, custom CSS, and private/public state.
- `verify` passes before cutover.
- Rollback returns traffic to the untouched old host.
- No 0039 API/archive behaviour regresses; CLI move uses strict names while
  the API owner restore keeps auto-suffix.
