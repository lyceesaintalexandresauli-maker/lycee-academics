# SDMS-Inspired FURPS Requirements

## Reference boundary

The public SDMS portal did not load during review, and the browser access host was unavailable. This specification uses publicly documented SDMS capabilities and does not claim pixel-level knowledge of its authenticated screens. Public sources describe an education information system covering learners, staff, infrastructure, ICT, school health, school feeding, and education statistics. Public payment guidance also describes fee payment and reconciled payment reporting through Umwalimu SACCO.

## Product direction

Make Lycée Academics a school operations and education data system with the clear, structured workflows expected from SDMS. Keep Flask as the authority for authentication, authorization, and records. Use React incrementally for the shared shell and high-traffic screens. Do not copy SDMS logos, text, or protected visual assets; use the reference to guide information hierarchy and workflows.

The shared records, module flow, AI boundary, and human approval model are diagrammed in [Smart School System Architecture](smart-school-architecture.md).

## FURPS requirements

### Functionality

- Maintain one student record with verified guardian links, academic-year enrollment history, class placement, attendance, results, documents, and fee statement.
- Maintain staff records and school structure, including academic years, departments, trades, classes, terms, and role assignments.
- Record attendance scans and manual changes as separate events; produce daily attendance and correction reports with export.
- Support admissions, assessments, marks, report cards, fees, library, communications, welfare, and school operations through connected workflows.
- Reconcile payments with method, receipt/reference, status, actor, timestamp, and exception reason. Only confirmed receipts affect balances and collected-fee reports.
- Provide school, department, trade, class, and year summaries with drill-downs and spreadsheet exports.
- Provide configurable imports and validation summaries for student, staff, and enrollment records.
- Keep every read and write behind server-side role and record-scope checks. Parents see only verified linked children; staff see only their authorized scope.

### Usability

- Provide a consistent role-based application shell with clear module navigation, breadcrumbs, page titles, and a prominent current-school/year context.
- Make common tasks direct: find a learner, register or transfer, take attendance, enter marks, reconcile a payment, and export a report.
- Use searchable/paginated tables, explicit empty/loading/error states, inline validation, confirmation for consequential edits, and preserved filter state.
- Support phone, tablet, and desktop layouts; keyboard navigation; visible focus; readable contrast; and English, Kinyarwanda, and French labels.
- Reduce duplicate data entry by selecting from existing learners, classes, terms, and fee requirements.
- Do not claim visual equivalence until authenticated SDMS screenshots or an accessible demonstration are available for comparison.

### Reliability

- Apply schema changes through idempotent migrations and preserve existing records during upgrade.
- Keep append-only audit events for attendance corrections, payment reconciliation, enrollment changes, and permission-sensitive actions.
- Back up the database and uploaded files on a documented schedule; document and rehearse restore procedures.
- Show transaction outcomes clearly and prevent duplicate submissions for imports, payments, attendance events, and other retryable operations.
- Define recovery behavior for unavailable database, email/SMS, payment, and RFID services; never report a failed integration as successful.
- Establish an offline workflow only for explicitly selected tasks, with a visible pending-sync queue, conflict handling, and server-side authorization on sync.

### Performance

- Paginate large student, attendance, payment, and audit tables; apply filters in SQL and avoid loading entire school histories into memory.
- Add and review indexes for school/year/class/student/date and status filters used by reports.
- Proposed initial target: common list and dashboard requests complete within 2 seconds at the 95th percentile under the agreed production dataset and expected concurrent load.
- Proposed initial target: exports run asynchronously or stream results when they exceed the agreed row limit, with progress and a clear completion state.
- Measure query duration, request errors, export time, and background job delays before tuning or claiming capacity.

### Supportability

- Keep configuration in environment variables, document required secrets and integrations, and fail safely when security-critical configuration is missing.
- Provide structured logs with request identifiers and safe error messages; never log credentials or sensitive learner data unnecessarily.
- Document role permissions, data ownership, import formats, migration order, backup/restore, and deployment steps.
- Provide an operational health page for database, scheduled attendance reconciliation, notifications, file storage, and configured integrations.
- Define a support contact/workflow and a way to report data corrections without allowing users to silently overwrite audit history.
- Maintain automated regression coverage for permissions, guardian scopes, migrations, payment reconciliation, attendance audit, and export behavior.

## Delivery sequence

1. **Foundation and access:** formalize permission/scope matrix; finish enrollment history backfill; add import validation and school/year context.
2. **Core data workflows:** complete student/staff records, attendance audit exports, results and class/year reporting.
3. **Finance:** fee ledger and reconciliation workflow, payment-provider integration only when credentials and provider contracts are available.
4. **Operations and quality:** infrastructure/special-program inventory, support health, backup/restore, and operational logs.
5. **Experience migration:** migrate the shared shell and modules to React one workflow at a time while preserving Flask authorization and parity.
6. **Reference review:** compare screenshots and task flows against SDMS once the public/authenticated reference can be inspected; adjust navigation, terminology, and layout based on observed evidence.

## Current implementation notes

- The repository already contains Flask workflows for students, admissions, academics, attendance/RFID, fees, library, welfare, behavior, messaging, and meetings.
- Academic-year, department, trade, class, term, and enrollment models plus a first migration/backfill already exist; coverage and continuing use need verification.
- Authenticated `/student/rfid-login` requests append scan events with server timestamps, reader ID, result, and duplicate status to `RFIDScanLog`; attendance corrections have a separate audit trail. This is event capture, not yet an official frozen daily report or revision workflow.
- React/Vite is an incremental migration, not a replacement backend. The current migration plan identifies the administrator dashboard as the first React screen.
- The FURPS targets above are proposed acceptance criteria; they are not claims about measured current performance or SDMS's private interface.

## Public reference sources

- [MINICT SDMS presentation](https://www.minict.gov.rw/index.php?eID=dumpFile&f=81880&t=f&token=322973ce89e8c60fcee16a12cd850aecf1aff9a7)
- [MINEDUC Education Statistical Yearbook 2023/24](https://www.mineduc.gov.rw/fileadmin/user_upload/Mineduc/Publications/REPORTS/Education_Statistics/Education_statistical_yearbook/Final_Education_Statistical_Yearbook_23_24.pdf)
- [Umwalimu SACCO SDMS fee-payment information](https://umwalimusacco.rw/?page_id=44)
