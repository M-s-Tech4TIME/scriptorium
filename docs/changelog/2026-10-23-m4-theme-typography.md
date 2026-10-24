# 2026-10-23 — M4 theme typography: vendored Inter reading face (0030)

The typography ruling of the M4-C3.5 second-owner-look arc: the
article/documentation face moves from the consult serif stack to a
vendored **Inter**, on the owner's explicit preference for the
system-sans "Notion look" with consistent cross-machine rendering
(decision 0030).

## What changed

- **In the theme** (`backend/app/sphinx/theme/scriptorium/`):
  - `static/fonts/` — new: `inter-latin.woff2` (72.5 KB, variable,
    upright) + `inter-latin-italic.woff2` (79.7 KB, italic) + the
    vendored OFL 1.1 license text (`OFL-Inter.txt`). Retrieved from
    Google Fonts 2026-10-23 per the owner's sourcing ruling (Inter
    v20 latin instance); `file(1)`-verified woff2.
  - `static/scriptorium.css` — `@font-face` pair (`font-weight:
    100 900`, `font-display: swap`, relative `fonts/…` URLs served
    from the artifact's `_static` — zero network holds) and the ruled
    override `--sd-font-body: "Inter", system-ui, …` in the 0029/0030
    addendum `:root` block; the consult `:root` stays verbatim with
    `references/tokens.css`. `--sd-font-heading` follows by indirection.
- **NOTICE** — new third-party-fonts paragraph (Inter Project Authors,
  OFL 1.1, Google Fonts source + date).
- **Tests** — materialization asserts the vendored fonts dir; the
  artifact `_static` inventory gains `fonts/`; physiology asserts
  `@font-face` + file path + the override token. Suite `76 passed /
  36 skipped` (`-W error`), ruff + `mypy --strict` clean (no new
  runtime dependency; fonts ride the theme package).

## Rulings under it

- Sans replaces the serif reading face for body + headings (0028 D4
  superseded by owner ruling; recorded, reference consult untouched).
- Fallback = the ruled UI sans stack — the RTD-faithful chain
  (`Lato, proxima-nova, …`) was considered that day and **dropped by
  the owner** ("don't complicate it").
- Latin-only subset disclosed: non-latin glyphs fall back to the same
  stack; per-script vendoring would need a future ruling.

## Not in this tranche

M4-C4 packaging, serving-phase hooks, dark-mode policy — all per
0026/0027 mandates. CI push + ×3 verification follows the owner's
preview verdict (same flow as the pending `0f5fcc8` + 0029 pass).

## Next

Owner look at preview #3 (Inter live) → commit + push (`0f5fcc8` +
0029 pass + 0030 typography) → CI green ×3 → M4-C4 packaging →
0017 docutils-0.23 probe → M4-complete report → serving phase
(Q-SERVE-A…E).
