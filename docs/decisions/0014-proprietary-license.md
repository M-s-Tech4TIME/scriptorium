# 0014 — Proprietary license; public repo for CI only; Tech4TIME attribution

Status: accepted | Date: 2026-10-16 | Approver: owner
Context: Scriptorium is a proprietary commercial product of M/s. Tech4TIME
(future sale to clients). Repo is public solely for free GitHub Actions CI
(no paid plan). Open-source options withdrawn by owner.
Options: (A) no OSI license + explicit proprietary `NOTICE` now (chosen);
(B) full custom EULA now (deferred to pre-sale, needs counsel);
(C) any OSI license (rejected — contradicts commercial sale, practically irreversible).
Decision: (A). `NOTICE` (all rights reserved, visibility grants no rights),
`README.md` + `nfpm.yaml` (`Proprietary`, maintainer `M/s. Tech4TIME`) carry
attribution. GitHub repo: public `M-s-Tech4TIME/scriptorium` with owner text.
Consequences: Secret/customer-data hygiene is sev-1 (rotate+purge+report);
signing keys never in repo; contributor terms (CLA) required before any
outside contribution.
