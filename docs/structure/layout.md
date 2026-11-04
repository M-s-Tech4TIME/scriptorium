# Layout + naming (monorepo under scriptorium/, decision 0012)

Last updated: 2026-11-04 / Ref: server-move/first-run + built-in TLS (0040)

Repo root contains only `scriptorium/` (+ `.git`). All work happens under `scriptorium/`.

```
project-scriptorium/
└── scriptorium/
    ├── AGENTS.md  project-details.md  docker-compose.yml
    ├── backend/ (FastAPI: app/{routers,schemas,models,convert,sphinx,serving,worker,backup,tls}/ alembic/ tests/ pyproject.toml typings/)
    ├── frontend/ (React+TS+TipTap: src/{editor,components,pages}/ package.json tsconfig.json)
    ├── packaging/ (nfpm.yaml; build-requirements.{in,lock}; config.env.example;
    │   systemd/scriptorium-{web,worker,redis,redirect,tls-renew}.service + scriptorium-tls-renew.timer;
    │   scripts/{build-app-venv,build-venv,postinst,prerm})
    ├── docs/  scripts/  dist/ (gitignored)
    └── .github/workflows/ (NOTE: GitHub requires workflows at repo-root .github/ — see OPEN-QUESTIONS.md)
```

Naming: `scriptorium-web/worker/redis/redirect` units, `scriptorium` user,
`/opt/scriptorium`, `/etc/scriptorium/config.env` (0600),
`/etc/scriptorium/tls/` (local CA + versioned leaves; `ca.key` is
`root:root 0600`), `/var/lib/scriptorium/{artifacts,media,backups}`
(0026/0038/0039), tables (0012-era list; renames since:
`projects`→`grimoires` 0003, plus athenaeums/grimoire_categories/
refresh_tokens/public_names/media_assets/backup_jobs — current model in
data-model.md). API prefix `/api/v1/*`. Any rename = Rule 4 decision.
