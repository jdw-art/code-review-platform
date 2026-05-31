from __future__ import annotations

import time
from datetime import datetime

from app.core.config import Settings
from app.db.session import SessionLocal
from app.services.daily_report_service import DailyReportService


def _matches_cron_part(value: int, expression: str) -> bool:
    if expression == "*":
        return True
    for part in expression.split(","):
        part = part.strip()
        if not part:
            continue
        if part == "*":
            return True
        if "/" in part:
            base, step_text = part.split("/", 1)
            step = int(step_text)
            if base == "*":
                if value % step == 0:
                    return True
                continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start <= value <= end:
                return True
            continue
        if int(part) == value:
            return True
    return False


def cron_matches_now(expression: str, now: datetime | None = None) -> bool:
    current = now or datetime.now()
    minute, hour, day, month, day_of_week = expression.split()
    cron_weekday = (current.weekday() + 1) % 7
    return (
        _matches_cron_part(current.minute, minute)
        and _matches_cron_part(current.hour, hour)
        and _matches_cron_part(current.day, day)
        and _matches_cron_part(current.month, month)
        and _matches_cron_part(cron_weekday, day_of_week)
    )


def run_daily_report_once(session) -> str | None:
    return DailyReportService(session=session).send_today_report()


def main() -> None:
    settings = Settings()
    last_run_key: tuple[int, int, int, int, int] | None = None
    while True:
        now = datetime.now()
        current_key = (now.year, now.month, now.day, now.hour, now.minute)
        if current_key != last_run_key and cron_matches_now(settings.report_crontab_expression, now):
            session = SessionLocal()
            try:
                run_daily_report_once(session)
            finally:
                session.close()
            last_run_key = current_key
        time.sleep(30)
