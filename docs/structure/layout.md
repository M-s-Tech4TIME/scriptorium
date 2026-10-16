# Layout + naming (monorepo, Q1)

Last updated: 2026-10-16 / Ref: uncommitted

```
/ AGENTS.md  project-details.md  docker-compose.yml
  backend/ (FastAPI: app/{routers,schemas,models,convert,sphinx,worker}/ alembic/ tests/ pyproject.toml)
  frontend/ (React+TS+TipTap: src/{editor,components,pages}/ package.json tsconfig.json)
  packaging/ (nfpm.yaml systemd/scriptorium-{web,worker}.service scripts/{setup,migrate})
  docs/  .github/workflows/  dist/ (gitignored)
```

Naming: `scriptorium-web/worker` units, `scriptorium` user, `/opt/scriptorium`,
`/etc/scriptorium/config.env` (0600), `/var/lib/scriptorium/{sources,builds,uploads}`,
tables per Q21 (`users memberships projects nodes documents document_history builds audit_log`).
API prefix `/api/v1/*`. Any rename = Rule 4 decision.
