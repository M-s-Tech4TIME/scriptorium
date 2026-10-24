# Layout + naming (monorepo under scriptorium/, decision 0012)

Last updated: 2026-10-24 / Ref: M4-C4 packaging layout

Repo root contains only `scriptorium/` (+ `.git`). All work happens under `scriptorium/`.

```
project-scriptorium/
└── scriptorium/
    ├── AGENTS.md  project-details.md  docker-compose.yml
    ├── backend/ (FastAPI: app/{routers,schemas,models,convert,sphinx,worker}/ alembic/ tests/ pyproject.toml)
    ├── frontend/ (React+TS+TipTap: src/{editor,components,pages}/ package.json tsconfig.json)
    ├── packaging/ (nfpm.yaml; build-requirements.{in,lock}; config.env.example;
    │   systemd/scriptorium-{web,worker}.service; scripts/{build-venv,postinst,prerm})
    ├── docs/  scripts/  dist/ (gitignored)
    └── .github/workflows/ (NOTE: GitHub requires workflows at repo-root .github/ — see OPEN-QUESTIONS.md)
```

Naming: `scriptorium-web/worker` units, `scriptorium` user, `/opt/scriptorium`,
`/etc/scriptorium/config.env` (0600), `/var/lib/scriptorium/{sources,builds,uploads}`
(0026 adds `artifacts/` — `/var/lib/scriptorium/artifacts/{athenaeum}/{build_number}/`),
tables (0012-era list; renames since: `projects`→`grimoires` 0003, plus
athenaeums/grimoire_categories/refresh_tokens — current model in
data-model.md). API prefix `/api/v1/*`. Any rename = Rule 4 decision.
