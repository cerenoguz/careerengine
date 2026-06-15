from pathlib import Path

import src.reporting.report_writer as report_writer


def test_save_daily_report_writes_report_file(tmp_path: Path) -> None:
    report_writer.REPORTS_DIR = tmp_path

    email_body = "CareerEngine Daily Job Report"

    report_path = report_writer.save_daily_report(email_body)

    assert report_path.exists()
    assert report_path.name == "daily_report.txt"
    assert report_path.read_text(encoding="utf-8") == email_body + "\n"