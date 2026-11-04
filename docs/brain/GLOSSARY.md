# GLOSSARY

Last updated: 2026-11-04 / Ref: 0040 server move/first-run + built-in TLS

- **Athenaeum (Library):** one user's complete documentation project — the library layer (`athenaeums`, 0020).
- **Grimoire-category (Section):** a folder/section inside a Library grouping Grimoires (`grimoire_categories`, per-Athenaeum, 0020 Q-M3-9=A). **Single membership**: a Grimoire belongs to exactly one Section or Uncategorized; "same book on two shelves" is served by duplication (0022/0023 record), not shared membership.
- **Grimoire (Book):** one self-contained documentation set — a Sphinx project (`grimoires`, renamed from `projects` by 0018).
- **Chapter:** in-book ordered-tree folder node (`nodes.kind='chapter'`; renamed from 0010's `category` by 0022). Drives the `toctree`.
- **Folio:** in-book page/file node (`nodes.kind='folio'`; renamed from 0010's `page` by 0022) + its `documents` row; the actual `.rst`/`.md` materializes at build time — TipTap JSON stays canonical (0010/Q21).
- **Node:** ordered-tree row (`nodes` table, kind `chapter|folio`) driving TOC/`toctree`.
- **Document:** editor content for a folio; canonical `tiptap_json` (`tiptap@1`), derived `source_text` (Q-M3-3=A).
- **Source format:** per-Grimoire `rst` (default) or `myst`; export target, not canonical.
- **Build:** queued Sphinx job (`builds` row) producing a versioned, immutable HTML artifact + `manifest.json` from generated sources.
- **Publication pointer:** owner-selected `latest`/`stable` build reference on an Athenaeum; aliases resolve through it, while numbered builds stay immutable (0035 A2).
- **Public name (public slug):** globally unique URL name (`athenaeums.public_slug`) independent of the per-owner editor slug (0035 D1). The owner may rename it; the old value becomes a permanent alias (0036).
- **Public-name alias:** a retired `public_names` row that redirects `308` to the current canonical name after the current site's access check; never reused by another site (0036).
- **Public-name tombstone:** a `public_names` row left after Athenaeum deletion (`athenaeum_id NULL`); old URLs return `404` and the name can never be claimed again (0036).
- **Manifest:** `manifest.json` beside a build's `html/`, listing artifact inventory/SHA-256, inline-script CSP hashes, identity, and custom-CSS hash; the serving/export contract (0035 E2).
- **Custom CSS:** bounded, namespaced owner skin input materialized as external `_static/custom.css` at build time; no at-rules/remote assets/scripts (0035 E2).
- **TLS root:** `SC_TLS_ROOT` (default `/etc/scriptorium/tls`) holding `ca.pem`, `ca.key`, `state.json`, `current`, and versioned leaves (0040).
- **Local CA:** Scriptorium-generated ECDSA P-384 trust anchor (10 years); its private key is `root:root 0600`, the one app-path ownership exception (0040 O1/F-B1).
- **Leaf certificate:** ECDSA P-256 server certificate (90 days, `serverAuth`, DNS/IP SANs) issued by the local CA; `fullchain.pem` = leaf + CA (0040).
- **TLS version:** one immutable directory under `$SC_TLS_ROOT/versions/` containing `fullchain.pem`, `privkey.pem`, and `meta.json`; activation swaps `current` atomically (0040).
- **TLS mode:** `generated` (renewable by Scriptorium) or `imported` (validated external PEM; never auto-renewed) (0040 F-F1).
- **Strict move restore:** CLI restore mode that fails before writes on a live-name or another owner's tombstone conflict instead of suffixing; the API restore keeps 0039 auto-suffix (0040 I1).
- **Allowlist:** owner-approved suppression/exception with scope + expiry + decision ref (Rule 6).
- **Gate:** blocking CI check; failing gate blocks merge/push completion.
