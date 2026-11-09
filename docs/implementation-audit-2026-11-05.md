# Implementation Audit — 2026-11-05

## Scope and method

This is a source audit of the current checkout against the Smart School architecture and the supplied implementation prompt. It covers models, migrations, routes, services, templates, tests, configuration, and the requested implementation-status documents. No production database or live deployment was queried. **“Implemented” below describes source presence and connection; it does not imply production verification.** Runtime tests are recorded separately after the first implementation slice.

The working tree already contains user changes and prior task changes, including a modified SQLite database, deleted files under `hardware/esp32_school_rfid/`, `.vscode/mcp.json`, and `pytest.ini`. Preserve these; new RFID work uses `hardware/esp32_rfid_sdms/`.

## Executive status

| Status | Areas |
| --- | --- |
| IMPLEMENTED BUT NOT FULLY TESTED | Core Flask app/session auth; student and guardian records; academic/assessment screens; basic attendance and RFID endpoint; welfare case/report workflow; separate behavior model/workflow; fees and library; meetings/messaging/notifications |
| PARTIALLY IMPLEMENTED | Relational enrollment; RFID event history and official reconciliation; academic approval/history; role scope consistency; finance reconciliation; analytics; exports; audit coverage; React migration documentation |
| NOT IMPLEMENTED | General stock/inventory, staff accountability reports, resource/purchase requests, complete expense accounting, permission-aware School AI Assistant in the current source tree, full cross-domain early warning |
| BROKEN OR INCONSISTENT | React migration docs say `react-frontend/` exists, but it is absent; School AI docs describe `/ai-assistant` and `/api/ai/chat`, but no such route/service exists; welfare documentation names migrations from a different baseline than this checkout; boot previously failed at ORM mapping until `FeeTransaction.student` was made explicit |

No area can be labeled **COMPLETE AND TESTED** for production from this source-only audit.

## Prioritized implementation backlog

### A. Database and model gaps

| Status / priority | Finding and evidence | Files to change | Main risk / dependency |
| --- | --- | --- | --- |
| PARTIALLY IMPLEMENTED · P1 | `AcademicEnrollment` links student/year/department/trade/class, but unique `(student_id, academic_year_id)` prevents preserving multiple class placements when a student transfers within the same year. | `backend-app/app/models/enrollment.py`, `academic_structure.py`, new migration, student/enrollment service | Must preserve legacy `User.class_name` and attendance/grade history; migration needs data-copy and rollback strategy. |
| PARTIALLY IMPLEMENTED · P1 | Authenticated scans now append `RFIDScanLog` events with device ID, server time, outcome, and duplicate flag. No official daily report snapshot/revision model exists. | `models/rfid.py`, `models/attendance.py`, `routes/rfid.py`, attendance service, new migration | Raw UID is sensitive; avoid storing credentials; add durable idempotency keys for device retries and report revision rules. |
| PARTIALLY IMPLEMENTED · P2 | Welfare records and daily reports exist; records store class text but no enrollment reference, and there are no monthly/annual report snapshots. | `models/welfare.py`, welfare migration, welfare routes/services | Historical class and scope correctness depends on enrollment linkage. |
| PARTIALLY IMPLEMENTED · P2 | `BehaviorRecord` is separate, but lacks a structured severity, intervention/counseling plan, evidence attachment, parent acknowledgement, and trend snapshot. Legacy `DisciplineCase` retains `mark_deduction`. | `models/behavior.py`, `discipline.py`, migrations | Do not infer or bulk-convert legacy discipline meaning; preserve grade data boundaries. |
| NOT IMPLEMENTED · P2 | No general inventory item, category, supplier, location, stock movement/count, purchase, or resource request model was found. Library books/loans are not general inventory. | New models/migrations and dedicated service/routes | Needs transaction rules, stock constraints, financial linkage, permissions, and audit before UI. |
| PARTIALLY IMPLEMENTED · P2 | Fees have requirements and transactions; no expense, supplier payment, budget, cashbook, bank/mobile reconciliation or receipt attachment model. Recent fee reconciliation adds state/actor/note, but transaction values use floating point and legacy reference is not unique. | `models/fees.py`, fee migration, finance service/routes | Currency precision, reversal rules, approvals, and preserving existing balances. |
| NOT IMPLEMENTED · P2 | No employee daily/monthly/term/year report or general material/emergency request model. Daily welfare reports are role-specific and do not satisfy staff accountability. | New report/request models, migrations, services/routes | Reporting periods and deadlines must be configurable; reminders need idempotent jobs. |
| PARTIALLY IMPLEMENTED · P3 | `ActivityLog`, meeting, message, notice, and welfare audits cover selected areas; there is no unified audit contract across finance, enrollment, attendance publication, imports, and approvals. | audit models/services and affected domain models/routes | Define retention, actor, before/after, reason, and source IDs without logging secrets. |

