# GLOSSARY

Last updated: 2026-10-21 / Ref: 0022 (folio/chapter) + 0020/0021

- **Athenaeum (Library):** one user's complete documentation project — the library layer (`athenaeums`, 0020).
- **Grimoire-category (Section):** a folder/section inside a Library grouping Grimoires (`grimoire_categories`, per-Athenaeum, 0020 Q-M3-9=A). **Single membership**: a Grimoire belongs to exactly one Section or Uncategorized; "same book on two shelves" is served by duplication (0022/0023 record), not shared membership.
- **Grimoire (Book):** one self-contained documentation set — a Sphinx project (`grimoires`, renamed from `projects` by 0018).
- **Chapter:** in-book ordered-tree folder node (`nodes.kind='chapter'`; renamed from 0010's `category` by 0022). Drives the `toctree`.
- **Folio:** in-book page/file node (`nodes.kind='folio'`; renamed from 0010's `page` by 0022) + its `documents` row; the actual `.rst`/`.md` materializes at build time — TipTap JSON stays canonical (0010/Q21).
- **Node:** ordered-tree row (`nodes` table, kind `chapter|folio`) driving TOC/`toctree`.
- **Document:** editor content for a folio; canonical `tiptap_json` (`tiptap@1`), derived `source_text` (Q-M3-3=A).
- **Source format:** per-Grimoire `rst` (default) or `myst`; export target, not canonical.
- **Build:** queued Sphinx job (`builds` row) producing versioned HTML artifact from generated sources.
- **Allowlist:** owner-approved suppression/exception with scope + expiry + decision ref (Rule 6).
- **Gate:** blocking CI check; failing gate blocks merge/push completion.
