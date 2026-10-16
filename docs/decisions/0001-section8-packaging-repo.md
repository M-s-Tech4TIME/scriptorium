# 0001 — Section 8 distribution/packaging/repo (Q1–Q9)

Status: accepted | Date: 2026-10-16 | Approver: owner | Ref: plan-mode §8
Context: On-prem self-hosted first, SaaS kept open. Need .deb/.rpm plug-and-play, single releasable version, PG external.
Options: (A) monorepo + nfpm + web/worker units + FHS /opt + file/env/setup + explicit migrate + bundled frontend + GPG/SBOM + Releases-then-repo vs (B) multi-repo + native debhelper/spec + single unit + /usr distro-python + auto-migrate + split frontend + checksums-only.
Decision: (A) as in AGENTS.md frozen foundation.
Consequences: One version/CI for both packages; sysadmin runs setup+migrate; PGDG required where distro default <18.
