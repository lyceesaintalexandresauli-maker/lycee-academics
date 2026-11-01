# Patron and Matron Welfare Workflow

## Access matrix

| Role | Student scope | Read welfare history | Create welfare records | Record return | Submit daily report | Review reports |
| --- | --- | --- | --- | --- | --- | --- |
| Patron | Male students | Male students | Male students | Male students | Patron report only | Own report history |
| Matron | Female students | Female students | Female students | Female students | Matron report only | Own report history |
| Headteacher | All students | All students | No | No | No | All Patron/Matron reports |
| Super administrator | All students | All students | No | No | No | All Patron/Matron reports |

Scope checks run on the server for roster queries, record creation, return updates, and history URLs. Patrons and Matrons cannot open the general student directory/profile pages, which contain guardian contact and home-address data. Their attendance view is limited to the same gender scope; attendance remains read-only in this workflow.

## Workflow

- The Patron or Matron records sickness at school, sickness in hospital, sent-home status, authorized leave, welfare concerns, or critical incidents.
- Sent-home return dates are calculated from the recorded event date and the granted number of weeks (1–52). Authorized leave requires a named approver and a return date on or after the leave date.
- Active sickness, sent-home, and leave statuses must be resolved with a return/recovery action before another active status can be opened for that student. Welfare concerns and critical incidents can be closed with a required resolution/follow-up note.
- Critical incident records queue an in-app alert for the Headteacher and Super Administrator. A Patron/Matron can optionally request a private guardian notice on a record; configured email/SMS delivery follows the existing notification provider settings.
- Daily summaries use official attendance and welfare records. “Absent / not marked” is provisional until the normal attendance reconciliation closes the scan window. Late students count as Present and are also reported in the late total.
- A role can submit one report per date. The totals are stored as a snapshot; reports are retained after submission. Headteacher or Super Administrator review is recorded with reviewer, timestamp, comments, and an audit event.
- Record creation, returns, report submission/review, and restricted student-history views have audit events. There is no delete control for welfare records.

## Routes

| Route | Methods | Authorized roles | Purpose |
| --- | --- | --- | --- |
| `/welfare` | GET | Patron, Matron, Headteacher, Super Administrator | Scoped dashboard, daily summary, records and report history |
| `/welfare` | POST | Patron, Matron, Headteacher, Super Administrator | Patron/Matron record, return, report actions; leadership report review only |
| `/welfare/records/<student_id>` | GET | Patron, Matron, Headteacher, Super Administrator | Role-scoped welfare history and audit trail |

Every POST action performs a role check in addition to the route permission check. Changing a student or report ID does not expand access.

## Database

The `v20261027_02_patron_matron_welfare.py` migration creates these tables idempotently:

- `student_welfare_record`: welfare status, factual reason, authorization, expected and actual return, and reporter.
- `daily_welfare_report`: one report per role/date, snapshot totals, submission, and leadership review.
- `welfare_audit_event`: actor, action, related student/record/report, state snapshots, reason, and timestamp.

The application currently applies migrations during startup, matching the existing repository convention. Back up the database before deployment and verify the migration against the deployment database before enabling Patron/Matron accounts.
