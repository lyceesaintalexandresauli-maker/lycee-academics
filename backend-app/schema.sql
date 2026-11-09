a-- Schema-only export for the Lycee Academics SQLite database.
-- Contains table and index definitions only; no student or staff records.
-- Generated from backend-app/instance/lyceedemuhura.db.

PRAGMA foreign_keys = ON;

CREATE TABLE academic_enrollment (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	academic_year_id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	trade_id INTEGER NOT NULL, 
	class_id INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_enrollment_student_year UNIQUE (student_id, academic_year_id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(academic_year_id) REFERENCES academic_year (id), 
	FOREIGN KEY(department_id) REFERENCES department (id), 
	FOREIGN KEY(trade_id) REFERENCES trade (id), 
	FOREIGN KEY(class_id) REFERENCES school_class (id)
);

CREATE TABLE academic_subject (
	id INTEGER NOT NULL, 
	trade VARCHAR(100) NOT NULL, 
	level VARCHAR(50) NOT NULL, 
	class_name VARCHAR(100) NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	teacher_id INTEGER, 
	academic_year VARCHAR(9), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_academic_subject_class_year UNIQUE (class_name, subject, academic_year), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
);

CREATE TABLE academic_term (
	id INTEGER NOT NULL, 
	academic_year_id INTEGER NOT NULL, 
	name VARCHAR(50) NOT NULL, 
	sequence INTEGER NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_current BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_term_year_name UNIQUE (academic_year_id, name), 
	FOREIGN KEY(academic_year_id) REFERENCES academic_year (id)
);

CREATE TABLE academic_year (
	id INTEGER NOT NULL, 
	name VARCHAR(20) NOT NULL, 
	start_date DATE, 
	end_date DATE, 
	is_current BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
);

CREATE TABLE activity_log (
	id INTEGER NOT NULL, 
	actor_id INTEGER, 
	actor_name VARCHAR(160) NOT NULL, 
	student_id INTEGER, 
	student_name VARCHAR(160) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	details TEXT NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE admission_applicant (
	id INTEGER NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	guardian_name VARCHAR(160), 
	phone VARCHAR(40), 
	email VARCHAR(160), 
	desired_department VARCHAR(100), 
	desired_trade VARCHAR(100) NOT NULL, 
	desired_level VARCHAR(50) NOT NULL, 
	desired_class VARCHAR(100) NOT NULL, 
	documents_submitted TEXT, 
	documents_verified BOOLEAN NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	applied_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	converted_student_id INTEGER, 
	PRIMARY KEY (id), 
	UNIQUE (converted_student_id), 
	FOREIGN KEY(converted_student_id) REFERENCES user (id)
);

CREATE TABLE announcement (
	id INTEGER NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	body TEXT NOT NULL, 
	audience VARCHAR(30) NOT NULL, 
	is_published BOOLEAN NOT NULL, 
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	published_at DATETIME, 
	author_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(author_id) REFERENCES user (id)
);

CREATE TABLE appointment (
	id INTEGER NOT NULL, 
	visitor_name VARCHAR(160) NOT NULL, 
	visitor_phone VARCHAR(40), 
	visitor_email VARCHAR(160), 
	student_id INTEGER, 
	purpose VARCHAR(200) NOT NULL, 
	scheduled_date VARCHAR(10) NOT NULL, 
	scheduled_time VARCHAR(5) NOT NULL, 
	notes TEXT, 
	status VARCHAR(30) NOT NULL, 
	created_by INTEGER NOT NULL, 
	parent_id INTEGER, 
	staff_id INTEGER, 
	parent_attended BOOLEAN, 
	staff_attended BOOLEAN, 
	staff_notes TEXT, 
	decision_summary TEXT, 
	follow_up_actions TEXT, 
	follow_up_due_date VARCHAR(10), 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(created_by) REFERENCES user (id), 
	FOREIGN KEY(parent_id) REFERENCES user (id), 
	FOREIGN KEY(staff_id) REFERENCES user (id)
);

CREATE TABLE assessment (
	id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	assessment_type VARCHAR(20) NOT NULL, 
	class_name VARCHAR(100) NOT NULL, 
	target_student_ids TEXT, 
	rubric_id INTEGER, 
	time_limit_minutes INTEGER, 
	randomize_questions BOOLEAN NOT NULL, 
	focus_mode BOOLEAN NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	term VARCHAR(30) NOT NULL, 
	academic_year VARCHAR(9), 
	instructions TEXT, 
	media_url VARCHAR(1000), 
	due_at VARCHAR(19), 
	max_score FLOAT NOT NULL, 
	attachment_path VARCHAR(255), 
	attachment_name VARCHAR(255), 
	is_published BOOLEAN NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id), 
	FOREIGN KEY(rubric_id) REFERENCES grading_rubric (id)
);

CREATE TABLE assessment_attempt (
	id INTEGER NOT NULL, 
	assessment_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	started_at VARCHAR(19) NOT NULL, 
	question_order_json TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_assessment_student_attempt UNIQUE (assessment_id, student_id), 
	FOREIGN KEY(assessment_id) REFERENCES assessment (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE assessment_question (
	id INTEGER NOT NULL, 
	assessment_id INTEGER NOT NULL, 
	prompt TEXT NOT NULL, 
	question_type VARCHAR(30) NOT NULL, 
	options_json TEXT NOT NULL, 
	correct_answer TEXT NOT NULL, 
	media_url VARCHAR(1000), 
	points FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(assessment_id) REFERENCES assessment (id)
);

CREATE TABLE assessment_submission (
	id INTEGER NOT NULL, 
	assessment_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	submitted_at VARCHAR(19) NOT NULL, 
	answers_json TEXT, 
	auto_score FLOAT, 
	rubric_results_json TEXT, 
	focus_warnings INTEGER NOT NULL, 
	attachment_path VARCHAR(255), 
	attachment_name VARCHAR(255), 
	score FLOAT, 
	feedback TEXT, 
	is_graded BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_assessment_student_submission UNIQUE (assessment_id, student_id), 
	FOREIGN KEY(assessment_id) REFERENCES assessment (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE attendance (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	day VARCHAR(10) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	arrival_time VARCHAR(26), 
	afternoon_time VARCHAR(26), 
	source VARCHAR(30), 
	note VARCHAR(500), 
	edited_by INTEGER, 
	session_name VARCHAR(30), 
	device_id VARCHAR(64), 
	card_uid VARCHAR(100), 
	is_corrected BOOLEAN NOT NULL, 
	correction_reason TEXT, 
	corrected_at VARCHAR(26), 
	explanation TEXT, 
	explanation_approved_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(edited_by) REFERENCES user (id), 
	FOREIGN KEY(explanation_approved_by) REFERENCES user (id)
);

CREATE TABLE attendance_audit_trail (
	id INTEGER NOT NULL, 
	attendance_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	day VARCHAR(10) NOT NULL, 
	session_name VARCHAR(30), 
	old_status VARCHAR(30), 
	new_status VARCHAR(30) NOT NULL, 
	old_source VARCHAR(30), 
	new_source VARCHAR(30) NOT NULL, 
	changed_by_id INTEGER NOT NULL, 
	changed_at VARCHAR(26) NOT NULL, 
	reason TEXT NOT NULL, 
	ip_address VARCHAR(45), 
	PRIMARY KEY (id), 
	FOREIGN KEY(attendance_id) REFERENCES attendance (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(changed_by_id) REFERENCES user (id)
);

CREATE TABLE behavior_record (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	student_name VARCHAR(160) NOT NULL, 
	class_name VARCHAR(100), 
	department VARCHAR(100), 
	trade VARCHAR(100), 
	level VARCHAR(50), 
	academic_year VARCHAR(9), 
	reporter_id INTEGER NOT NULL, 
	reporter_role VARCHAR(30) NOT NULL, 
	record_type VARCHAR(20) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	description TEXT NOT NULL, 
	location VARCHAR(160), 
	action_taken TEXT, 
	follow_up_required BOOLEAN DEFAULT 0 NOT NULL, 
	follow_up_date VARCHAR(10), 
	parent_notification_required BOOLEAN DEFAULT 0 NOT NULL, 
	parent_notification_status VARCHAR(20) DEFAULT 'not_required' NOT NULL, 
	status VARCHAR(20) DEFAULT 'submitted' NOT NULL, 
	is_published BOOLEAN DEFAULT 0 NOT NULL, 
	resolution TEXT, 
	resolved_by_id INTEGER, 
	resolved_at VARCHAR(19), 
	created_at VARCHAR(19) NOT NULL, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_behavior_record_type CHECK (record_type IN ('Positive', 'Concern', 'Serious', 'Critical')), 
	CONSTRAINT ck_behavior_record_status CHECK (status IN ('submitted', 'under_review', 'resolved')), 
	FOREIGN KEY(student_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(reporter_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(resolved_by_id) REFERENCES user (id) ON DELETE RESTRICT
);

CREATE TABLE book (
	id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	category VARCHAR(100) NOT NULL, 
	quantity INTEGER, 
	available INTEGER, 
	PRIMARY KEY (id)
);

CREATE TABLE book_loan (
	id INTEGER NOT NULL, 
	book_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	borrowed_date DATE NOT NULL, 
	due_date DATE NOT NULL, 
	returned_date DATE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(book_id) REFERENCES book (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE correspondence (
	id INTEGER NOT NULL, 
	direction VARCHAR(20) NOT NULL, 
	reference_number VARCHAR(80) NOT NULL, 
	contact_name VARCHAR(180) NOT NULL, 
	subject VARCHAR(240) NOT NULL, 
	details TEXT, 
	letter_date VARCHAR(10) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	recorded_by INTEGER NOT NULL, 
	recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (reference_number), 
	FOREIGN KEY(recorded_by) REFERENCES user (id)
);

CREATE TABLE daily_welfare_report (
	id INTEGER NOT NULL, 
	reporter_role VARCHAR(30) NOT NULL, 
	reporter_id INTEGER NOT NULL, 
	report_date VARCHAR(10) NOT NULL, 
	total_students INTEGER NOT NULL, 
	sick_count INTEGER NOT NULL, 
	hospitalized_count INTEGER NOT NULL, 
	sent_home_count INTEGER NOT NULL, 
	follow_up_count INTEGER NOT NULL, 
	incident_count INTEGER NOT NULL, 
	observations TEXT NOT NULL, 
	recommended_actions TEXT, 
	serious_incidents TEXT, 
	submitted_at VARCHAR(19) NOT NULL, 
	reviewed_by_id INTEGER, 
	reviewed_at VARCHAR(19), 
	review_comments TEXT, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_daily_welfare_report_role_date UNIQUE (reporter_role, report_date), 
	FOREIGN KEY(reporter_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(reviewed_by_id) REFERENCES user (id) ON DELETE RESTRICT
);

CREATE TABLE day_schedule_entry (
	id INTEGER NOT NULL, 
	schedule_date DATE NOT NULL, 
	class_name VARCHAR(100), 
	start_time VARCHAR(20), 
	end_time VARCHAR(20), 
	activity VARCHAR(160) NOT NULL, 
	details TEXT, 
	is_published BOOLEAN NOT NULL, 
	created_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES user (id)
);

CREATE TABLE department (
	id INTEGER NOT NULL, 
	school_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	code VARCHAR(50), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_department_school_name UNIQUE (school_id, name), 
	FOREIGN KEY(school_id) REFERENCES school (id)
);

CREATE TABLE discipline_case (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	record_type VARCHAR(30) NOT NULL, 
	details TEXT NOT NULL, 
	action_taken TEXT, 
	remarks TEXT, 
	mark_deduction FLOAT, 
	is_published BOOLEAN NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE fee_requirement (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	title VARCHAR(120) NOT NULL, 
	amount FLOAT NOT NULL, 
	due_date DATE NOT NULL, 
	details TEXT, 
	created_by INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(created_by) REFERENCES user (id)
);

CREATE TABLE fee_transaction (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	requirement_id INTEGER, 
	total_fees FLOAT, 
	amount FLOAT NOT NULL, 
	method VARCHAR(40), 
	reference VARCHAR(100), 
	created_at VARCHAR(19) NOT NULL, reconciliation_status VARCHAR(20) NOT NULL DEFAULT 'confirmed', reconciled_by_id INTEGER REFERENCES user(id), reconciled_at VARCHAR(26), reconciliation_note TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(requirement_id) REFERENCES fee_requirement (id)
);

CREATE TABLE grade (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	subject VARCHAR(100) NOT NULL, 
	term VARCHAR(50), 
	academic_year VARCHAR(9), 
	module_code VARCHAR(40), 
	module_category VARCHAR(32), 
	module_weight FLOAT, 
	marks FLOAT NOT NULL, 
	max_marks FLOAT, 
	formative_marks FLOAT, 
	integrated_marks FLOAT, 
	comprehensive_marks FLOAT, 
	reassessment_marks FLOAT, 
	remarks TEXT, 
	is_published BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
);

CREATE TABLE grading_rubric (
	id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	description TEXT, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
);

CREATE TABLE grading_rubric_criterion (
	id INTEGER NOT NULL, 
	rubric_id INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	description TEXT, 
	max_points FLOAT NOT NULL, 
	position INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(rubric_id) REFERENCES grading_rubric (id)
);

CREATE TABLE learning_material (
	id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	resource_type VARCHAR(40) NOT NULL, 
	class_name VARCHAR(100) NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	description TEXT, 
	reference_content TEXT, 
	standards TEXT, 
	source_reference VARCHAR(500), 
	schematic_data TEXT, 
	external_url VARCHAR(1000), 
	activity_data TEXT, 
	attachment_path VARCHAR(255), 
	attachment_name VARCHAR(255), 
	is_published BOOLEAN NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
);

CREATE TABLE lesson_plan (
	id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	teacher_id INTEGER NOT NULL, 
	lesson_date DATE NOT NULL, 
	topic VARCHAR(180) NOT NULL, 
	objectives TEXT NOT NULL, 
	activities TEXT, 
	resources TEXT, 
	status VARCHAR(30) NOT NULL, 
	review_comment TEXT, 
	reviewed_by INTEGER, 
	submitted_at DATETIME NOT NULL, 
	reviewed_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(subject_id) REFERENCES academic_subject (id), 
	FOREIGN KEY(teacher_id) REFERENCES user (id), 
	FOREIGN KEY(reviewed_by) REFERENCES user (id)
);

CREATE TABLE meeting (
	id INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	description TEXT, 
	meeting_type VARCHAR(32) NOT NULL, 
	class_name VARCHAR(100), 
	student_id INTEGER, 
	organizer_id INTEGER NOT NULL, 
	chairperson_id INTEGER, 
	secretary_id INTEGER, 
	minutes_approver_id INTEGER, 
	scheduled_date VARCHAR(10) NOT NULL, 
	start_time VARCHAR(5) NOT NULL, 
	end_time VARCHAR(5) NOT NULL, 
	location VARCHAR(160), 
	status VARCHAR(24) NOT NULL, 
	approval_status VARCHAR(24) NOT NULL, 
	confidentiality VARCHAR(24) NOT NULL, 
	qa_duration_minutes INTEGER, 
	panel_perspectives VARCHAR(1000), 
	room_released_at VARCHAR(19), 
	room_release_reason VARCHAR(160), 
	microsoft_event_id VARCHAR(255), 
	microsoft_join_url VARCHAR(1000), 
	microsoft_sync_status VARCHAR(24) NOT NULL, 
	microsoft_sync_error VARCHAR(500), 
	created_at VARCHAR(19) NOT NULL, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(organizer_id) REFERENCES user (id), 
	FOREIGN KEY(chairperson_id) REFERENCES user (id), 
	FOREIGN KEY(secretary_id) REFERENCES user (id), 
	FOREIGN KEY(minutes_approver_id) REFERENCES user (id)
);

CREATE TABLE meeting_action_comment (
	id INTEGER NOT NULL, 
	action_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	body VARCHAR(2000) NOT NULL, 
	is_parent_visible BOOLEAN NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(action_id) REFERENCES meeting_action_item (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES user (id)
);

CREATE TABLE meeting_action_item (
	id INTEGER NOT NULL, 
	meeting_id INTEGER NOT NULL, 
	agenda_item_id INTEGER, 
	title VARCHAR(200) NOT NULL, 
	details TEXT, 
	assignee_id INTEGER NOT NULL, 
	assigned_by_id INTEGER NOT NULL, 
	deadline VARCHAR(10) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	completion_evidence TEXT, 
	review_outcome VARCHAR(1000), 
	is_parent_visible BOOLEAN NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE CASCADE, 
	FOREIGN KEY(agenda_item_id) REFERENCES meeting_agenda_item (id) ON DELETE SET NULL, 
	FOREIGN KEY(assignee_id) REFERENCES user (id), 
	FOREIGN KEY(assigned_by_id) REFERENCES user (id)
);

CREATE TABLE meeting_agenda_item (
	id INTEGER NOT NULL, 
	meeting_id INTEGER NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	details TEXT, 
	position INTEGER NOT NULL, 
	created_by_id INTEGER NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by_id) REFERENCES user (id)
);

CREATE TABLE meeting_attendance (
	id INTEGER NOT NULL, 
	participant_id INTEGER NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	representative_name VARCHAR(160), 
	representative_relationship VARCHAR(80), 
	verified_by_id INTEGER, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meeting_attendance_participant UNIQUE (participant_id), 
	FOREIGN KEY(participant_id) REFERENCES meeting_participant (id) ON DELETE CASCADE, 
	FOREIGN KEY(verified_by_id) REFERENCES user (id)
);

CREATE TABLE meeting_audit_event (
	id INTEGER NOT NULL, 
	meeting_id INTEGER, 
	actor_id INTEGER, 
	actor_name VARCHAR(160) NOT NULL, 
	actor_role VARCHAR(30) NOT NULL, 
	event_type VARCHAR(48) NOT NULL, 
	details TEXT NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	previous_hash VARCHAR(64) NOT NULL, 
	event_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE SET NULL, 
	FOREIGN KEY(actor_id) REFERENCES user (id), 
	UNIQUE (event_hash)
);

CREATE TABLE meeting_minutes (
	id INTEGER NOT NULL, 
	meeting_id INTEGER NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	current_version INTEGER NOT NULL, 
	submitted_by_id INTEGER, 
	submitted_at VARCHAR(19), 
	approved_by_id INTEGER, 
	approved_at VARCHAR(19), 
	approval_note VARCHAR(1000), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meeting_minutes_meeting UNIQUE (meeting_id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE CASCADE, 
	FOREIGN KEY(submitted_by_id) REFERENCES user (id), 
	FOREIGN KEY(approved_by_id) REFERENCES user (id)
);

CREATE TABLE meeting_minutes_revision (
	id INTEGER NOT NULL, 
	minutes_id INTEGER NOT NULL, 
	version INTEGER NOT NULL, 
	content TEXT NOT NULL, 
	author_id INTEGER NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	event VARCHAR(24) NOT NULL, 
	decision_note VARCHAR(1000), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meeting_minutes_revision UNIQUE (minutes_id, version), 
	FOREIGN KEY(minutes_id) REFERENCES meeting_minutes (id) ON DELETE CASCADE, 
	FOREIGN KEY(author_id) REFERENCES user (id)
);

CREATE TABLE meeting_notification_log (
	id INTEGER NOT NULL, 
	meeting_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	dedupe_key VARCHAR(120) NOT NULL, 
	in_app_status VARCHAR(20) NOT NULL, 
	external_status VARCHAR(20) NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meeting_notice_dedupe_user UNIQUE (dedupe_key, user_id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE meeting_participant (
	id INTEGER NOT NULL, 
	meeting_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	student_id INTEGER, 
	participant_role VARCHAR(32) NOT NULL, 
	invited_at VARCHAR(19) NOT NULL, 
	invitation_status VARCHAR(24) NOT NULL, 
	response_comment VARCHAR(1000), 
	responded_at VARCHAR(19), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_meeting_participant_user UNIQUE (meeting_id, user_id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE, 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE message_audit_event (
	id INTEGER NOT NULL, 
	actor_id INTEGER, 
	actor_name VARCHAR(160) NOT NULL, 
	actor_role VARCHAR(30) NOT NULL, 
	event_type VARCHAR(40) NOT NULL, 
	conversation_id INTEGER, 
	message_id INTEGER, 
	details TEXT NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	previous_hash VARCHAR(64) NOT NULL, 
	event_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (event_hash)
);

CREATE TABLE message_conversation (
	id INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	conversation_type VARCHAR(30) NOT NULL, 
	created_by_id INTEGER NOT NULL, 
	created_by_name VARCHAR(160) NOT NULL, 
	created_by_role VARCHAR(30) NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	meeting_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(meeting_id) REFERENCES meeting (id) ON DELETE SET NULL
);

CREATE TABLE message_participant (
	id INTEGER NOT NULL, 
	conversation_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	user_name VARCHAR(160) NOT NULL, 
	user_role VARCHAR(30) NOT NULL, 
	added_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_message_participant UNIQUE (conversation_id, user_id), 
	FOREIGN KEY(conversation_id) REFERENCES message_conversation (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE message_permission (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	can_send BOOLEAN NOT NULL, 
	updated_by_id INTEGER NOT NULL, 
	updated_by_name VARCHAR(160) NOT NULL, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE message_report (
	id INTEGER NOT NULL, 
	message_id INTEGER NOT NULL, 
	reporter_id INTEGER, 
	reporter_name VARCHAR(160) NOT NULL, 
	reporter_role VARCHAR(30) NOT NULL, 
	reason VARCHAR(1000) NOT NULL, 
	status VARCHAR(20) DEFAULT 'open' NOT NULL, 
	resolution VARCHAR(1000), 
	reviewed_by_id INTEGER, 
	reviewed_by_name VARCHAR(160), 
	created_at VARCHAR(19) NOT NULL, 
	reviewed_at VARCHAR(19), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_message_reporter UNIQUE (message_id, reporter_id), 
	FOREIGN KEY(message_id) REFERENCES school_message (id), 
	FOREIGN KEY(reporter_id) REFERENCES user (id) ON DELETE SET NULL
);

CREATE TABLE official_notice (
	id INTEGER NOT NULL, 
	created_by_id INTEGER, 
	created_by_name VARCHAR(160) NOT NULL, 
	created_by_role VARCHAR(30) NOT NULL, 
	subject VARCHAR(160) NOT NULL, 
	body TEXT NOT NULL, 
	recipient_ids_json TEXT NOT NULL, 
	category VARCHAR(40) DEFAULT 'general' NOT NULL, 
	is_sensitive BOOLEAN DEFAULT 0 NOT NULL, 
	status VARCHAR(32) DEFAULT 'pending_approval' NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	approved_by_id INTEGER, 
	approved_by_name VARCHAR(160), 
	approved_by_role VARCHAR(30), 
	approved_at VARCHAR(19), 
	sensitive_approved_by_id INTEGER, 
	sensitive_approved_by_name VARCHAR(160), 
	sensitive_approved_by_role VARCHAR(30), 
	sensitive_approved_at VARCHAR(19), 
	published_by_id INTEGER, 
	published_by_name VARCHAR(160), 
	published_by_role VARCHAR(30), 
	published_at VARCHAR(19), 
	revoked_by_id INTEGER, 
	revoked_by_name VARCHAR(160), 
	revoked_by_role VARCHAR(30), 
	revoked_at VARCHAR(19), 
	rejected_by_id INTEGER, 
	rejected_by_name VARCHAR(160), 
	rejected_by_role VARCHAR(30), 
	rejected_at VARCHAR(19), 
	decision_note VARCHAR(1000), 
	PRIMARY KEY (id)
);

CREATE TABLE official_notice_audit_event (
	id INTEGER NOT NULL, 
	notice_id INTEGER, 
	actor_id INTEGER, 
	actor_name VARCHAR(160) NOT NULL, 
	actor_role VARCHAR(30) NOT NULL, 
	event_type VARCHAR(40) NOT NULL, 
	details TEXT NOT NULL, 
	created_at VARCHAR(19) NOT NULL, 
	previous_hash VARCHAR(64) NOT NULL, 
	event_hash VARCHAR(64) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (event_hash)
);

CREATE TABLE official_notice_permission (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	can_create BOOLEAN DEFAULT 0 NOT NULL, 
	can_approve BOOLEAN DEFAULT 0 NOT NULL, 
	can_approve_sensitive BOOLEAN DEFAULT 0 NOT NULL, 
	can_publish BOOLEAN DEFAULT 0 NOT NULL, 
	can_revoke BOOLEAN DEFAULT 0 NOT NULL, 
	updated_by_id INTEGER, 
	updated_by_name VARCHAR(160), 
	updated_at VARCHAR(19), 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE parent_notification_preference (
	id INTEGER NOT NULL, 
	parent_id INTEGER NOT NULL, 
	email_enabled BOOLEAN NOT NULL, 
	sms_enabled BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(parent_id) REFERENCES user (id)
);

CREATE TABLE pending_card (
	id INTEGER NOT NULL, 
	uid VARCHAR(100) NOT NULL, 
	first_seen VARCHAR(19) NOT NULL, 
	last_seen VARCHAR(26), 
	state VARCHAR(30), 
	PRIMARY KEY (id), 
	UNIQUE (uid)
);

CREATE TABLE report_card_approval (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	academic_year VARCHAR(9) NOT NULL, 
	confirmed_by INTEGER NOT NULL, 
	confirmed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_report_approval_student_year UNIQUE (student_id, academic_year), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(confirmed_by) REFERENCES user (id)
);

CREATE TABLE rfid_card (
	id INTEGER NOT NULL, 
	card_uid VARCHAR(100) NOT NULL, 
	student_id INTEGER, 
	status VARCHAR(30) NOT NULL, 
	issued_at VARCHAR(26), 
	deactivated_at VARCHAR(26), 
	deactivation_reason VARCHAR(255), 
	replaced_by_card_id INTEGER, 
	notes TEXT, 
	created_at VARCHAR(26), 
	updated_at VARCHAR(26), 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(replaced_by_card_id) REFERENCES rfid_card (id)
);

CREATE TABLE rfid_device (
	id INTEGER NOT NULL, 
	device_id VARCHAR(64) NOT NULL, 
	device_name VARCHAR(100) NOT NULL, 
	device_token VARCHAR(128) NOT NULL, 
	location VARCHAR(120) NOT NULL, 
	device_type VARCHAR(50) NOT NULL, 
	assigned_class VARCHAR(100), 
	allowed_sessions VARCHAR(100), 
	is_active BOOLEAN NOT NULL, 
	last_seen VARCHAR(26), 
	last_ip VARCHAR(45), 
	firmware_version VARCHAR(50), 
	created_at VARCHAR(26), 
	PRIMARY KEY (id)
);

CREATE TABLE rfid_scan_log (
	id INTEGER NOT NULL, 
	card_uid VARCHAR(100) NOT NULL, 
	student_id INTEGER, 
	device_id VARCHAR(64), 
	day VARCHAR(10) NOT NULL, 
	scanned_at VARCHAR(26) NOT NULL, 
	scan_clock VARCHAR(8) NOT NULL, 
	session_name VARCHAR(30) NOT NULL, 
	status_result VARCHAR(50) NOT NULL, 
	is_duplicate BOOLEAN NOT NULL, 
	message VARCHAR(255), 
	raw_payload TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);

CREATE TABLE room_reservation (
	id INTEGER NOT NULL, 
	room_name VARCHAR(160) NOT NULL, 
	purpose VARCHAR(160) NOT NULL, 
	reserved_by_id INTEGER NOT NULL, 
	starts_at DATETIME NOT NULL, 
	ends_at DATETIME NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	created_at DATETIME NOT NULL, 
	released_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(reserved_by_id) REFERENCES user (id) ON DELETE CASCADE
);

CREATE TABLE school (
	id INTEGER NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	code VARCHAR(50), 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	UNIQUE (code)
);

CREATE TABLE school_class (
	id INTEGER NOT NULL, 
	trade_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	level VARCHAR(30) NOT NULL, 
	code VARCHAR(80), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_class_trade_name UNIQUE (trade_id, name), 
	FOREIGN KEY(trade_id) REFERENCES trade (id), 
	UNIQUE (code)
);

CREATE TABLE school_message (
	id INTEGER NOT NULL, 
	sender_id INTEGER NOT NULL, 
	sender_name VARCHAR(160), 
	sender_role VARCHAR(30), 
	recipient_id INTEGER, 
	recipient_role VARCHAR(30), 
	subject VARCHAR(160) NOT NULL, 
	body TEXT NOT NULL, 
	message_type VARCHAR(24) DEFAULT 'general' NOT NULL, 
	conversation_id INTEGER, 
	in_reply_to_id INTEGER, 
	approval_status VARCHAR(20) DEFAULT 'approved' NOT NULL, 
	approved_by_id INTEGER, 
	approved_by_name VARCHAR(160), 
	approved_at VARCHAR(19), 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(sender_id) REFERENCES user (id), 
	FOREIGN KEY(recipient_id) REFERENCES user (id), 
	FOREIGN KEY(conversation_id) REFERENCES message_conversation (id), 
	FOREIGN KEY(in_reply_to_id) REFERENCES school_message (id)
);

CREATE TABLE setting (
	id INTEGER NOT NULL, 
	"key" VARCHAR(80) NOT NULL, 
	value VARCHAR(80) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE ("key")
);

CREATE TABLE student_document (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	uploaded_by INTEGER NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	stored_name VARCHAR(80) NOT NULL, 
	category VARCHAR(80) NOT NULL, 
	uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(uploaded_by) REFERENCES user (id), 
	UNIQUE (stored_name)
);

CREATE TABLE student_guardian (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	guardian_id INTEGER NOT NULL, 
	relationship VARCHAR(80) NOT NULL, 
	status VARCHAR(20) DEFAULT 'verified' NOT NULL, 
	verified_by_id INTEGER, 
	verified_at VARCHAR(19) NOT NULL, 
	revoked_by_id INTEGER, 
	revoked_at VARCHAR(19), 
	PRIMARY KEY (id), 
	CONSTRAINT uq_student_guardian UNIQUE (student_id, guardian_id), 
	FOREIGN KEY(student_id) REFERENCES user (id) ON DELETE CASCADE, 
	FOREIGN KEY(guardian_id) REFERENCES user (id) ON DELETE CASCADE, 
	FOREIGN KEY(verified_by_id) REFERENCES user (id), 
	FOREIGN KEY(revoked_by_id) REFERENCES user (id)
);

CREATE TABLE student_welfare_record (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	student_name VARCHAR(160) NOT NULL, 
	class_name VARCHAR(100), 
	gender VARCHAR(30), 
	reporter_id INTEGER NOT NULL, 
	reporter_role VARCHAR(30) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	case_state VARCHAR(24) DEFAULT 'open' NOT NULL, 
	details TEXT NOT NULL, 
	authorization_by VARCHAR(160), 
	authorization_note TEXT, 
	event_date VARCHAR(10) NOT NULL, 
	expected_return_date VARCHAR(10), 
	actual_return_date VARCHAR(10), 
	follow_up_required BOOLEAN DEFAULT 0 NOT NULL, 
	follow_up_date VARCHAR(10), 
	follow_up_notes TEXT, 
	notify_guardian BOOLEAN DEFAULT 0 NOT NULL, 
	is_urgent BOOLEAN DEFAULT 0 NOT NULL, 
	requires_admin_approval BOOLEAN DEFAULT 0 NOT NULL, 
	approval_status VARCHAR(20) DEFAULT 'not_required' NOT NULL, 
	approved_by_id INTEGER, 
	approved_at VARCHAR(19), 
	approval_note TEXT, 
	info_request TEXT, 
	info_response TEXT, 
	assigned_to_id INTEGER, 
	assigned_note TEXT, 
	reviewed_by_id INTEGER, 
	reviewed_at VARCHAR(19), 
	resolved_by_id INTEGER, 
	resolved_at VARCHAR(19), 
	resolution_note TEXT, 
	created_at VARCHAR(19) NOT NULL, 
	updated_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_welfare_record_status CHECK (status IN ('sick_at_school','hospitalized','sent_home','authorized_leave','welfare_concern','emergency','misconduct_report')), 
	CONSTRAINT ck_welfare_record_case_state CHECK (case_state IN ('open','follow_up','awaiting_info','awaiting_approval','resolved')), 
	FOREIGN KEY(student_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(reporter_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(approved_by_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(assigned_to_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(reviewed_by_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(resolved_by_id) REFERENCES user (id) ON DELETE RESTRICT
);

CREATE TABLE syllabus_coverage (
	id INTEGER NOT NULL, 
	subject_id INTEGER NOT NULL, 
	unit_title VARCHAR(180) NOT NULL, 
	planned_lessons INTEGER NOT NULL, 
	completed_lessons INTEGER NOT NULL, 
	notes TEXT, 
	updated_by INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_syllabus_unit_subject UNIQUE (subject_id, unit_title), 
	FOREIGN KEY(subject_id) REFERENCES academic_subject (id), 
	FOREIGN KEY(updated_by) REFERENCES user (id)
);

CREATE TABLE timetable_entry (
	id INTEGER NOT NULL, 
	class_name VARCHAR(100) NOT NULL, 
	day_of_week VARCHAR(20) NOT NULL, 
	time_slot VARCHAR(50) NOT NULL, 
	subject VARCHAR(100) NOT NULL, 
	teacher_name VARCHAR(160), 
	PRIMARY KEY (id)
);

CREATE TABLE trade (
	id INTEGER NOT NULL, 
	department_id INTEGER NOT NULL, 
	name VARCHAR(160) NOT NULL, 
	code VARCHAR(50), 
	is_active BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_trade_department_name UNIQUE (department_id, name), 
	FOREIGN KEY(department_id) REFERENCES department (id)
);

CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	full_name VARCHAR(160) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(30) NOT NULL, 
	email VARCHAR(160), 
	phone VARCHAR(40), 
	date_of_birth DATE, 
	gender VARCHAR(30), 
	academic_year VARCHAR(9), 
	guardian_name VARCHAR(160), 
	guardian_relationship VARCHAR(80), 
	guardian_phone VARCHAR(40), 
	address VARCHAR(500), 
	emergency_contact_name VARCHAR(160), 
	emergency_contact_phone VARCHAR(40), 
	emergency_contact_relationship VARCHAR(80), 
	department VARCHAR(100), 
	level VARCHAR(50), 
	trade VARCHAR(100), 
	class_name VARCHAR(100), 
	sdms_code VARCHAR(32), 
	profile_photo VARCHAR(255), 
	rfid_uid VARCHAR(100), 
	parent_id INTEGER, 
	is_active_account BOOLEAN, 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email), 
	UNIQUE (sdms_code), 
	UNIQUE (rfid_uid), 
	FOREIGN KEY(parent_id) REFERENCES user (id)
);

CREATE TABLE user_notification (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	body TEXT NOT NULL, 
	link VARCHAR(255), 
	created_at VARCHAR(19) NOT NULL, 
	is_read BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);

CREATE TABLE welfare_audit_event (
	id INTEGER NOT NULL, 
	actor_id INTEGER NOT NULL, 
	actor_name VARCHAR(160) NOT NULL, 
	action VARCHAR(80) NOT NULL, 
	student_id INTEGER, 
	record_id INTEGER, 
	report_id INTEGER, 
	before_state VARCHAR(80), 
	after_state VARCHAR(80), 
	reason TEXT, 
	created_at VARCHAR(19) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(student_id) REFERENCES user (id) ON DELETE RESTRICT, 
	FOREIGN KEY(record_id) REFERENCES student_welfare_record (id) ON DELETE RESTRICT, 
	FOREIGN KEY(report_id) REFERENCES daily_welfare_report (id) ON DELETE RESTRICT
);

CREATE INDEX ix_academic_enrollment_academic_year_id ON academic_enrollment (academic_year_id);

CREATE INDEX ix_academic_enrollment_class_id ON academic_enrollment (class_id);

CREATE INDEX ix_academic_enrollment_department_id ON academic_enrollment (department_id);

CREATE INDEX ix_academic_enrollment_student_id ON academic_enrollment (student_id);

CREATE INDEX ix_academic_enrollment_trade_id ON academic_enrollment (trade_id);

CREATE INDEX ix_academic_subject_class_name ON academic_subject (class_name);

CREATE INDEX ix_academic_subject_teacher_id ON academic_subject (teacher_id);

CREATE INDEX ix_academic_term_academic_year_id ON academic_term (academic_year_id);

CREATE INDEX ix_activity_log_action ON activity_log (action);

CREATE INDEX ix_activity_log_created_at ON activity_log (created_at);

CREATE INDEX ix_activity_log_student_id ON activity_log (student_id);

CREATE INDEX ix_admission_applicant_status ON admission_applicant (status);

CREATE INDEX ix_announcement_audience ON announcement (audience);

CREATE INDEX ix_announcement_is_published ON announcement (is_published);

CREATE INDEX ix_appointment_parent_id ON appointment (parent_id);

CREATE INDEX ix_appointment_scheduled_date ON appointment (scheduled_date);

CREATE INDEX ix_appointment_staff_id ON appointment (staff_id);

CREATE INDEX ix_appointment_status ON appointment (status);

CREATE INDEX ix_appointment_student_id ON appointment (student_id);

CREATE INDEX ix_assessment_attempt_assessment_id ON assessment_attempt (assessment_id);

CREATE INDEX ix_assessment_attempt_student_id ON assessment_attempt (student_id);

CREATE INDEX ix_assessment_class_name ON assessment (class_name);

CREATE INDEX ix_assessment_question_assessment_id ON assessment_question (assessment_id);

CREATE INDEX ix_assessment_submission_assessment_id ON assessment_submission (assessment_id);

CREATE INDEX ix_assessment_submission_student_id ON assessment_submission (student_id);

CREATE INDEX ix_assessment_teacher_id ON assessment (teacher_id);

CREATE INDEX ix_attendance_audit_trail_attendance_id ON attendance_audit_trail (attendance_id);

CREATE INDEX ix_attendance_audit_trail_day ON attendance_audit_trail (day);

CREATE INDEX ix_attendance_audit_trail_student_id ON attendance_audit_trail (student_id);

CREATE INDEX ix_attendance_day ON attendance (day);

CREATE INDEX ix_behavior_record_class_name ON behavior_record (class_name);

CREATE INDEX ix_behavior_record_created_at ON behavior_record (created_at);

CREATE INDEX ix_behavior_record_is_published ON behavior_record (is_published);

CREATE INDEX ix_behavior_record_record_type ON behavior_record (record_type);

CREATE INDEX ix_behavior_record_reporter_id ON behavior_record (reporter_id);

CREATE INDEX ix_behavior_record_status ON behavior_record (status);

CREATE INDEX ix_behavior_record_student_id ON behavior_record (student_id);

CREATE INDEX ix_book_loan_book_id ON book_loan (book_id);

CREATE INDEX ix_book_loan_student_id ON book_loan (student_id);

CREATE INDEX ix_correspondence_direction ON correspondence (direction);

CREATE INDEX ix_correspondence_letter_date ON correspondence (letter_date);

CREATE INDEX ix_correspondence_status ON correspondence (status);

CREATE INDEX ix_daily_welfare_report_report_date ON daily_welfare_report (report_date);

CREATE INDEX ix_daily_welfare_report_reporter_id ON daily_welfare_report (reporter_id);

CREATE INDEX ix_daily_welfare_report_reporter_role ON daily_welfare_report (reporter_role);

CREATE INDEX ix_day_schedule_entry_schedule_date ON day_schedule_entry (schedule_date);

CREATE INDEX ix_department_school_id ON department (school_id);

CREATE INDEX ix_fee_requirement_student_id ON fee_requirement (student_id);

CREATE INDEX ix_grading_rubric_criterion_rubric_id ON grading_rubric_criterion (rubric_id);

CREATE INDEX ix_grading_rubric_teacher_id ON grading_rubric (teacher_id);

CREATE INDEX ix_learning_material_class_name ON learning_material (class_name);

CREATE INDEX ix_learning_material_teacher_id ON learning_material (teacher_id);

CREATE INDEX ix_lesson_plan_subject_id ON lesson_plan (subject_id);

CREATE INDEX ix_lesson_plan_teacher_id ON lesson_plan (teacher_id);

CREATE INDEX ix_meeting_action_comment_action_id ON meeting_action_comment (action_id);

CREATE INDEX ix_meeting_action_item_agenda_item_id ON meeting_action_item (agenda_item_id);

CREATE INDEX ix_meeting_action_item_assignee_id ON meeting_action_item (assignee_id);

CREATE INDEX ix_meeting_action_item_deadline ON meeting_action_item (deadline);

CREATE INDEX ix_meeting_action_item_meeting_id ON meeting_action_item (meeting_id);

CREATE INDEX ix_meeting_action_item_status ON meeting_action_item (status);

CREATE INDEX ix_meeting_agenda_item_meeting_id ON meeting_agenda_item (meeting_id);

CREATE INDEX ix_meeting_approval_status ON meeting (approval_status);

CREATE INDEX ix_meeting_attendance_participant_id ON meeting_attendance (participant_id);

CREATE INDEX ix_meeting_audit_event_actor_id ON meeting_audit_event (actor_id);

CREATE INDEX ix_meeting_audit_event_event_type ON meeting_audit_event (event_type);

CREATE INDEX ix_meeting_audit_event_meeting_id ON meeting_audit_event (meeting_id);

CREATE INDEX ix_meeting_chairperson_id ON meeting (chairperson_id);

CREATE INDEX ix_meeting_class_name ON meeting (class_name);

CREATE INDEX ix_meeting_meeting_type ON meeting (meeting_type);

CREATE INDEX ix_meeting_minutes_approver_id ON meeting (minutes_approver_id);

CREATE INDEX ix_meeting_minutes_meeting_id ON meeting_minutes (meeting_id);

CREATE INDEX ix_meeting_minutes_revision_minutes_id ON meeting_minutes_revision (minutes_id);

CREATE INDEX ix_meeting_minutes_status ON meeting_minutes (status);

CREATE INDEX ix_meeting_notification_log_meeting_id ON meeting_notification_log (meeting_id);

CREATE INDEX ix_meeting_notification_log_user_id ON meeting_notification_log (user_id);

CREATE INDEX ix_meeting_organizer_id ON meeting (organizer_id);

CREATE INDEX ix_meeting_participant_invitation_status ON meeting_participant (invitation_status);

CREATE INDEX ix_meeting_participant_meeting_id ON meeting_participant (meeting_id);

CREATE INDEX ix_meeting_participant_student_id ON meeting_participant (student_id);

CREATE INDEX ix_meeting_participant_user_id ON meeting_participant (user_id);

CREATE INDEX ix_meeting_scheduled_date ON meeting (scheduled_date);

CREATE INDEX ix_meeting_secretary_id ON meeting (secretary_id);

CREATE INDEX ix_meeting_status ON meeting (status);

CREATE INDEX ix_meeting_student_id ON meeting (student_id);

CREATE INDEX ix_message_audit_event_conversation_id ON message_audit_event (conversation_id);

CREATE INDEX ix_message_audit_event_event_type ON message_audit_event (event_type);

CREATE INDEX ix_message_audit_event_message_id ON message_audit_event (message_id);

CREATE UNIQUE INDEX ix_message_conversation_meeting_id ON message_conversation (meeting_id);

CREATE INDEX ix_message_participant_conversation_id ON message_participant (conversation_id);

CREATE INDEX ix_message_participant_user_id ON message_participant (user_id);

CREATE UNIQUE INDEX ix_message_permission_user_id ON message_permission (user_id);

CREATE INDEX ix_message_report_message_id ON message_report (message_id);

CREATE INDEX ix_message_report_reporter_id ON message_report (reporter_id);

CREATE INDEX ix_official_notice_audit_event_event_type ON official_notice_audit_event (event_type);

CREATE INDEX ix_official_notice_audit_event_notice_id ON official_notice_audit_event (notice_id);

CREATE INDEX ix_official_notice_created_by_id ON official_notice (created_by_id);

CREATE UNIQUE INDEX ix_official_notice_permission_user_id ON official_notice_permission (user_id);

CREATE INDEX ix_official_notice_status ON official_notice (status);

CREATE UNIQUE INDEX ix_parent_notification_preference_parent_id ON parent_notification_preference (parent_id);

CREATE INDEX ix_report_card_approval_student_id ON report_card_approval (student_id);

CREATE UNIQUE INDEX ix_rfid_card_card_uid ON rfid_card (card_uid);

CREATE INDEX ix_rfid_card_student_id ON rfid_card (student_id);

CREATE UNIQUE INDEX ix_rfid_device_device_id ON rfid_device (device_id);

CREATE INDEX ix_rfid_scan_log_card_uid ON rfid_scan_log (card_uid);

CREATE INDEX ix_rfid_scan_log_day ON rfid_scan_log (day);

CREATE INDEX ix_rfid_scan_log_device_id ON rfid_scan_log (device_id);

CREATE INDEX ix_rfid_scan_log_student_id ON rfid_scan_log (student_id);

CREATE INDEX ix_room_reservation_ends_at ON room_reservation (ends_at);

CREATE INDEX ix_room_reservation_reserved_by_id ON room_reservation (reserved_by_id);

CREATE INDEX ix_room_reservation_room_name ON room_reservation (room_name);

CREATE INDEX ix_room_reservation_starts_at ON room_reservation (starts_at);

CREATE INDEX ix_room_reservation_status ON room_reservation (status);

CREATE INDEX ix_school_class_trade_id ON school_class (trade_id);

CREATE INDEX ix_school_message_conversation_id ON school_message (conversation_id);

CREATE INDEX ix_school_message_in_reply_to_id ON school_message (in_reply_to_id);

CREATE INDEX ix_student_document_student_id ON student_document (student_id);

CREATE INDEX ix_student_guardian_guardian_id ON student_guardian (guardian_id);

CREATE INDEX ix_student_guardian_status ON student_guardian (status);

CREATE INDEX ix_student_guardian_student_id ON student_guardian (student_id);

CREATE INDEX ix_student_welfare_record_case_state ON student_welfare_record (case_state);

CREATE INDEX ix_student_welfare_record_class_name ON student_welfare_record (class_name);

CREATE INDEX ix_student_welfare_record_created_at ON student_welfare_record (created_at);

CREATE INDEX ix_student_welfare_record_event_date ON student_welfare_record (event_date);

CREATE INDEX ix_student_welfare_record_follow_up_date ON student_welfare_record (follow_up_date);

CREATE INDEX ix_student_welfare_record_is_urgent ON student_welfare_record (is_urgent);

CREATE INDEX ix_student_welfare_record_reporter_id ON student_welfare_record (reporter_id);

CREATE INDEX ix_student_welfare_record_reporter_role ON student_welfare_record (reporter_role);

CREATE INDEX ix_student_welfare_record_status ON student_welfare_record (status);

CREATE INDEX ix_student_welfare_record_student_id ON student_welfare_record (student_id);

CREATE INDEX ix_syllabus_coverage_subject_id ON syllabus_coverage (subject_id);

CREATE INDEX ix_trade_department_id ON trade (department_id);

CREATE INDEX ix_user_notification_user_id ON user_notification (user_id);

CREATE INDEX ix_welfare_audit_event_action ON welfare_audit_event (action);

CREATE INDEX ix_welfare_audit_event_actor_id ON welfare_audit_event (actor_id);

CREATE INDEX ix_welfare_audit_event_created_at ON welfare_audit_event (created_at);

CREATE INDEX ix_welfare_audit_event_record_id ON welfare_audit_event (record_id);

CREATE INDEX ix_welfare_audit_event_report_id ON welfare_audit_event (report_id);

CREATE INDEX ix_welfare_audit_event_student_id ON welfare_audit_event (student_id);

CREATE UNIQUE INDEX ux_user_sdms_code ON "user" (sdms_code);

CREATE TABLE class_module (
    id INTEGER NOT NULL,
    class_id INTEGER NOT NULL,
    code VARCHAR(32) NOT NULL,
    title VARCHAR(200) NOT NULL,
    category VARCHAR(1) NOT NULL,
    hours INTEGER NOT NULL,
    teacher_id INTEGER,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_by_id INTEGER NOT NULL,
    created_at DATETIME NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_class_module_code UNIQUE (class_id, code),
    CONSTRAINT ck_class_module_category CHECK (category IN ('C', 'G', 'S')),
    CONSTRAINT ck_class_module_hours CHECK (hours >= 0),
    FOREIGN KEY(class_id) REFERENCES school_class (id) ON DELETE CASCADE,
    FOREIGN KEY(teacher_id) REFERENCES user (id),
    FOREIGN KEY(created_by_id) REFERENCES user (id)
);

CREATE INDEX ix_class_module_class_id ON class_module (class_id);
CREATE INDEX ix_class_module_teacher_id ON class_module (teacher_id);
