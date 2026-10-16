# Technology — nfpm 2.x (packaging)

- Version: 2.x (resolve exact at first package build, M5; verify then per Rule 5.2).
- Why: single YAML → `.deb` + `.rpm`, zero-dep Go binary, CI-friendly (decision 0001/Q2).
  `lintian` + `rpmlint` gates catch non-compliance.
- Used: `packaging/nfpm.yaml` + `systemd/` + `scripts/` (postinst/prerm never touch DB).
- Verified: shortlist 2026-10-16 (goreleaser/nfpm); exact pin at M5 with matrix entry.
