from datetime import date
from pathlib import Path


REPORTS_DIR = Path("reports")


def save_daily_report(email_body: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    report_path = REPORTS_DIR / "daily_report.txt"

    report_path.write_text(email_body + "\n", encoding="utf-8")

    return report_path


def save_dated_daily_report(email_body: str) -> Path:
    REPORTS_DIR.mkdir(exist_ok=True)

    today = date.today().isoformat()
    report_path = REPORTS_DIR / f"daily_report_{today}.txt"

    report_path.write_text(email_body + "\n", encoding="utf-8")

    return report_path
