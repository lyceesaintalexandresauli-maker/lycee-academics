# Repository Guidelines for Coding Agents

## Project shape

This repo is a Flask-first school management system. The backend under [backend-app](backend-app) is the source of truth for authentication, authorization, database access, and school-scoped permissions. React/Vite is being introduced incrementally and must never bypass server-side enforcement.

Key references:
- [README.md](README.md) for setup and deployment expectations
- [docs/react-migration-plan.md](docs/react-migration-plan.md) for frontend migration boundaries
- [docs/meetings-api.md](docs/meetings-api.md) for meeting API contracts
- [docs/meeting-schema.md](docs/meeting-schema.md) for meeting database and migration expectations
- [MEETING_PANEL_IMPLEMENTATION.md](MEETING_PANEL_IMPLEMENTATION.md) for workflow-specific constraints

## Required agent behaviors

- Keep route handlers thin and focused on request validation, auth checks, and response shaping.
- Move reusable business logic into services or utilities instead of embedding it in routes.
- Preserve role checks, school scoping, and guardian access patterns from the backend.
- Treat the backend as the authority for permission enforcement even when React screens are present.
- Prefer focused tests in [backend-app/tests](backend-app/tests) for route, access, and data-boundary changes.
- Follow the existing Python conventions: four-space indentation, `snake_case`, and `PascalCase` for classes.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

If the React frontend exists, build it before running the app:

```powershell
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
python run.py
```

If the frontend package is absent, fall back to the backend-only routes and keep the staged migration plan in [docs/react-migration-plan.md](docs/react-migration-plan.md) in mind.

## Database and migration rules

- Use SQLAlchemy models and Flask migration patterns; do not edit a live database directly.
- If a schema change is necessary, add or update migration files under [backend-app/migrations/versions](backend-app/migrations/versions).
- Before changing meeting-related schema or endpoints, read [docs/meeting-schema.md](docs/meeting-schema.md) and [docs/meetings-api.md](docs/meetings-api.md) first.
- Keep schema changes idempotent and compatible with the app’s startup migration flow.

## Validation

Run the backend test suite:

```powershell
python -m pytest
```

If frontend behavior changes, validate the frontend build:

```powershell
npm.cmd run build --prefix react-frontend
```

## Security and configuration guardrails

- Keep secrets and local config values in `.env`; do not commit credentials or local SQLite files.
- Treat bootstrap admin credentials as local development values only.
- Do not broaden access, loosen scoping, or bypass backend permission checks to make a small change simpler.

## Commit and PR expectations

Use concise, imperative commit subjects such as “Fix teacher class assignment scope.” Pull requests should describe the user-visible change, note any config or migration impact, and include verification performed.