### B. Backend routes and service gaps

| Status / priority | Finding and evidence | Files to change | Main risk / dependency |
| --- | --- | --- | --- |
| PARTIALLY IMPLEMENTED · P1 | `/student/rfid-login` validates the configured token, card, time window and daily attendance, and now persists authenticated scan outcomes with a device ID. It does not enforce active enrollment or produce official report revisions. | `routes/rfid.py`, `services/attendance_service.py`, `services/rfid_service.py`, RFID tests | Keep server time authoritative; avoid changing notification timing without reconciliation policy. |
| PARTIALLY IMPLEMENTED · P1 | Most student queries use mutable `User.class_name`, not active/historical `AcademicEnrollment`. | `routes/students.py`, `attendance.py`, `academics.py`, `assessments.py`, `behavior.py`, `welfare.py`, `reports.py`, guardian helpers | Migrate query by query; keep authorized guardian and teacher scopes server-side. |
| IMPLEMENTED BUT NOT FULLY TESTED · P2 | Welfare routes/services include role-scoped case create/update/resolve, daily reports, admin review and audit, but monthly/annual and missing-report accountability are absent. | `routes/welfare.py`, `services/welfare_report_service.py`, scheduler, docs/tests | Verify gender scope and whether reports are derivable from daily source records. |
| PARTIALLY IMPLEMENTED · P2 | Behavior workflow records, reviews, resolves, publishes and sends in-app parent notices; it does not implement the full intervention/follow-up and discipline decision chain. | `routes/behavior.py`, `routes/discipline.py`, behavior service/model | Parent notifications must not expose unpublished or out-of-scope details. |
| NOT IMPLEMENTED · P2 | No general stock, purchasing, resource request, expense, or staff-report endpoints/services found. | New focused blueprints/services, route registration | Implement backend authorization and transaction boundaries before adding forms. |
| BROKEN OR INCONSISTENT · P2 | Current source inventory contains no AI route/service, while `docs/school-ai-assistant.md` claims an authenticated assistant API. | `routes/__init__.py`, new AI service/route only after safe data tools exist, docs | Never expose broad query execution or frontend-only filters to AI. |

### C. Academic enrollment integration gaps

**Status: PARTIALLY IMPLEMENTED.** The hierarchy and enrollment models plus `v20261031_01_academic_foundation.py` exist and backfill only recognized class labels. Several routes still read `User.department`, `trade`, `level`, `class_name`, and `academic_year`. Transfers within one year cannot be represented under the current uniqueness constraint. The `AcademicEnrollment` report added in the previous slice reads historical rows but does not make those rows authoritative in student, teacher, guardian, attendance, academic, welfare, or behavior queries.

**Affected files:** `models/enrollment.py`, `migrations/versions/v20261031_01_academic_foundation.py`, `routes/students.py`, `academics.py`, `assessments.py`, `attendance.py`, `rfid.py`, `parent_portal.py`, `behavior.py`, `welfare.py`, `reports.py`, `utils/helpers.py`, `tests/test_academic_placement_forms.py`, `test_guardian_access.py`, `test_role_access.py`.

