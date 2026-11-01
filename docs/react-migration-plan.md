# React Migration Assessment

## Current architecture

- Flask 3 and SQLAlchemy own authentication, session cookies, database access, permissions, file handling, and school workflows.
- The shared layout is in `backend-app/app/templates/base.html`. Most module pages are HTML strings built in Python route modules.
- The application has about 30 route modules and a broad set of school workflows. Existing APIs include meeting and RFID endpoints; many other create, edit, upload, and export actions are handled by Flask HTML routes.
- The database and existing user/session records can remain in place. A React UI does not replace the backend responsibilities that enforce access control or connect RFID hardware.

## Migration approach

Use React for the browser UI and retain Flask as the authenticated backend. Move behavior in slices so an unmigrated page continues to use its existing Flask route until its React screen and API are ready. Do not move authorization into React; every read and write API must enforce the existing server-side role, class, and guardian scope.

1. **Frontend foundation (started):** Add a Vite/React build under `react-frontend/`, preserve theme and language preferences, and add a same-origin administrator dashboard API. Master Administrator `/dashboard` uses the React build when it exists; otherwise Flask serves the previous dashboard.
2. **Shared application shell:** Migrate responsive navigation, notifications, profile actions, language selection, theme controls, login and session-expiry behavior.
3. **Core records:** Add JSON APIs and React screens for students, guardians, classes, enrollment, attendance, RFID registration, and reports. Preserve existing endpoints while each workflow is migrated.
4. **Teaching and communication:** Migrate academics, assignments, grades, meetings, messages, announcements, and notifications, including uploads and exports.
5. **Remaining modules and parity:** Migrate fees, library, admissions, documents, correspondence, discipline, welfare, AI assistant, and administration. Check role access, validation, audit, mobile accessibility, and all existing user journeys before removing any legacy page.
6. **Deployment cutover:** Build React assets during deployment, verify the deployed asset paths and session cookie behavior, then retire legacy HTML routes only after parity is demonstrated.

## Current implementation status

- React/Vite source and build configuration are in `react-frontend/`.
- `GET /api/admin/dashboard` is restricted to `master_admin` and returns dashboard counts, the seven-day attendance series, and the same limited recent attendance fields shown by the existing administrator dashboard.
- Master Administrator `/dashboard` serves `backend-app/app/static/react/index.html` when a React build is present. Without that generated build, the existing Flask dashboard remains active.
- Other roles and all non-dashboard pages continue to use their existing Flask routes. The full system has **not** been migrated to React yet.
- No database schema migration was needed for this first UI slice.

## Build

From the repository root, install frontend dependencies and build the static assets:

```powershell
npm.cmd install --prefix react-frontend
npm.cmd run build --prefix react-frontend
```

Then run the Flask application as usual. The generated files are written to `backend-app/app/static/react/` and are ignored by Git; deployment must run the same frontend build before starting Flask. Until that build is available, the previous master dashboard remains the fallback.

## Parity and safety requirements

- Keep Flask session authentication and server-side authorization for every API call.
- Preserve form validation, confirmation behavior, flash/error feedback, upload/download behavior, exports, audit records, and role-specific visibility.
- Maintain current URLs or provide redirects for bookmarks and external integrations, including the ESP32 RFID endpoints.
- Do not change the SQLAlchemy schema or migrate the database as part of a front-end conversion unless a reviewed feature explicitly requires it.
- Keep each legacy route until its React workflow has equivalent behavior and has been reviewed against the existing role and data-access rules.
