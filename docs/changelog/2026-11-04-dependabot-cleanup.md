# 2026-11-04 — Dependabot Docker entry cleanup

Owner approved removing the unused `docker` ecosystem entry from
`.github/dependabot.yml` (option 1 of the 0040 closeout report). This is
CI housekeeping, not a product change.

## Why

- The entry was added in `9d645e3` with `directory: /`.
- The repository contains no `Dockerfile` or Kubernetes manifest, so
  every scheduled "Dependabot Updates" run aborted with
  `dependency_file_not_found`.
- The failure predates tranche 0040 and is unrelated to the five
  required CI gates.

## Change

- Removed only the `docker` stanza. The pip (`/backend`, `/packaging`),
  npm (`/frontend`), and github-actions (`/`) entries are unchanged.
- No runtime code, package version, or lockfile changed.

## Verification

- The edited YAML parses with PyYAML.
- `scripts/validate-docs.sh` and `git diff --check` pass locally.
- CI ×3 results and the `main` fast-forward are recorded in the
  closeout commit.
- The scheduled Dependabot Updates run is expected to stop reporting the
  missing Dockerfile on its next weekly run.
