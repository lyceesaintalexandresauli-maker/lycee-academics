"""Master Administrator analytics dashboard (weducation + HR-analytics layout)."""

from __future__ import annotations

import datetime
import json

from flask_login import current_user
from markupsafe import escape

from app.extensions import db
from app.models import (
    AdmissionApplicant,
    Attendance,
    DayScheduleEntry,
    DisciplineCase,
    FeeTransaction,
    Meeting,
    PendingCard,
    User,
)
from app.routes.dashboard import (
    _admin_age_buckets,
    _admin_month_calendar,
    _admin_pair_lists,
    _admin_rate_bars,
    _admin_ring_svg,
)
from app.utils.rendering import page


CHART_COLORS = [
    "#2563eb", "#22c55e", "#8b5cf6", "#f97316", "#ff4c61",
    "#06b6d4", "#eab308", "#64748b",
]


def render_master_admin_dashboard():
    today = datetime.date.today()
    today_iso = today.isoformat()
    month_start = today.replace(day=1)
    month_end = (
        month_start.replace(month=12, day=31) if today.month == 12
        else month_start.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
    )
    month_start_dt = datetime.datetime.combine(month_start, datetime.time.min)

    total_students = User.query.filter_by(role="student").count()
    total_teachers = User.query.filter_by(role="teacher").count()
    total_accounts = User.query.count()
    today_attendance = Attendance.query.filter_by(day=today_iso).count()
    pending_cards = PendingCard.query.filter_by(state="Pending").count()
    present_today = Attendance.query.filter_by(day=today_iso, status="Present").count()
    absent_today = Attendance.query.filter_by(day=today_iso, status="Absent").count()
    late_today = Attendance.query.filter_by(day=today_iso, status="Late").count()
    present_like = present_today + late_today
    active_pct = round(present_like / total_students * 100) if total_students else 0
    inactive_pct = round(absent_today / total_students * 100, 1) if total_students else 0.0
    absence_rate = inactive_pct
    staff_count = User.query.filter(User.role.notin_(("student", "parent"))).count()
    teacher_pct = round(total_teachers / staff_count * 100) if staff_count else 0
    discipline_count = DisciplineCase.query.count()

    total_admissions = AdmissionApplicant.query.count()
    pending_admissions = AdmissionApplicant.query.filter(
        AdmissionApplicant.status.in_({"Submitted", "Under Review"})
    ).count()
    month_admissions = AdmissionApplicant.query.filter(
        AdmissionApplicant.applied_at >= month_start_dt
    ).count()
    admissions_ring = round(pending_admissions / total_admissions * 100) if total_admissions else 0

    schedule_month = DayScheduleEntry.query.filter(
        DayScheduleEntry.schedule_date >= month_start,
        DayScheduleEntry.schedule_date <= month_end,
        DayScheduleEntry.is_published.is_(True),
    ).all()
    meetings_month = Meeting.query.filter(
        Meeting.scheduled_date >= month_start.isoformat(),
        Meeting.scheduled_date <= month_end.isoformat(),
        Meeting.status.in_({"Scheduled", "Rescheduled", "In Progress"}),
    ).all()
    event_days = {entry.schedule_date.day for entry in schedule_month}
    for meeting in meetings_month:
        try:
            event_days.add(datetime.date.fromisoformat(meeting.scheduled_date).day)
        except ValueError:
            pass
    upcoming_events = DayScheduleEntry.query.filter(
        DayScheduleEntry.schedule_date >= today,
        DayScheduleEntry.is_published.is_(True),
    ).count() + Meeting.query.filter(
        Meeting.scheduled_date >= today_iso,
        Meeting.status.in_({"Scheduled", "Rescheduled", "In Progress"}),
    ).count()
    events_ring = min(100, round(len(event_days) / max(1, month_end.day) * 100))

    finance_labels, finance_income, attendance_labels, attendance_series = [], [], [], []
    week_income_total = 0.0
    for days_ago in range(6, -1, -1):
        day = today - datetime.timedelta(days=days_ago)
        day_sum = db.session.query(db.func.coalesce(db.func.sum(FeeTransaction.amount), 0)).filter(
            FeeTransaction.created_at.like(f"{day.isoformat()}%")
        ).scalar()
        amount = float(day_sum or 0)
        finance_labels.append(day.strftime("%a").upper())
        finance_income.append(amount)
        week_income_total += amount
        attendance_labels.append(day.strftime("%d %b"))
        attendance_series.append(Attendance.query.filter_by(day=day.isoformat()).count())

    avg_fee = float(db.session.query(db.func.avg(FeeTransaction.amount)).scalar() or 0)
    age_labels, age_values, avg_age = _admin_age_buckets(today)

    trade_rows = (
        db.session.query(User.trade, db.func.count(User.id))
        .filter(User.role == "student")
        .group_by(User.trade)
        .order_by(db.func.count(User.id).desc())
        .all()
    )
    trade_labels, trade_values = _admin_pair_lists(trade_rows)
    trade_totals = {(label or "Not specified"): int(count) for label, count in trade_rows}

    level_rows = (
        db.session.query(User.level, db.func.count(User.id))
        .filter(User.role == "student")
        .group_by(User.level)
        .order_by(db.func.count(User.id).desc())
        .all()
    )
    level_labels, level_values = _admin_pair_lists(level_rows)

    gender_rows = (
        db.session.query(User.gender, db.func.count(User.id))
        .filter(User.role == "student")
        .group_by(User.gender)
        .order_by(db.func.count(User.id).desc())
        .all()
    )
    gender_labels, gender_values = _admin_pair_lists(gender_rows, blank="Unspecified")

    class_rows = (
        db.session.query(User.class_name, db.func.count(User.id))
        .filter(User.role == "student")
        .group_by(User.class_name)
        .order_by(db.func.count(User.id).desc())
        .all()
    )
    class_labels, class_values = _admin_pair_lists(class_rows, blank="Unassigned", limit=8)

    absent_trade_rows = (
        db.session.query(User.trade, db.func.count(Attendance.id))
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.day == today_iso, Attendance.status == "Absent")
        .group_by(User.trade)
        .order_by(db.func.count(Attendance.id).desc())
        .all()
    )
    absent_trade_labels, absent_trade_values = _admin_pair_lists(absent_trade_rows)

    absent_class_rows = (
        db.session.query(User.class_name, db.func.count(Attendance.id))
        .join(User, Attendance.student_id == User.id)
        .filter(Attendance.day == today_iso, Attendance.status == "Absent")
        .group_by(User.class_name)
        .order_by(db.func.count(Attendance.id).desc())
        .limit(8)
        .all()
    )
    absent_class_labels, absent_class_values = _admin_pair_lists(absent_class_rows, blank="Unassigned")

    absence_rate_items = []
    for label, total in sorted(trade_totals.items(), key=lambda item: item[1], reverse=True)[:8]:
        absent_count = next((int(count) for trade, count in absent_trade_rows if (trade or "Not specified") == label), 0)
        rate = round(absent_count / total * 100, 1) if total else 0.0
        absence_rate_items.append((label, rate))
    absence_rate_bars = _admin_rate_bars(absence_rate_items, accent="#ff4c61")

    status_items = [
        ("Present", round(present_today / today_attendance * 100, 1) if today_attendance else 0.0),
        ("Late", round(late_today / today_attendance * 100, 1) if today_attendance else 0.0),
        ("Absent", round(absent_today / today_attendance * 100, 1) if today_attendance else 0.0),
    ]
    status_bars = _admin_rate_bars(status_items, accent="#2563eb")

    top_trade = trade_labels[0] if trade_labels else "Not specified"
    top_trade_share = round(trade_values[0] / total_students * 100, 1) if trade_values and total_students else 0.0
    highest_absence_trade = absence_rate_items[0][0] if absence_rate_items else "n/a"
    highest_absence_rate = absence_rate_items[0][1] if absence_rate_items else 0.0
    top_age_label = age_labels[age_values.index(max(age_values))] if age_values and max(age_values) else "Unknown"
    top_age_share = round(max(age_values) / total_students * 100, 1) if age_values and total_students and max(age_values) else 0.0

    insights = [
        f"Total headcount is {total_students} registered students across {total_accounts} accounts.",
        f"Absence rate today is {absence_rate}% ({absent_today} students marked absent).",
        f"{highest_absence_trade} has the highest absence rate at {highest_absence_rate}%.",
        f"Most students ({top_age_share}%) fall in the {top_age_label} age group." if avg_age else f"Largest trade group is {top_trade} at {top_trade_share}%.",
        f"Average recorded fee payment is {avg_fee:,.0f} RWF; weekly income is {week_income_total:,.0f} RWF.",
    ]
    insights_html = "".join(
        f"<div class='admin-insight'><i class='bi bi-lightbulb'></i><span>{escape(text)}</span></div>"
        for text in insights
    )

    recent_students = User.query.filter_by(role="student").order_by(User.id.desc()).limit(6).all()
    recent_students_html = "".join(
        f"<li><span class='admin-avatar' aria-hidden='true'>{escape((student.full_name or '?')[:1].upper())}</span>"
        f"<div><strong>{escape(student.full_name)}</strong>"
        f"<small>{escape(student.class_name or 'Unassigned class')}</small></div></li>"
        for student in recent_students
    ) or "<li class='admin-empty'>No students registered yet.</li>"

    calendar_html = _admin_month_calendar(today, event_days)
    events_ring_svg = _admin_ring_svg(events_ring, "#ff4c61")
    admissions_ring_svg = _admin_ring_svg(admissions_ring, "#8b5cf6")
    month_label = today.strftime("%B %Y")
    range_label = f"{month_start.strftime('%b %Y')} – {today.strftime('%b %Y')}"

    body = """
<style>
.admin-dash{--ad-purple:#7c3aed;--ad-blue:#2563eb;--ad-pink:#ff4c61;--ad-green:#22c55e;--ad-orange:#f97316;--ad-soft:#f4f6fb;display:grid;gap:16px}
.admin-dash-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;flex-wrap:wrap}
.admin-dash-heading h1{margin:6px 0 4px;font-size:clamp(1.4rem,2.2vw,1.85rem)}
.admin-dash-heading p{margin:0;color:var(--muted)}
.admin-filters{display:flex;flex-wrap:wrap;gap:8px}
.admin-filter{border:1px solid var(--border);background:var(--card);border-radius:10px;padding:8px 12px;font-size:.74rem;font-weight:700;color:var(--muted)}
.admin-filter strong{color:var(--text);font-weight:800}
.admin-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.admin-metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
.admin-kpi,.admin-metric{text-decoration:none;color:inherit;transition:transform .18s ease,box-shadow .18s ease}
.admin-kpi:hover,.admin-metric:hover{transform:translateY(-2px);color:inherit}
.admin-kpi{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:112px;padding:16px;border-radius:20px;box-shadow:0 10px 28px rgba(15,23,42,.06);border:1px solid transparent}
.admin-kpi-copy{min-width:0}.admin-kpi-label{font-size:.74rem;font-weight:700;opacity:.86;margin-bottom:6px}
.admin-kpi-value{font-size:clamp(1.4rem,2.2vw,1.9rem);font-weight:850;line-height:1;letter-spacing:-.03em}
.admin-kpi-note{margin-top:7px;font-size:.66rem;font-weight:650;opacity:.82}
.admin-kpi-purple{background:linear-gradient(145deg,#8b5cf6,#6d28d9);color:#fff}
.admin-kpi-blue{background:linear-gradient(145deg,#2563eb,#1e3a8a);color:#fff}
.admin-kpi-white{background:var(--card);border-color:var(--border);color:var(--text)}
.admin-kpi-white .admin-kpi-label,.admin-kpi-white .admin-kpi-note{color:var(--muted);opacity:1}
.admin-kpi-icon{width:40px;height:40px;border-radius:12px;display:grid;place-items:center;background:rgba(255,255,255,.18);font-size:1.1rem}
.admin-kpi-white .admin-kpi-icon{background:#eef2ff;color:var(--ad-blue)}
.admin-metric{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:14px;box-shadow:0 8px 22px rgba(15,23,42,.04);display:grid;gap:8px;min-height:104px}
.admin-metric-top{display:flex;align-items:center;justify-content:space-between;gap:8px}
.admin-metric-icon{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:#eef2ff;color:var(--ad-blue);font-size:.95rem}
.admin-metric-label{font-size:.72rem;font-weight:750;color:var(--muted)}
.admin-metric-value{font-size:1.35rem;font-weight:850;letter-spacing:-.03em;line-height:1}
.admin-metric-delta{font-size:.68rem;font-weight:750}
.admin-metric-delta.up{color:var(--ad-green)}.admin-metric-delta.down{color:var(--ad-pink)}.admin-metric-delta.flat{color:var(--muted)}
.admin-ring{width:58px;height:58px;flex:0 0 auto}
.admin-ring-bg{fill:none;stroke:rgba(15,23,42,.08);stroke-width:3.2}
[data-theme="dark"] .admin-ring-bg{stroke:rgba(255,255,255,.12)}
.admin-ring-fg{fill:none;stroke-width:3.2;stroke-linecap:round}
.admin-ring-text{font-size:7.2px;font-weight:800;fill:var(--text)}
.admin-mid{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(250px,.8fr);gap:12px}
.admin-grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.admin-grid-4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.admin-card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:16px;box-shadow:0 10px 28px rgba(15,23,42,.04)}
.admin-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px}
.admin-card-head h2{margin:0;font-size:.98rem}
.admin-card-head p{margin:3px 0 0;color:var(--muted);font-size:.74rem}
.admin-toggle{display:inline-flex;gap:6px;background:var(--ad-soft);border-radius:999px;padding:4px}
[data-theme="dark"] .admin-toggle{background:rgba(255,255,255,.06)}
.admin-toggle span{border-radius:999px;padding:4px 9px;font-size:.66rem;font-weight:750;color:var(--muted)}
.admin-toggle .is-active{background:#fff;color:var(--text);box-shadow:0 2px 8px rgba(15,23,42,.08)}
[data-theme="dark"] .admin-toggle .is-active{background:rgba(255,255,255,.12);color:#fff}
.admin-finance-stats{display:flex;flex-wrap:wrap;gap:16px;margin-bottom:6px}
.admin-finance-stats strong{display:block;font-size:1rem;letter-spacing:-.02em}
.admin-finance-stats small{color:var(--muted);font-size:.7rem;font-weight:700}
.admin-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.admin-dot-green{background:var(--ad-green)}.admin-dot-orange{background:var(--ad-orange)}
.admin-chart{height:210px;position:relative}.admin-chart-sm{height:190px}
.admin-cal-weekdays,.admin-cal-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;text-align:center}
.admin-cal-weekdays{margin-bottom:8px;color:var(--muted);font-size:.66rem;font-weight:750}
.admin-cal-day{display:grid;place-items:center;min-height:30px;border-radius:10px;font-size:.74rem;font-weight:700}
.admin-cal-day.is-empty{visibility:hidden}
.admin-cal-day.has-event{background:rgba(255,76,97,.12);color:var(--ad-pink)}
.admin-cal-day.is-today{background:var(--ad-pink);color:#fff;box-shadow:0 6px 14px rgba(255,76,97,.28)}
.admin-rate-row{display:grid;grid-template-columns:minmax(72px,.9fr) minmax(0,1.4fr) 52px;gap:8px;align-items:center;margin-bottom:8px}
.admin-rate-label{font-size:.72rem;font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.admin-rate-track{height:8px;border-radius:999px;background:rgba(148,163,184,.18);overflow:hidden}
.admin-rate-track span{display:block;height:100%;border-radius:999px}
.admin-rate-row strong{font-size:.72rem;text-align:right}
.admin-recent-list{list-style:none;margin:0;padding:0;display:grid;gap:9px}
.admin-recent-list li{display:flex;align-items:center;gap:10px}
.admin-recent-list strong{display:block;font-size:.8rem}
.admin-recent-list small{color:var(--muted);font-size:.68rem}
.admin-avatar{width:32px;height:32px;border-radius:50%;display:grid;place-items:center;background:linear-gradient(135deg,#8b5cf6,#2563eb);color:#fff;font-weight:800;font-size:.74rem;flex:0 0 auto}
.admin-empty{color:var(--muted);font-size:.8rem}
.admin-insights{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;background:var(--ad-soft);border:1px solid var(--border);border-radius:16px;padding:12px}
[data-theme="dark"] .admin-insights{background:rgba(255,255,255,.04)}
.admin-insight{display:flex;gap:8px;align-items:flex-start;font-size:.72rem;line-height:1.35;color:var(--text);font-weight:650}
.admin-insight i{color:#eab308;margin-top:1px}
.admin-quick{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.admin-quick a{display:flex;align-items:center;gap:10px;padding:11px;border:1px solid var(--border);border-radius:14px;color:var(--text);background:var(--card);font-weight:700;font-size:.8rem}
.admin-quick a i{width:28px;height:28px;border-radius:9px;display:grid;place-items:center;background:#eef2ff;color:var(--ad-blue)}
@media(max-width:1200px){.admin-metrics{grid-template-columns:repeat(3,minmax(0,1fr))}.admin-grid-3,.admin-grid-4,.admin-insights{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:900px){.admin-kpis,.admin-mid{grid-template-columns:1fr 1fr}.admin-grid-3,.admin-grid-4{grid-template-columns:1fr}.admin-quick{grid-template-columns:1fr 1fr}}
@media(max-width:600px){.admin-kpis,.admin-metrics,.admin-mid,.admin-insights,.admin-quick{grid-template-columns:1fr}.admin-chart,.admin-chart-sm{height:180px}.admin-rate-row{grid-template-columns:minmax(64px,.8fr) minmax(0,1.2fr) 48px}}
</style>
<div class="admin-dash">
  <div class="admin-dash-heading">
    <div>
      <span class="pill">SCHOOL ANALYTICS</span>
      <h1>School Analytics Dashboard</h1>
      <p>Student overview, attendance insights, admissions, and finance from live school records.</p>
    </div>
    <div class="admin-filters" aria-label="Dashboard scope">
      <div class="admin-filter">Date Range: <strong>{{ range_label }}</strong></div>
      <div class="admin-filter">Trade: <strong>All</strong></div>
      <div class="admin-filter">Class: <strong>All</strong></div>
      <div class="admin-filter">Level: <strong>All</strong></div>
      <a class="btn btn-accent" href="/admin"><i class="bi bi-gear me-1"></i> Admin Center</a>
    </div>
  </div>

  <section class="admin-kpis" aria-label="Highlight metrics">
    <a class="admin-kpi admin-kpi-purple" href="/students">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Total Students</div>
        <div class="admin-kpi-value">{{ total_students }}</div>
        <div class="admin-kpi-note">{{ total_accounts }} system accounts</div>
      </div>
      <span class="admin-kpi-icon"><i class="bi bi-people-fill"></i></span>
    </a>
    <a class="admin-kpi admin-kpi-blue" href="/admin">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Total Teachers</div>
        <div class="admin-kpi-value">{{ total_teachers }}</div>
        <div class="admin-kpi-note">Teacher accounts</div>
      </div>
      <span class="admin-kpi-icon"><i class="bi bi-mortarboard-fill"></i></span>
    </a>
    <a class="admin-kpi admin-kpi-white" href="/day-schedule">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Events</div>
        <div class="admin-kpi-value">{{ upcoming_events }}</div>
        <div class="admin-kpi-note">Upcoming schedules & meetings</div>
      </div>
      {{ events_ring_svg|safe }}
    </a>
    <a class="admin-kpi admin-kpi-white" href="/admissions">
      <div class="admin-kpi-copy">
        <div class="admin-kpi-label">Admissions</div>
        <div class="admin-kpi-value">{{ total_admissions }}</div>
        <div class="admin-kpi-note">{{ pending_admissions }} pending review</div>
      </div>
      {{ admissions_ring_svg|safe }}
    </a>
  </section>

  <section class="admin-metrics" aria-label="Workforce-style school KPIs">
    <a class="admin-metric" href="/students">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-people"></i></span><span class="admin-metric-delta flat">Headcount</span></div>
      <div class="admin-metric-label">Total Students</div>
      <div class="admin-metric-value">{{ total_students }}</div>
    </a>
    <a class="admin-metric" href="/admissions">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-person-plus"></i></span><span class="admin-metric-delta up">This month</span></div>
      <div class="admin-metric-label">New Admissions</div>
      <div class="admin-metric-value">{{ month_admissions }}</div>
    </a>
    <a class="admin-metric" href="/attendance">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-person-x"></i></span><span class="admin-metric-delta down">Today</span></div>
      <div class="admin-metric-label">Absent Count</div>
      <div class="admin-metric-value">{{ absent_today }}</div>
    </a>
    <a class="admin-metric" href="/attendance">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-graph-down-arrow"></i></span><span class="admin-metric-delta {% if absence_rate > 10 %}down{% else %}flat{% endif %}">Rate</span></div>
      <div class="admin-metric-label">Absence Rate</div>
      <div class="admin-metric-value">{{ absence_rate }}%</div>
    </a>
    <a class="admin-metric" href="/fees">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-cash-coin"></i></span><span class="admin-metric-delta up">Avg fee</span></div>
      <div class="admin-metric-label">Avg Fee Payment</div>
      <div class="admin-metric-value">{{ avg_fee_display }}</div>
    </a>
    <a class="admin-metric" href="/students">
      <div class="admin-metric-top"><span class="admin-metric-icon"><i class="bi bi-calendar3"></i></span><span class="admin-metric-delta flat">Years</span></div>
      <div class="admin-metric-label">Avg Student Age</div>
      <div class="admin-metric-value">{{ avg_age_display }}</div>
    </a>
  </section>

  <div class="admin-mid">
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>School Finance</h2>
          <p>Fee payments recorded during the last 7 days.</p>
        </div>
        <div class="admin-toggle" aria-hidden="true"><span>Monthly</span><span class="is-active">Weekly</span></div>
      </div>
      <div class="admin-finance-stats">
        <div><small><span class="admin-dot admin-dot-green"></span>Income</small><strong>{{ week_income_display }} RWF</strong></div>
        <div><small><span class="admin-dot admin-dot-orange"></span>Expense</small><strong>0 RWF</strong></div>
      </div>
      <div class="admin-chart"><canvas id="adminFinanceChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head">
        <div>
          <h2>School Event Calendar</h2>
          <p>{{ month_label }} · Discipline cases: {{ discipline_count }}</p>
        </div>
        <a href="/meetings" class="btn btn-sm btn-outline-success">Meetings</a>
      </div>
      {{ calendar_html|safe }}
    </section>
  </div>

  <div class="admin-grid-3">
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Attendance Trend</h2><p>Records saved over the last 7 days.</p></div></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminAttendanceTrendChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Absences by Trade</h2><p>Today’s absent marks grouped by trade.</p></div><span class="pill">{{ absent_today }}</span></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminAbsentTradeChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Absences by Class</h2><p>Highest absence classes today.</p></div></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminAbsentClassChart"></canvas></div>
    </section>
  </div>

  <div class="admin-grid-3">
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Students by Trade</h2><p>Current registered student distribution.</p></div></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminTradeChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Absence Rate by Trade</h2><p>Share of each trade marked absent today.</p></div></div>
      {{ absence_rate_bars|safe }}
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Students by Age Group</h2><p>Based on date of birth where available.</p></div><span class="pill">{{ total_students }}</span></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminAgeChart"></canvas></div>
    </section>
  </div>

  <div class="admin-grid-4">
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Gender Diversity</h2><p>Students by recorded gender.</p></div></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminGenderChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Students by Level</h2><p>Level distribution across the school.</p></div></div>
      <div class="admin-chart admin-chart-sm"><canvas id="adminLevelChart"></canvas></div>
    </section>
    <section class="admin-card">
      <div class="admin-card-head"><div><h2>Attendance Status Mix</h2><p>Present, late, and absent share today.</p></div></div>
      {{ status_bars|safe }}
      <p class="admin-empty mb-0 mt-2">Attendance records today: {{ today_attendance }} · Pending RFID: {{ pending_cards }}</p>
    </section>
    <section class="admin-card">
      <div class="admin-card-head">
        <div><h2>Recent Students</h2><p>Latest student accounts.</p></div>
        <a href="/students" class="btn btn-sm btn-outline-success">View</a>
      </div>
      <ul class="admin-recent-list">{{ recent_students_html|safe }}</ul>
    </section>
  </div>

  <section class="admin-insights" aria-label="Key insights">{{ insights_html|safe }}</section>

  <section class="admin-card">
    <div class="admin-card-head"><div><h2>Quick Access</h2><p>Open the most-used school modules.</p></div></div>
    <div class="admin-quick">
      <a href="/students"><i class="bi bi-people"></i><span>Students</span></a>
      <a href="/grades"><i class="bi bi-journal-text"></i><span>Report Cards</span></a>
      <a href="/fees"><i class="bi bi-cash-stack"></i><span>Fees</span></a>
      <a href="/timetable"><i class="bi bi-calendar3"></i><span>Timetable</span></a>
    </div>
  </section>
</div>
<script>
(() => {
  const muted = getComputedStyle(document.documentElement).getPropertyValue('--muted').trim() || '#667085';
  const palette = {{ chart_colors|safe }};
  const empty = (labels) => (!labels || !labels.length ? ['No data'] : labels);
  const emptyVals = (values) => (!values || !values.length ? [0] : values);
  const lineOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, ticks: { color: muted, precision: 0 }, grid: { color: 'rgba(120,135,140,.12)' } },
      x: { ticks: { color: muted }, grid: { display: false } }
    }
  };
  const donut = (el, labels, values) => {
    if (!el || !window.Chart) return;
    new Chart(el, {
      type: 'doughnut',
      data: { labels: empty(labels), datasets: [{ data: emptyVals(values), backgroundColor: palette, borderWidth: 0 }] },
      options: { responsive: true, maintainAspectRatio: false, cutout: '62%', plugins: { legend: { position: 'bottom', labels: { color: muted, boxWidth: 10, font: { size: 10 } } } } }
    });
  };
  const bars = (el, labels, values, horizontal=false) => {
    if (!el || !window.Chart) return;
    new Chart(el, {
      type: 'bar',
      data: { labels: empty(labels), datasets: [{ data: emptyVals(values), backgroundColor: palette, borderRadius: 8, borderWidth: 0 }] },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { color: muted, precision: 0 }, grid: horizontal ? { color: 'rgba(120,135,140,.12)' } : { display: false } },
          y: { beginAtZero: true, ticks: { color: muted, precision: 0 }, grid: horizontal ? { display: false } : { color: 'rgba(120,135,140,.12)' } }
        }
      }
    });
  };
  if (!window.Chart) return;
  new Chart(document.getElementById('adminFinanceChart'), {
    type: 'line',
    data: {
      labels: {{ finance_labels|safe }},
      datasets: [
        { label: 'Income', data: {{ finance_income|safe }}, borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,.12)', fill: true, tension: .38, pointRadius: 3 },
        { label: 'Expense', data: {{ finance_labels|safe }}.map(() => 0), borderColor: '#f97316', tension: .38, pointRadius: 2 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { color: muted, callback: (v) => Number(v).toLocaleString() }, grid: { color: 'rgba(120,135,140,.12)' } },
        x: { ticks: { color: muted }, grid: { display: false } }
      }
    }
  });
  new Chart(document.getElementById('adminAttendanceTrendChart'), {
    type: 'line',
    data: { labels: {{ attendance_labels|safe }}, datasets: [{ data: {{ attendance_series|safe }}, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,.12)', fill: true, tension: .35, pointRadius: 3 }] },
    options: lineOpts
  });
  donut(document.getElementById('adminAbsentTradeChart'), {{ absent_trade_labels|safe }}, {{ absent_trade_values|safe }});
  bars(document.getElementById('adminAbsentClassChart'), {{ absent_class_labels|safe }}, {{ absent_class_values|safe }}, true);
  bars(document.getElementById('adminTradeChart'), {{ trade_labels|safe }}, {{ trade_values|safe }}, false);
  donut(document.getElementById('adminAgeChart'), {{ age_labels|safe }}, {{ age_values|safe }});
  donut(document.getElementById('adminGenderChart'), {{ gender_labels|safe }}, {{ gender_values|safe }});
  bars(document.getElementById('adminLevelChart'), {{ level_labels|safe }}, {{ level_values|safe }}, true);
})();
</script>
"""
    return page(
        "Analytics Dashboard",
        body,
        "master_admin",
        total_accounts=total_accounts,
        total_students=total_students,
        total_teachers=total_teachers,
        today_attendance=today_attendance,
        pending_cards=pending_cards,
        today_iso=today_iso,
        upcoming_events=upcoming_events,
        total_admissions=total_admissions,
        pending_admissions=pending_admissions,
        month_admissions=month_admissions,
        absent_today=absent_today,
        absence_rate=absence_rate,
        avg_fee_display=f"{avg_fee:,.0f}",
        avg_age_display=f"{avg_age:g}" if avg_age else "—",
        week_income_display=f"{week_income_total:,.0f}",
        month_label=month_label,
        range_label=range_label,
        discipline_count=discipline_count,
        active_pct=active_pct,
        inactive_pct=inactive_pct,
        teacher_pct=teacher_pct,
        events_ring_svg=events_ring_svg,
        admissions_ring_svg=admissions_ring_svg,
        calendar_html=calendar_html,
        recent_students_html=recent_students_html,
        absence_rate_bars=absence_rate_bars,
        status_bars=status_bars,
        insights_html=insights_html,
        finance_labels=json.dumps(finance_labels),
        finance_income=json.dumps(finance_income),
        attendance_labels=json.dumps(attendance_labels),
        attendance_series=json.dumps(attendance_series),
        absent_trade_labels=json.dumps(absent_trade_labels),
        absent_trade_values=json.dumps(absent_trade_values),
        absent_class_labels=json.dumps(absent_class_labels),
        absent_class_values=json.dumps(absent_class_values),
        trade_labels=json.dumps(trade_labels),
        trade_values=json.dumps(trade_values),
        age_labels=json.dumps(age_labels),
        age_values=json.dumps(age_values),
        gender_labels=json.dumps(gender_labels),
        gender_values=json.dumps(gender_values),
        level_labels=json.dumps(level_labels),
        level_values=json.dumps(level_values),
        chart_colors=json.dumps(CHART_COLORS),
    )
