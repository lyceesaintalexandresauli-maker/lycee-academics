# Target Implementation Status

## Included in this package

- Existing Smart School application from the supplied ZIP.
- Existing RFID, attendance, academic, behavior, discipline, fees, library, meetings, messaging and learning modules.
- New relational `School`, `Department`, `Trade`, `SchoolClass`, `AcademicYear`, `AcademicTerm` models.
- New historical `AcademicEnrollment` model.
- Seed/backfill migration for the current Lycée de Muhura academic structure.
- Target-system architecture and implementation documentation.

## Next implementation milestones

- Wire enrollment into all student-facing and staff-facing queries.
- Replace legacy placement-only filtering with enrollment scope.
- Implement official daily RFID snapshot/reconciliation workflow.
- Add Patron/Matron welfare cases and submission workflow.
- Complete behavior scoring/trend/risk and disciplinary action workflow.
- Add school-wide analytics by department/trade/class/student.
- Implement the permission-aware School AI Assistant.

The AI layer should not be considered production-complete until its permission guard, data-source tracing and audit logging are implemented and tested.
