# 0035 — Serving phase: published builds, visibility, URLs, and E2 headers

- **Status:** accepted and implemented
- **Decided:** 2026-10-24 (owner approved the serving forks A2/B3/C1/D1/E2)
- **Amended:** 2026-10-28 by 0036 — D1's immutable-public-name clause is
  superseded by owner-renamable names with permanent aliases/tombstones.
  The URL shape and all other rulings are unchanged.
- **Scope:** serving published Sphinx artifacts over HTTP. Page-level URL
  aliases, remote distribution, and the React shell format remain later
  phases.

## Owner rulings

| Fork | Ruling |
|---|---|
| A2 — what is served | Owner-published, immutable numbered builds. Two publication pointers: `latest` and `stable`; publish to one or both. Unpublishing clears a pointer but never revokes numbered history, so rollback/stable links survive. |
| B3 — visibility | Per-Athenaeum public toggle, **private by default**. Private sites allow the owner or any member of a grimoire in the Athenaeum; everyone else gets the uniform `404`. Public sites are open to anonymous readers. |
| C1 — mechanics | FastAPI serves the artifact files directly. No nginx alias is required for v1; the same app-side route is the local/CI proof. |
| D1 — URLs | `/a/{public_slug}/` (channel root), `/a/{public_slug}/latest/…`, `/a/{public_slug}/stable/…`, and immutable `/a/{public_slug}/b/{number}/…`. The public name is a globally unique slug separate from the per-owner editor slug. **Amended by 0036:** the owner may rename it; old names become permanent aliases. |
| E2 — host security + skin | Strict CSP built from the artifact manifest's inline-script hashes, `style-src 'self'` only, no inline styles/event handlers, and a bounded/namespaced custom-CSS input materialized as an external file at build time. |

## URL and publication semantics

- **Public slug:** generated once from the editor slug. A globally free
  name keeps the slug; a collision gets an 8-hex suffix (migration backfill
  uses the full UUID). Renaming the editor slug never changes the public
  URL. **Amended by 0036:** the owner may rename the public name through
  its own endpoint; old names remain permanent aliases and are never
  reused after deletion.
- **Channel roots:** `/a/{public_slug}/` redirects `307` to `latest` when
  that pointer has a servable build, otherwise to `stable`; with neither
  pointer it is `404`.
- **Pointer aliases:** `latest`/`stable` are publication-pointer aliases and
  are served with `Cache-Control: no-cache`. They resolve to an `ok`,
  manifest-backed build. (Public-name aliases are added by 0036 and use
  permanent `308` redirects.)
- **Numbered builds:** `/b/{number}/` is addressable only after that build
  was published at least once (`builds.published_at` is set). It is served
  with a one-year immutable cache. Unpublishing does not revoke it.
- **Publishing:** owner-only; a build must be `ok` and have a valid
  manifest, otherwise `409`. Publishing records the first `published_at`
  and `published_by`, sets the requested pointer(s), and audits the action.
- **Visibility changes:** owner-only `PATCH /athenaeums/{id}` with
  `is_public`. Public/private affects access and cache headers, not the
  immutable artifact.

## Access model

- Private site: no/invalid credential → uniform `404`; owner or any member
  of a grimoire in the Athenaeum → allowed. Members do not need a
  grimoire-scoped role beyond membership for read access.
- Public site: anonymous allowed; an invalid credential is simply treated
  as anonymous.
- Browser navigation cannot attach a bearer header, so login/refresh also
  set a 15-minute `scriptorium_access` cookie: `HttpOnly`, `SameSite=Lax`,
  path `/a`, `Secure` in production. API routes keep bearer auth.
- Private responses (including canonical redirects) carry
  `private, no-store`, `Vary: Cookie`, and `X-Robots-Tag: noindex,
  nofollow`. Public alias responses are `no-cache`; public numbered
  builds are immutable. Redirects use relative `Location` targets, so a
  spoofed Host header cannot become an open redirect.

## Artifact manifest and E2 headers

Every successful build writes `manifest.json` beside `html/`:

- format/version, Athenaeum/build identity, site id, entrypoint, timestamp;
- sorted file inventory with SHA-256 and byte counts;
- hashes of every non-empty inline `<script>` body;
- custom-CSS path/hash when present.

