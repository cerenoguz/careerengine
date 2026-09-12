from datetime import date
from html.parser import HTMLParser

from src.models import Job, SourceHealth
from src.reporting.email_report import (
    build_daily_email_html,
    build_daily_email_report,
    format_report_date,
    format_subject_date,
    format_top_role_line,
)


def make_job(
    index: int = 1,
    *,
    is_new_discovery: bool = False,
    location: str | None = "Boston, MA",
) -> Job:
    return Job(
        id=str(index),
        company=f"Company {index}",
        title=f"Software Engineer {index}",
        location=location,
        description="Python backend software engineering role.",
        url=f"https://example.com/jobs/{index}",
        date_posted=None,
        source="test",
        eligibility_status="likely_compatible",
        description_similarity=0.05,
        score=90.0,
        why_matched=["Strong CS/Math degree relevance (+15)", "Role match"],
        first_found_date=None,
        is_new_discovery=is_new_discovery,
    )


def build_report(
    jobs: list[Job],
    *,
    health_records: list[SourceHealth] | None = None,
    total_jobs_collected: int = 10,
    qualified_jobs: int | None = None,
    dashboard_url: str = "https://careerengine.example.com",
) -> str:
    return build_daily_email_report(
        health_records=health_records or [],
        total_jobs_collected=total_jobs_collected,
        qualified_jobs=qualified_jobs if qualified_jobs is not None else len(jobs),
        newly_discovered_jobs=jobs,
        additional_qualified_jobs=max(len(jobs) - 5, 0),
        dashboard_url=dashboard_url,
    )


def test_format_report_date():
    assert format_report_date(date(2026, 6, 16)) == "Tuesday - June 16, 2026"


def test_format_subject_date():
    assert format_subject_date(date(2026, 6, 16)) == "6/16/2026"


def test_format_top_role_line_marks_new_jobs():
    job = make_job(is_new_discovery=True)

    assert (
        format_top_role_line(1, job)
        == "1. Company 1 — Software Engineer 1 — Boston, MA 🚨 New"
    )


def test_format_top_role_line_handles_missing_location():
    job = make_job(location=None)

    assert (
        format_top_role_line(1, job)
        == "1. Company 1 — Software Engineer 1 — Location not listed"
    )


def test_daily_email_report_uses_lightweight_dashboard_reminder():
    report = build_report(
        [make_job(1, is_new_discovery=True), make_job(2, is_new_discovery=True)],
        qualified_jobs=40,
        dashboard_url="https://careerengine.example.com",
    )

    assert report.startswith("Hi there,")
    assert "Your CareerEngine job queue has been updated." in report
    assert "Open dashboard:\nhttps://careerengine.example.com" in report
    assert "Newly found jobs today: 2" in report
    assert "Your top matches among today's new jobs:" in report
    assert "1. Company 1 — Software Engineer 1 — Boston, MA" in report
    assert "2. Company 2 — Software Engineer 2 — Boston, MA" in report
    assert "Active qualified opportunities ranked: 40" in report
    assert "Best of luck,\nCareerEngine" in report

    assert "Score Guide:" not in report
    assert "Description Similarity Guide:" not in report
    assert "CareerEngine recommendation:" not in report
    assert "Why CareerEngine selected this role:" not in report


def test_daily_email_report_caps_list_at_top_five_by_fit():
    jobs = [make_job(index, is_new_discovery=True) for index in range(1, 7)]

    report = build_report(jobs)

    assert "Newly found jobs today: 6" in report
    assert "1. Company 1 — Software Engineer 1 — Boston, MA" in report
    assert "5. Company 5 — Software Engineer 5 — Boston, MA" in report
    assert "6. Company 6 — Software Engineer 6 — Boston, MA" not in report
    assert "...and 1 more. See the dashboard for the full list." in report


def test_daily_email_report_handles_no_new_jobs():
    report = build_report([], total_jobs_collected=0, qualified_jobs=0)

    assert "No new job postings found today." in report
    assert "Best of luck,\nCareerEngine" in report


