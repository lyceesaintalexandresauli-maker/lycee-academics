# Copilot instructions for this repository

## Project shape

This repository is a Flask-first school management system. The backend under [backend-app](../backend-app) remains the source of truth for auth, authorization, database access, and school-scoped permissions. React/Vite is introduced incrementally and must not bypass server-side checks.

Key references:
- [README.md](../README.md) for local setup and deployment expectations
- [AGENTS.md](../AGENTS.md) for repo-level workflow expectations
- [docs/react-migration-plan.md](../docs/react-migration-plan.md) for frontend migration boundaries
- [docs/meetings-api.md](../docs/meetings-api.md) for meeting API contracts
- [docs/meeting-schema.md](../docs/meeting-schema.md) for database and migration expectations
- [MEETING_PANEL_IMPLEMENTATION.md](../MEETING_PANEL_IMPLEMENTATION.md) for workflow-specific constraints

## Required conventions

- Keep route handlers thin and focused on validation, auth checks, and response shaping.
- Move reusable logic into services or utilities instead of embedding it in routes.
- Preserve role checks, school-scoping, and guardian access patterns from the backend.
- Prefer the backend as the authority for permission enforcement, even when React screens exist.
- Use SQLAlchemy models and migration-friendly patterns rather than editing a live database directly.
- If schema changes are required, add a migration under [backend-app/migrations/versions](../backend-app/migrations/versions).
- Before changing meeting endpoints or schema, read [docs/meetings-api.md](../docs/meetings-api.md) and [docs/meeting-schema.md](../docs/meeting-schema.md).

## Local setup and validation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

When the React package is present:

```powershell
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
python run.py
```

Run backend tests with:

```powershell
python -m pytest
```

If frontend behavior changes, validate the build with:

```powershell
npm.cmd run build --prefix react-frontend
```

## Security and config guardrails

- Keep secrets and local config values in `.env`; do not commit credentials or local SQLite files.
- Treat bootstrap admin credentials as local development values only.
- Do not broaden access or bypass backend permission checks to make a small change easier.
- Keep changes aligned with the staged frontend migration approach in [docs/react-migration-plan.md](../docs/react-migration-plan.md).
