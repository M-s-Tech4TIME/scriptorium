# Decision 0030 — theme typography: vendored Inter reading face

Status: accepted · 2026-10-23 · Owner: alsechemist (ruled in review of the
M4-C3.5 preview #2 typography sheet in chat; final fallback ruling delivered
2026-10-23)

## Ruling

1. **Mechanics = Option B, vendored webfont** (owner picked B from the
   presented A/B/C sheet): a self-hosted face inside the theme — still
   zero network (served from the artifact itself, same clause as the
   icon sprite; the consult's "no webfonts" intent is satisfied by
   vendoring, not by CDN absence).
2. **Face = Inter** — the owner ruled for a sans reading face
   ("Notion-like"). Notion's doc default is the OS system sans stack
   (SF/Segoe), which cannot be redistributed; Inter (SIL OFL 1.1,
   neutral grotesque, SF-metric kin) is the closest legal vendored
   match. Considered-and-noted: ABC Favorit (Notion's brand face) and
   SF Pro are Applicants-unredistributable/commercial — excluded.
3. **Scope = body + headings** (`--sd-font-body`; `--sd-font-heading`
   follows by token indirection). UI chrome stays the ruled system sans
   `--sd-font-ui`; code stays `--sd-font-mono`; reading scale stays
   17px / 1.65; the h1–h6 ladder stays. Reading color pairs untouched —
   AA rows unchanged.
4. **Fallback stack = the ruled UI sans stack** (owner ruled explicitly:
   "stick to the previous plan — fallback to the current sans stack")::
   `--sd-font-body: "Inter", system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;`
   Considered and **dropped by the owner** the same day: an
   RTD-faithful chain (`Lato, proxima-nova, …` — Lato is RTD's
   CDN-served face; dead weight on stock machines) and vendoring Lato
   as a true secondary. Simplicity ruled.
5. **Source = Google Fonts** (owner-directed): the variable faces were
   retrieved from `fonts.googleapis.com` (2026-10-23) — Inter v20
   instance, latin subset, ranges `ital,opsz,wght 0/1,14..32,100..900`.
   Files: `static/fonts/inter-latin.woff2` (72.5 KB, upright) and
   `inter-latin-italic.woff2` (79.7 KB, italic); byte-checked
   `Web Open Font Format v2`. The OFL 1.1 license text is vendored
   alongside (`OFL-Inter.txt`), NOTICE carries the attribution row.
   `@font-face` uses `font-display: swap` with `font-weight: 100 900`
   (variable) + matching italic face. Latin-only subset: the engine's
   default language is English; glyphs outside the subset transparently
   fall back to the ruled sans stack (a per-script vendoring would be a
   future owner ruling only).

## Effects

- `static/scriptorium.css`: `@font-face` pair + the owner-ruled
  `--sd-font-body` override lives in the 0029/0030 addendum `:root`
  block — the consult `:root` stays verbatim-matched with
  `references/tokens.css`; the reference file stays intentional-consult
  (the delta is documented here, per the "improvise, don't copy" clause
  in scriptorium-design-spec).
- `static/fonts/`: two woff2 faces + vendored OFL text.
- `NOTICE`: Inter attribution paragraph (Google Fonts source + date).
- Tests: materialization asserts the fonts directory (3 files);
  artifact `_static` inventory gains `fonts`, and physiology asserts
  `@font-face`, the file path and the override token. Suite stayed
  `76 passed / 36 skipped`, `-W error`, ruff + `mypy --strict` clean.
- Packaging (C4 upcoming): the fonts ride the wheel (theme package
  data) — no new dependency.
