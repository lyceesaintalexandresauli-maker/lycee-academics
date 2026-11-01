# AI-Powered School System: Repository Gap Analysis

Assessment date: 2026-10-29  
Repository: `smart_school_refactored_ui_updated/smart_school_refactored`

## Current architecture

- Flask, Flask-Login, SQLAlchemy, and server-rendered Jinja/HTML routes are the operational application. A separate React/Vite dashboard experiment is described in `docs/react-migration-plan.md`; it is not a full React migration.
- The existing `User` row combines account and student identity fields. Student class placement is stored as text on `User`; there is no relational academic-year enrollment history.
- Server-side role checks exist in `app/utils/constants.py` and route decorators. Guardian links have a dedicated verified/revocable relationship model. Teacher and guardian scopes are implemented in several workflows, but role-specific scope is inconsistent across modules.
- Database changes use handwritten, idempotent migration modules invoked during app creation. Test fixtures use in-memory SQLite.

## Feature coverage

| Area | Existing implementation | Gap / risk |
|---|---|---|
| Authentication and roles | Flask session authentication; master admin, head teacher, teacher, secretary, parent, student, accountant, librarian, discipline, patron, matron, auditor roles | No documented permission-plus-scope registry across all endpoints; multi-role account/workspace switching is not implemented. |
| Student registration and guardians | Student registration, SDMS code, RFID UID on the student account, guardian link verification/revocation, parent portal | Academic history is not normalized; class placement is mutable text. Imports and verified identity workflows need stronger duplicate review. |
| School structure | Department, trade, level, class name, section fields and filters | No relational Department/Trade/Class/AcademicYear/Enrollment records; catalog options and active counts are not fully database-driven. |
| RFID and attendance | RFID endpoint, token-protected status endpoint, pending-card workflow, scan windows, absence reconciliation, manual attendance, reports | Attendance rows represent daily results rather than an immutable raw scan-event ledger; enrollment-at-scan history and device synchronization audit are limited. |
| Daily attendance reports | Attendance summaries and server-triggered absence reconciliation | No immutable official report snapshot/revision workflow in this checkout; welfare source completeness is not reconciled into a report. |
| Welfare | Patron/matron roles, dashboards and some class-scoped access references | No dedicated welfare case/report model or service was found. Gender-based assignment scope and welfare overlays are not enforced consistently. |
| Behavior and discipline | `DisciplineCase` stores Achievement/Concern reports, publication and mark deductions; a discipline page exists | Behavior and disciplinary decisions share one model. No configurable severity taxonomy, case workflow, intervention history, trend/risk explanation, or term evaluation. Mark deduction on a behavior report risks conflating behavior with academic records. |
| Academics and assessments | Subjects, timetable, grades, assessments/submissions/attempts, rubrics, lesson materials, report card approval | Assignment/LMS and official exam/reporting workflows are partial; historical enrollment/teacher assignment versioning and complete grade approval/publication are not consistently represented. |
| Fees and library | Fee requirements/transactions, books and loans | Payment requests, provider-backed delivery records, and full inventory/loan history controls require review. |
| Communication and meetings | Announcements, messages, notifications, parent alerts, meetings, approvals, minutes, actions and audit events | Email/SMS provider delivery status/retries and notification preferences need broader verification. |
| Timetable and day schedule | Timetable entries and day schedule entries | Approval, publication, and role-scoped schedule lifecycle should be audited against the requested workflow. |
| Analytics and reports | Admin dashboard, attendance, student and academic reports | No unified school→department→trade→class→student drill-down or validated cross-domain trend/risk dashboards. |
| AI assistant and knowledge base | No AI assistant route/service or approved school-policy knowledge workflow found in the route/service inventory | Missing role-aware data tools, conversation audit/history, safe refusal, human-confirmed actions, and document retrieval. |
| Audit and governance | Activity log, meeting and messaging audit chains, some sensitive actions logged | Audit coverage is uneven; retention, backup verification, approval logs, and operational monitoring need documentation and implementation. |
| Testing | Tests cover attendance, guardian access, meetings, notifications, RFID, role access, and students | No broad behavior, welfare, academic publication, analytics, AI-scope, historical enrollment, or end-to-end acceptance tests. |

## Recommended implementation sequence

1. **Foundation and data boundaries:** document role permissions/scopes; add relational academic structure and enrollment history through migrations; preserve current `User` data and legacy URLs.
2. **Attendance and welfare integrity:** add immutable RFID scan events and daily report revisions; add Patron/Matron welfare records with separate attendance overlays and audited scope checks.
3. **Behavior and discipline separation:** introduce behavior records and configurable classifications; retain existing discipline records and preserve their history; prevent behavior reporting from changing academic marks.
4. **Academic workflow:** verify teacher assignment scope, LMS submissions, official result approval/publication, and historical enrollment-based reporting.
5. **Unified reporting and notifications:** provide hierarchy drill-down, delivery logs/retries and preference handling without duplicating existing notification records.
6. **AI assistant:** add only after authorization and reporting APIs provide safe, auditable, role-scoped data access; require human confirmation for consequential actions.
7. **Governance and release:** complete security, accessibility, performance, backup/recovery and deployment checks; run regression and end-to-end workflows.

## First implementation slice

**Implemented:** behavior and discipline now have separate records. Migration `v20261029_02_add_behavior_records.py` creates `behavior_record` without rewriting `DisciplineCase`. The `/behavior` workflow supports staff submissions, teacher class scope, Patron/Matron class-and-gender scope, verified-parent/own-student published views, manager review/resolution/publication, audit activity records, and requested in-app parent notifications on publication. Serious and critical records must enter review before publication.

**Still needed in this area:** configurable behavior categories, interventions and disciplinary action records, risk/trend analytics, term/year evaluations, parent delivery receipts, and policy-controlled retention. Existing behavior-like `DisciplineCase` rows are deliberately not bulk-converted because their meaning, severity, and notification history cannot be inferred safely.

## Constraints and open operational dependencies

- This assessment is based on source inspection; it does not establish production database connectivity, deployment behavior, or RFID hardware operation.
- Current records use mutable class-name text, so historic reports cannot reliably reconstruct prior enrollment without an enrollment-history model.
- AI provider, SMS/email provider, school retention policy, behavior scoring policy, and production service objectives are not configured in the inspected source.
- The new behavior workflow is a first slice, not a replacement for the existing discipline page; it has not yet been exercised against the production database or deployed UI.
