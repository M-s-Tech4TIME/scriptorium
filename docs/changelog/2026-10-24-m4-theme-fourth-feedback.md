# Changelog 2026-10-24 — M4-C3.5 fourth feedback batch (0034)

## What landed

- **Panel placeholder only:** the sidebar search field now reads
  `Search`; the dialog keeps `Search the library`, and the full search
  page is unchanged.
- **Code-block language label:** the header now reads the language from
  the outer `div.highlight-<lang>` wrapper instead of the inner
  `div.highlight` block. Python, JavaScript, and Bash render their names;
  no-language and Pygments `default` blocks show `Code`.
- **Pager column:** the article and pager share a new
  `.sd-reading-main` first grid column. Next ends at the article edge and
  never crosses the On-This-Page rail.
- **No-flash collapsed panel:** an inline `<head>` script applies the
  persisted collapsed state before the shell exists, so Previous/Next
  navigation no longer paints the panel expanded for a frame. The body
  script then swaps in the normal `.sd-panel-off` class and removes the
  pre-paint marker.
- **Regression coverage:** Node assertions for the language helper;
  theme-build assertions for the panel/dialog placeholders, the
  `.sd-reading-main` rule, the pager's DOM ancestry, and the pre-paint
  panel marker before the shell.
- **Records:** decision 0034, the 0029 code-chrome correction, the
  `docs/technology/sphinx.md` note, and the brain sync.

## Why

The owner approved the preview #5 baseline (`b15446f`, CI green ×3) and
asked for three corrections. Preview #6 implemented them and was
approved; the review then exposed a one-frame expanded-panel flash on
pager navigation while the panel was collapsed. This batch is the first
change executed under Standing Rule 8 (decision 0033): it fixes the
items while re-verifying the approved search, dialog, clear, toggle,
scrollspy, weight, and inline-code behavior.

## Verification

Preview #7 (the rebuilt `.preview/site` artifact) was checked in headless
Chrome:

- Code headers: Bash, JavaScript, Python; no empty labels.
- Pager at 1400×900: article right 1069, Next right 1069, rail left
  1101; Next is inside the article and clear of the rail. At 1000×800
  and 800×900 the rail is hidden and the pager stays in the column; no
  horizontal overflow.
- Panel placeholder `Search`; dialog placeholder `Search the library`.
- No-flash state with stored `closed`: the first body script sees
  `html.sd-panel-pending-off` before the shell exists; the final shell
  is collapsed, the marker is removed, the sidebar width is 0, and the
  expand control is visible. Stored `open` paints expanded with no
  marker; toggling still persists `closed`/`open` correctly.
- Search sentence → 7 folios / 12 sections, exact-phrase group first,
  88 marks; dialog `dx=0, dy=0`, internal scroll, full link carries
  `?q=`; Escape closes; clear-only leaves the value empty and the dialog
  closed; collapse/expand and scrollspy are unchanged.
- Full gates: `pytest -W error` 80 passed / 36 skipped; ruff check/format
  and `mypy --strict` clean.

## Status

Preview #6 was approved; preview #7 adds the no-flash panel fix and is
browser-verified. Decision 0034 is committed together with the
already-committed Standing Rule 8 docs (`cbe2b22`), then pushed and
CI-verified green ×3.
