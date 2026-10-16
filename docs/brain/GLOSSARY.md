# GLOSSARY

Last updated: 2026-10-16 / Ref: uncommitted (M0 seed)

- **Node:** generic ordered-tree row (`nodes` table, kind `category|page`) driving TOC/`toctree`.
- **Document:** editor content for a page-node; canonical `tiptap_json` (`tiptap@1`), derived `source_text`.
- **Source format:** per-project `rst` (default) or `myst`; export target, not canonical.
- **Build:** queued Sphinx job (`builds` row) producing versioned HTML artifact from generated sources.
- **Allowlist:** owner-approved suppression/exception with scope + expiry + decision ref (Rule 6).
- **Gate:** blocking CI check; failing gate blocks merge/push completion.
