from datetime import date

from src.models import Job, SourceHealth
from src.reporting.email_report import (
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
    newly_found_jobs: int = 0,
    dashboard_url: str = "https://careerengine.example.com",
) -> str:
    return build_daily_email_report(
        health_records=health_records or [],
        total_jobs_collected=total_jobs_collected,
        qualified_jobs=qualified_jobs if qualified_jobs is not None else len(jobs),
        top_ranked_jobs=jobs,
        additional_qualified_jobs=max(len(jobs) - 5, 0),
        newly_found_jobs=newly_found_jobs,
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
        [make_job(1), make_job(2)],
        qualified_jobs=40,
        newly_found_jobs=3,
        dashboard_url="https://careerengine.example.com",
    )

    assert report.startswith("Dear Ceren,")
    assert "Your CareerEngine job queue has been updated." in report
    assert "Open dashboard:\nhttps://careerengine.example.com" in report
    assert "Newly found jobs today: 3" in report
    assert "Top 5 ranked roles:" in report
    assert "1. Company 1 — Software Engineer 1 — Boston, MA" in report
    assert "2. Company 2 — Software Engineer 2 — Boston, MA" in report
    assert "Active qualified opportunities ranked: 40" in report
    assert "Best of luck,\nCareerEngine" in report

    assert "Score Guide:" not in report
    assert "Description Similarity Guide:" not in report
    assert "CareerEngine recommendation:" not in report
    assert "Why CareerEngine selected this role:" not in report


def test_daily_email_report_limits_top_roles_to_five():
    jobs = [make_job(index) for index in range(1, 7)]

    report = build_report(jobs)

    assert "1. Company 1 — Software Engineer 1 — Boston, MA" in report
    assert "5. Company 5 — Software Engineer 5 — Boston, MA" in report
    assert "6. Company 6 — Software Engineer 6 — Boston, MA" not in report


def test_daily_email_report_handles_no_ranked_roles():
    report = build_report([], total_jobs_collected=0, qualified_jobs=0)

    assert "No ranked opportunities found with the current filters." in report
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
