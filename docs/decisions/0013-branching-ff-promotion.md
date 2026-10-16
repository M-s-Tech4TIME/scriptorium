# 0013 — Branching: fast-forward-only release promotion (amends 0008)

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: Owner requires `main` (final/major releases) + `dev` (all development)
byte-identical after every merge. No industry standard mandates persistent
identical main+dev (GitFlow diverges by design; GitHub Flow has one line).
Options: (1) GitHub Flow single line (no dev — rejected, owner wants dev);
(2) GitFlow (diverges — rejected); (3) ff-only release promotion (chosen).
Decision: (3). Feature work via `feat/*` PRs into `dev` (merge commits allowed
on `dev`). `main` advances only via `git checkout main && git merge --ff-only dev`
(CLI/owner or release Action — GitHub web UI cannot ff-merge). `main` protection:
linear history + no force push + no deletions; no required-PR rule (would block
ff release pushes). Standing rule: after any `main` update, ff `dev` to `main`
and verify `git diff main dev` empty (same SHA).
Consequences: Identical refs by construction; linear auditable `main`.
