# 0003 — Version set Rule 5 (Q10–Q12)

Status: accepted | Date: 2026-10-16 | Approver: owner | Verified: 2026-10-16
Context: Latest-stable + compatible + long-lived (Rule 5 + owner LTS/proven rule).
Options: Python 3.15 (latest, 7 days old, weak wheel support) vs 3.13 (to 2029, PPA/source pain) vs 3.12 (to 2028, max-common); docutils 0.23 now vs 0.22.4 + gate 0.23.
Decision: Python 3.12.x; docutils 0.22.4 pinned, 0.23 in CI gate; proceed to §9 with this set.
Consequences: `/opt` venv bundles 3.12; upgrade to 3.13 needs owner decision + rebuild validation.
Full pins: `docs/technology/compatibility-matrix.md`.