def test_daily_email_report_summarizes_successful_and_disabled_sources():
    report = build_report(
        [make_job(1)],
        total_jobs_collected=10,
        qualified_jobs=1,
        health_records=[
            SourceHealth(
                company="WorkingCo",
                source="ashby",
                status="success",
                http_code=200,
                jobs_found=10,
                reason=None,
            ),
            SourceHealth(
                company="DisabledCo",
                source="custom",
                status="disabled",
                http_code=None,
                jobs_found=0,
                reason="Disabled for test.",
            ),
        ],
    )

    assert "Successful company sources: 1 / 2" in report
    assert "Total jobs collected: 10" in report
    assert "Active qualified opportunities ranked: 1" in report
    assert "Disabled Sources (1):" in report
    assert "- DisabledCo: Disabled for test." in report


def build_html_report(
    jobs: list[Job],
    *,
    health_records: list[SourceHealth] | None = None,
    total_jobs_collected: int = 10,
    qualified_jobs: int | None = None,
    dashboard_url: str = "https://careerengine.example.com",
) -> str:
    return build_daily_email_html(
        health_records=health_records or [],
        total_jobs_collected=total_jobs_collected,
        qualified_jobs=qualified_jobs if qualified_jobs is not None else len(jobs),
        newly_discovered_jobs=jobs,
        additional_qualified_jobs=max(len(jobs) - 5, 0),
        dashboard_url=dashboard_url,
    )


def test_daily_email_html_is_well_formed_and_includes_content():
    html_report = build_html_report(
        [make_job(1, is_new_discovery=True), make_job(2, is_new_discovery=True)],
        qualified_jobs=40,
        dashboard_url="https://careerengine.example.com",
    )

    assert html_report.startswith("<!doctype html>")
    assert html_report.rstrip().endswith("</html>")
    assert "Company 1" in html_report
    assert "Software Engineer 1" in html_report
    assert "Boston, MA" in html_report
    assert 'href="https://careerengine.example.com"' in html_report
    assert "View dashboard" in html_report
    assert "40" in html_report

    parser = _BalancedTagChecker()
    parser.feed(html_report)
    assert parser.unclosed == []


def test_daily_email_html_escapes_job_fields():
    job = make_job(1, is_new_discovery=True)
    job.company = "<script>alert(1)</script>"
    job.title = "R&D Engineer"

    html_report = build_html_report([job])

    assert "<script>alert(1)</script>" not in html_report
    assert "&lt;script&gt;" in html_report
    assert "R&amp;D Engineer" in html_report


def test_daily_email_html_caps_list_at_top_five_by_fit():
    jobs = [make_job(index, is_new_discovery=True) for index in range(1, 7)]

    html_report = build_html_report(jobs)

    assert "Company 1" in html_report
    assert "Company 5" in html_report
    assert "Company 6" not in html_report
    assert "+ 1 more in your dashboard" in html_report
    assert 'padding:1px 8px;">6</td>' in html_report


def test_daily_email_html_handles_no_new_jobs():
    html_report = build_html_report([], total_jobs_collected=0, qualified_jobs=0)

    assert "No new job postings found today." in html_report


def test_daily_email_html_lists_disabled_sources():
    html_report = build_html_report(
        [make_job(1)],
        health_records=[
            SourceHealth(
                company="WorkingCo",
                source="ashby",
                status="success",
                http_code=200,
                jobs_found=10,
                reason=None,
            ),
            SourceHealth(
                company="DisabledCo",
                source="custom",
                status="disabled",
                http_code=None,
                jobs_found=0,
                reason="Disabled for test.",
            ),
        ],
    )

    assert "DisabledCo" in html_report
    assert "Disabled for test." in html_report
    assert "Disabled sources (1)" in html_report


def test_daily_email_html_falls_back_when_dashboard_not_configured():
    html_report = build_html_report([make_job(1)], dashboard_url="")

    assert "View dashboard" not in html_report
    assert "Dashboard URL not configured" in html_report


class _BalancedTagChecker(HTMLParser):
    _VOID_TAGS = {"meta", "br", "img", "hr", "input", "link"}

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.unclosed: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag not in self._VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.unclosed.append(tag)
