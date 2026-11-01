"""Background scheduler for the daily consolidated welfare report.

Runs as a daemon thread inside the Flask application so report delivery does
not depend on a user keeping a dashboard open. Delivers the consolidated
Patron + Matron welfare report to school administrators before the configured
deadline (default 8:00 AM local time) every day.
"""

from __future__ import annotations

import datetime
import threading
import time

from app.extensions import db
from app.models import User
from app.services.welfare_report_service import (
    consolidated_report_for_day,
    deadline_settings,
    log_delivery,
    send_consolidated_report,
)
from app.services.welfare_service import (
    LEADER_ROLES,
    missing_reports_for,
    notify_missing_daily_reports,
    notify_overdue_follow_ups,
)
from app.utils.helpers import get_setting, now_string


class WelfareReportScheduler:
    def __init__(self):
        self._thread = None
        self._stop = threading.Event()
        self._started = False
        self._last_delivery_date = None
        self._last_check_date = None

    def start(self, app):
        if self._started:
            return
        self._started = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, args=(app,), daemon=True, name="welfare-report-scheduler")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _loop(self, app):
        while not self._stop.is_set():
            try:
                with app.app_context():
                    self._tick()
            except Exception:
                # Keep the scheduler alive even if one tick fails.
                pass
            self._stop.wait(60)

    def _tick(self):
        now = datetime.datetime.now()
        today = now.date().isoformat()
        if self._last_check_date != today:
            self._last_check_date = today
            # New day: reset delivery tracking.
            if self._last_delivery_date != today:
                self._last_delivery_date = None

        deadline_hour, deadline_minute = deadline_settings()
        # Deliver 5 minutes before the configured deadline, so it lands before the deadline.
        delivery_hour = deadline_hour - 1 if deadline_minute < 5 else deadline_hour
        delivery_minute = deadline_minute + 55 if deadline_minute < 5 else deadline_minute - 5
        delivery_minute = max(0, min(59, delivery_minute))

        due_now = (
            now.hour == delivery_hour and now.minute == delivery_minute
        ) and self._last_delivery_date != today

        if due_now:
            self._deliver_today(app)

        # Reminder / overdue checks once per day at the deadline hour.
        if now.hour == deadline_hour and now.minute == deadline_minute:
            self._check_reminders_and_overdue(app)

    def _deliver_today(self, app):
        from app.models.welfare import DailyWelfareReport

        today = datetime.date.today().isoformat()
        already = DailyWelfareReport.query.filter_by(report_date=today).first()
        actor = self._system_actor()
        if not actor:
            return

        success, message = send_consolidated_report(actor, today)
        self._last_delivery_date = today
        try:
            app.logger.info("Welfare scheduler: %s", message)
        except Exception:
            pass

    def _check_reminders_and_overdue(self, app):
        today = datetime.date.today().isoformat()
        actor = self._system_actor()
        if not actor:
            return

        # Remind Patron and Matron if they have not yet submitted today.
        missing = missing_reports_for(today)
        if missing:
            labels = ", ".join(role.replace("_", " ").title() for role in missing)
            from app.utils.notifications import notify_school_admins
            notify_school_admins(
                "Welfare",
                f"Daily welfare report reminder ({today})",
                f"The following daily welfare reports have not yet been submitted for {today}: {labels}. "
                "Please submit before the configured deadline.",
                "/welfare/report",
            )

        # Notify admins of overdue follow-ups.
        try:
            notify_overdue_follow_ups(today)
        except Exception:
            pass

    def _system_actor(self):
        """Return a Master Admin / Head Teacher actor for scheduler actions."""
        from app.models import User

        return (
            User.query.filter(User.role.in_(LEADER_ROLES), User.is_active_account.is_(True))
            .order_by(User.id.asc())
            .first()
        )


scheduler = WelfareReportScheduler()


def start_scheduler(app):
    scheduler.start(app)