**Dependencies/security:** enrollment status and effective dates; same-year transfer history; scoped teacher assignment; guardian linkage; legacy fallback policy and migration coverage report.

### D. RFID and attendance gaps

**Status: PARTIALLY IMPLEMENTED.** Configured device authentication, UID normalization, unassigned-card queue, time-window classification, daily Attendance creation, absence reconciliation, manual correction audit, and authenticated scan ledger writes exist. Scan events record device ID, server time, session/outcome and whether the attendance action was a duplicate. The route matches cards through `User.rfid_uid` and checks account activity, but not active enrollment. Reconciliation is a mutable daily Attendance operation, not a frozen, versioned official report with Patron/Matron review and welfare overlays. `/student/rfid-status` invokes reconciliation while polling, so its timing and notification effect need explicit acceptance criteria.

**Affected files:** `routes/rfid.py`, `services/attendance_service.py`, `services/rfid_service.py`, `models/rfid.py`, `models/attendance.py`, `models/welfare.py`, `routes/attendance.py`, `tests/test_rfid.py`, `tests/test_attendance.py`, `hardware/esp32_rfid_sdms/esp32_rfid_sdms.ino`, hardware README, `docs/meeting-security-and-deployment.md` (deployment security conventions).

**Priority:** first implementation milestone is authenticated RFID scan event persistence and event-to-daily attendance linkage, followed by versioned official reconciliation. Enrollment gating depends on first completing reliable enrollment backfill and transfer representation.

### E. Patron and Matron gaps

**Status: IMPLEMENTED BUT NOT FULLY TESTED.** Dedicated welfare records, gender-scoped rosters, active-case states, follow-up, approval/review, daily report snapshots and audit events exist in `models/welfare.py`, `routes/welfare.py`, `services/welfare_service.py`, `welfare_report_service.py`, `welfare_analytics_service.py`, and `tests/test_welfare.py`. There are no monthly/annual reports derived from cases, no enrollment reference, and no complete missed-report scheduler. Documentation route/migration names do not match the current checkout and must be corrected after verification.

### F. Behavior and discipline gaps

**Status: PARTIALLY IMPLEMENTED.** `BehaviorRecord` is separate from `DisciplineCase`; behavior routes support scoped submission, review, resolution, publication and in-app notice. It lacks structured intervention, investigation evidence, counseling plan, explicit parent acknowledgement and transparent trend/risk history. Existing discipline workflow and mark deduction must remain separate from behavior observations. Files: `models/behavior.py`, `models/discipline.py`, `routes/behavior.py`, `routes/discipline.py`, `tests/test_behavior_workflow.py`, `docs/ai-school-system-gap-analysis.md`.

### G. Finance and inventory integration gaps

**Status: PARTIALLY IMPLEMENTED for fees; NOT IMPLEMENTED for general inventory and purchasing.** `routes/fees.py` and `models/fees.py` support fee requirements and payments; recent changes introduce manual pending/confirmed/rejected reconciliation. There are no expense/supplier/budget/cashbook workflows. `library.py` tracks books and loans but is not stores inventory. There are no stock movements, requests, purchase orders, receipt discrepancies, or finance-to-stock references.

**Affected files:** `models/fees.py`, `routes/fees.py`, `routes/dashboard.py`, `routes/admin_master_dashboard.py`, `routes/reports.py`; new inventory/request/purchase models, migrations, services, role matrix and tests.

### H. Staff reporting and resource requests

**Status: NOT IMPLEMENTED.** No general staff report or material/emergency resource-request model/route/service exists. Welfare daily reports are not a substitute. Create shared workflows only after role/approval matrix, due dates, period uniqueness, attachments, review and fulfillment transitions are defined. Files to add: focused models, migration, services, routes, tests, navigation; update `ROLE_ACCESS`, `base.html`, admin reporting, notification scheduler.

### I. Analytics and AI

