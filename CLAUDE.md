# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Lycée de Muhura Smart School System — a Flask application (school management: admissions, academics, attendance/RFID, fees, meetings, welfare, library, discipline, messaging) with a React/Vite frontend (`react-frontend/`) being introduced incrementally. The root entrypoint is `run.py`, which loads the backend from the `backend-app/` package. Deployment target is Supabase (PostgreSQL) + Render.

## Commands

```powershell
# Setup (Windows)
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
python run.py                 # dev server on 0.0.0.0:5000

# Windows-local run using the existing instance/lyceedemuhura.db SQLite file
.\run-local.cmd

# Tests
python -m pytest              # config in pytest.ini: tests in backend-app/tests

# Frontend build check (when changing React behavior)
npm.cmd run build --prefix react-frontend
```

If the frontend package is absent or not built, the app falls back to backend-only Flask routes.

## Architecture

- `backend-app/app/models/` — SQLAlchemy models; DB tables and FKs are defined here, never recreated manually in the database
- `backend-app/app/routes/` — HTTP/UI routes; handlers should focus on request validation and response shaping
- `backend-app/app/services/` — business-logic seams (RFID, attendance, notifications, welfare analytics)
- `backend-app/app/templates/` — Jinja templates (most roles still use Flask-rendered pages)
- `backend-app/app/static/` — static assets
- `backend-app/tests/` — pytest tests
- `backend-app/migrations/versions/` — Flask-Migrate revisions
- `react-frontend/` — React/Vite source; first migrated screen is the Master Administrator dashboard
- `hardware/esp32_rfid_sdms/` — ESP32 RFID reader firmware
- `docs/` — architecture and module docs

## Key conventions and guardrails

- Keep Flask patterns and the server-side authorization model intact: role checks and school/guardian scoping live in the backend; never move critical permissions into React-only code.
- Database changes must go through migrations (idempotent, migration-friendly), not manual DB edits. Before schema changes, check `docs/meeting-schema.md` and migration history.
- For meeting-related work, consult `docs/meetings-api.md` and `docs/meeting-security-and-deployment.md` first. Frontend work follows `docs/react-migration-plan.md` (incremental adoption, no breaking backend flows).
- Python style: four-space indent, `snake_case` functions/variables, `PascalCase` classes.
- Add small focused tests under `backend-app/tests/` when changing routes, permissions, or data boundaries.
- RFID endpoints fail closed until `RFID_DEVICE_TOKEN` is set in the server env and on the reader.
- Fee transactions are pending until an accountant/master admin confirms them; only confirmed transactions affect balances and dashboard totals.

## Security and config

- Secrets and local values go in `.env` (see `.env.example`). Never commit credentials, local SQLite files, or virtual environments.
- Development-only bootstrap admin is `admin` / `admin1234`; production creates admins via `flask --app run.py create-admin` (min 12-char password).
- Scheduled jobs: `reconcile-daily-attendance` (per minute), `send-meeting-reminders` (hourly), `process-meeting-actions` (daily) — run as `flask --app run.py <command>`.

## Commits and PRs

Concise imperative subjects (e.g., "Fix teacher class assignment scope"). PRs describe the user-visible change, migration/config impact, verification performed, and include screenshots for UI changes.
