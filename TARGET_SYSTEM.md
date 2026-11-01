# AI-Powered Smart School Management & Student Intelligence System

This package is the migration baseline for the official target architecture.

## Official direction

- RFID remains the primary physical school-attendance source.
- Academic Bridge is a competitor/reference baseline, not an implementation target to copy.
- The system evolves into a unified school management and student-intelligence platform.
- The first implementation milestone is the relational academic/enrollment foundation.

## Target hierarchy

School → Department → Trade → Class → Academic Year/Term → Student Enrollment

## Intelligence streams

1. Attendance — RFID and official daily reconciliation.
2. Welfare — Patron/Matron reporting.
3. Behavior — positive/concern/serious/critical conduct records and trends.
4. Discipline — Admin-reviewed interventions and disciplinary decisions.
5. Academics — assessments, marks, report cards and performance trends.
6. Fees, library, schedules and communication.
7. Analytics — school → department → trade → class → student.
8. School AI Assistant — permission-aware analysis, explanations, reports and early-warning support.

## This package

The existing application is preserved as the migration starting point. The new relational academic hierarchy and historical enrollment models are included without removing the legacy placement fields, so existing functionality can be migrated incrementally.

The academic foundation migration is:

`backend-app/migrations/versions/v20261031_01_academic_foundation.py`

The migration defines the school's current departments, trades and classes and provides a backfill helper for existing student records.

## Implementation order

1. Academic hierarchy + enrollment
2. RFID attendance + welfare reconciliation
3. Behavior + discipline intelligence
4. Academic workflow and analytics
5. Unified analytics dashboards
6. School AI Assistant
7. Security, audit, tests and production hardening