A build is not servable without a valid manifest. The manifest is portable:
an exported artifact can carry it to nginx/S3/any static host as the
authoritative inventory/CSP input. The theme must remain free of inline
`style` attributes, inline event handlers, and `<style>` blocks; the
manifest fails the build otherwise.

The serving policy is:

```
default-src 'none'; script-src 'self' <exact inline-script hashes>;
script-src-attr 'none'; style-src 'self'; style-src-attr 'none';
img-src 'self' data:; font-src 'self'; connect-src 'self';
media-src 'self'; object-src 'none'; frame-ancestors 'none';
base-uri 'none'; form-action 'self'; worker-src 'none'
```

Plus `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
`Permissions-Policy`, `X-Frame-Options: DENY`, and same-origin
`Cross-Origin-*-Policy` headers. No `'unsafe-inline'` and no network
origins are allowed.

## Custom CSS sandbox

The owner edits custom CSS through the platform (`GET/PUT/DELETE
/api/v1/athenaeums/{id}/custom-css`), never by editing generated files.
The input and the normalized artifact file are capped at 64 KiB of UTF-8; normalization happens at save time:

- every selector is rewritten under `html[data-sd-athenaeum]`; `:root` and
  `html` become the marked root;
- flat rules only — no at-rules (including `@media`), nesting, comments
  tricks, or backslash escapes;
- no `url()`, `image-set()`, `data:`, `@import`, remote fonts/images, or
  any network fetch;
- no `expression()`, `behavior`, `-moz-binding`, or other script-ish CSS;
- no `position: fixed` overlay escape;
- no `<`/HTML injection into the generated stylesheet.

The normalized CSS is written to `_static/custom.css`, linked by Sphinx as
an external stylesheet, and hashed in the manifest. A CSS change requires a
new build; existing artifacts are immutable. Deleting the input does not
mutate published builds.

## Schema and migration 0007

Adds `athenaeums.public_slug` (unique, NOT NULL), `is_public` (default
false), `custom_css` (default empty), `latest_build_id`/`stable_build_id`
(FK builds, `SET NULL`), and `builds.published_at`/`published_by` (FK
users, `SET NULL`). Backfill is deterministic: unique editor slugs keep
their value; duplicate slugs get the full-UUID suffix, with a numeric
suffix only if a user-chosen slug already occupies that generated name. Migration 0007 is
append-only; downgrade mirrors the additions.

## Disclosures and limits

- Public numbered builds are intentionally immutable-cached. If an owner
  later makes a site private, already-cached copies at public numbered URLs
  are outside the server's control; the owner should treat publication as
  a disclosure. Alias/private responses are not cacheable.
- `public_slug` allocation is check-then-insert; a concurrent collision is
  rejected by the unique constraint and returns a clean `409` (not silently
  duplicated, not a 500). The public name was immutable in 0035; 0036 adds
  owner renames, permanent aliases, and tombstones without changing the URL
  shape.
- Custom CSS cannot use at-rules, so media queries are unavailable in the
  custom layer; the shipped theme's own responsive rules are unaffected.
- No custom JavaScript, template overrides, remote assets, or per-site
  brand settings beyond the CSS hook are accepted in this phase.
- Page-level URL aliases and distribution targets remain later phases;
  0036 supplies site-level public-name aliases. Numbered build URLs remain
  the stable base those later phases build on.
- The editorial app keeps its own CSP; E2 applies to the published/served
  artifact and the exported artifact.

## Verification

- Unit: CSS namespacing/refusal matrix, manifest inventory/hashes,
  inline-style/event/`<style>` refusal, CSP construction, cache headers,
  path traversal.
- Live: public/private serving, owner/member/outsider access, bearer and
  `/a` cookie, latest/stable/numbered routes, publish/unpublish/rollback,
  custom CSS build-bound behavior, directory redirects, missing/traversal
  paths, manifest gate.
- Build/theme: custom CSS external link, `data-sd-athenaeum` marker, no
  inline `style=`, manifest custom-CSS hash; existing approved search,
  placeholders, pager, panel state, code labels, and zero-network behavior
  remain pinned by the theme tests.
- Browser: served page with CSP, custom CSS, panel placeholder `Search`,
  dialog `Search the library`, search results, private cookie access, and
  private cache/robots headers verified in headless Chrome.
- Gates: `ruff`, `ruff format --check`, `mypy --strict`, `pytest -W error`;
  migration round-trip; CI green after push.
