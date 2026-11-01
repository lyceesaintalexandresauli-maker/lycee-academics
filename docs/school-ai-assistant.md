# School Assistant

## Current implementation

The assistant is a read-only, authenticated interface at `/ai-assistant`. Its JSON endpoint is `POST /api/ai/chat`, with a JSON body containing `message` and an `X-CSRF-Token` header issued in the page session. Requests are limited to 1,200 characters and 10 requests per user per minute. The endpoint accepts no client-supplied role, account ID, or student ID as an authorization input.

The application maps questions to a fixed set of server-side tools. Tools query existing records and apply the signed-in role's scope before returning summaries. Intent matching recognizes English school-topic terms and common synonyms; short follow-up questions can reuse the active chat's previous user questions to retain the topic and filters. The browser keeps up to eight user turns in memory and sends them with the next question. The server uses prior user questions only, re-runs authorization for every request, and does not persist the conversation. Assistant replies supplied by a client are not used as context. This is bounded rule-based dialogue, not a general-purpose conversational model. Out-of-scope or unrecognized questions receive a bounded explanation. Answers include their record source labels and explicitly identify when an attendance summary uses only recorded days.

The composer supports speech-to-text through the browser's Web Speech API when available. Microphone permission is required. Recognition is processed by the browser and may use its configured speech service; audio is not sent to this Flask endpoint. The transcription is inserted as editable text and is only sent after the user submits it. Voice recognition follows the selected English, French, or Kinyarwanda locale when the browser supports it. Use HTTPS (or localhost) for microphone access.

## Role scope

| Role | Available topics and record scope |
| --- | --- |
| Student | Own published grades and assessments, attendance, timetable, conduct reports released to the student, fees, library loans, announcements, and own notifications |
| Parent / Guardian | Verified linked children only; published academic records and assessments, attendance, timetable, released conduct reports, fees and library loans, announcements, and own notifications |
| Teacher | Assigned classes/students and teacher-owned grade/assessment records, plus attendance, conduct, timetable and class summaries |
| Patron / Matron | Students within the existing gender-based role scope, attendance, timetable, conduct, and authorized welfare summaries |
| Headteacher | School-wide academic, attendance, registration, conduct, welfare, and RFID summaries |
| Super Administrator | Headteacher summaries plus system account totals |
| Secretary | Attendance and registration summaries, timetable, announcements, and notifications |
| Accountant | Fee summaries and own timetable, announcements, and notifications |
| Librarian | Library loans, attendance, timetable, announcements, and notifications |
| Discipline staff | School-wide attendance and conduct records, matching the current discipline dashboard scope |

Welfare records are not exposed to parents because the current schema does not have an explicit parent-visible authorization flag. Parent-specific disclosure needs a school policy and an explicit data model before implementation.

## Provider configuration and privacy

The local factual tools work with `AI_PROVIDER_ENABLED=false`; no external AI provider is required. If an OpenAI-compatible endpoint is configured, the provider receives only a topic label and aggregate counts to produce an optional, clearly labeled suggestion. It does not receive the user's raw question, names, student IDs, or underlying rows. Provider output cannot invoke a tool or change a record. Keep the provider disabled unless the school approves the endpoint and its data handling.

The `ai_interaction_log` table records the user ID and role, matched topic/tool, aggregate count/date metadata, provider status, and request status. It deliberately excludes question and answer text. Logs are retained until removed under the school's database retention process; this first slice does not yet provide a configurable retention job or audit-log export screen.

## Schema and deployment

Migration `v20261027_03_school_ai_assistant.py` creates the `ai_interaction_log` table. The application also registers this table with its existing startup migration path. Install the existing `httpx` dependency only if the optional provider is used. Add provider values as deployment environment variables; do not commit credentials in `.env.example` or source control.

## Limits and next steps

- The assistant does not create, edit, approve, publish, send, or delete school data.
- It does not replace official report cards, attendance reconciliation, or professional review.
- Natural-language topic detection and date ranges are intentionally limited. Conversation context lives only in the active page and resets on refresh or New chat; speech recognition depends on browser support and its configured speech service.
- RFID reporting can count pending unassigned cards but cannot report device failures because the application does not currently persist structured scan-error events.
- Before production use, verify each school role's meaning and class assignment policy, decide data retention and parent welfare visibility, and test the deployed database migration and authorization paths.