**Status: PARTIALLY IMPLEMENTED analytics; NOT IMPLEMENTED AI in source.** Dashboards and domain reports exist, but hierarchy drill-down and validated cross-domain comparisons do not. No inventory/staff/request data exists to analyze. The claimed `/ai-assistant` and `/api/ai/chat` source is absent, so the assistant document is not evidence of a working assistant. Files: `routes/dashboard.py`, `admin_master_dashboard.py`, `reports.py`, `utils/constants.py`, route registration, new permission-scoped service/route only after data APIs and audit are established.

### J. Frontend and UI migration

**Status: BROKEN OR INCONSISTENT documentation; server-rendered Flask UI is the actual frontend.** Root inventory has no `react-frontend/`; `backend-app/app/templates/base.html` is the shared shell and module pages are mostly server-generated HTML. `docs/react-migration-plan.md` describes a React/Vite dashboard and API not present in this checkout. `hardware/esp32_rfid_sdms/` is a new firmware integration, not a web frontend. No React migration should be attempted until the intended dependency/build setup is restored or formally changed.

**Affected files:** `backend-app/app/templates/base.html`, `routes/*.py`, `docs/react-migration-plan.md`, `README.md`, deployment config.

### K. Security and audit

**Status: PARTIALLY IMPLEMENTED.** Flask session authentication, password hashing, server-side role decorators, verified guardian links, meeting API CSRF, welfare/behavior scope checks, and selected audit chains exist. Scoping remains inconsistent between current-class text and enrollment; CSRF coverage varies by route; RFID has one server-wide token rather than per-device credentials; the general config includes a development `SECRET_KEY` fallback, so production must be prevented from starting with that fallback. Files: `config.py`, `utils/decorators.py`, `utils/constants.py`, affected POST routes, RFID model/route, audit models/services, `.env.example`, security docs.

### L. Tests and production deployment

**Status: PARTIALLY IMPLEMENTED.** Existing tests cover initialization, student access, attendance, RFID UID normalization, welfare, behavior, guardian access, meetings, notifications, and some roles. The current `test_rfid.py` has only a UID-normalization test; it does not exercise the authenticated endpoint, event ledger, class scope, time windows or status poll. There are no inventory/request/staff/AI/enrollment-transfer end-to-end tests. Deployment docs mention external database and configuration, but no automated backup/restore implementation or verified production recovery evidence exists.

**Required tests/files:** extend `tests/test_rfid.py`, `test_attendance.py`, `test_guardian_access.py`, `test_role_access.py`; add enrollment transfer, inventory, finance reconciliation, request, AI scope, and end-to-end report tests. Update migration verification and deployment/backup documentation. Do not claim tested or production-ready before they pass.

## Safest implementation order

1. **Attendance integrity milestone:** authenticated scan events and device/result metadata are implemented with duplicate classification. Add durable device retry idempotency, then implement frozen/versioned official daily reconciliation with explicit welfare inputs and post-reconciliation notifications.
2. **Enrollment authority:** make transfer history representable, complete/backfill enrollment data, then migrate student and role-scoped queries incrementally.
3. **Access and audit:** enforce shared scope services and mutation protections; fail production startup when a development secret is used.
4. **Finance and inventory:** complete fee reconciliation, then add inventory and linked request → approval → purchase → payment → receipt workflows with separated role authority.
5. **Staff reporting and domain workflows:** reporting periods, reviews, reminders and resource fulfillment.
6. **Analytics:** hierarchy drill-down after data sources and scopes are reliable.
7. **AI:** implement read-only, source-traced, role-scoped analysis only after tool APIs exist; retain human approval for consequential actions.
8. **Frontend and production:** correct the React documentation to match reality or restore a real build, then complete responsive UI parity, backup/restore, performance and end-to-end verification.

## First approved implementation slice

The first RFID scan event slice is implemented: authenticated scans append device ID, server time, session, outcome and duplicate status; endpoint tests assert event capture, the firmware identifies its reader, and the hardware README documents the header. This slice does **not** claim official reconciliation is complete. Report snapshots, welfare gate, class/trade/department aggregation, durable retry idempotency, and enrollment gating remain the next attendance milestone. Test execution status is recorded in the delivery summary, not inferred from these source changes.
