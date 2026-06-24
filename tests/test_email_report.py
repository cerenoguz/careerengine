from datetime import date

from src.models import Job, SourceHealth
from src.reporting.email_report import (
    build_daily_email_report,
    format_discovery_label,
    format_opportunity_type,
    format_report_date,
    format_subject_date,
    format_work_authorization_signal,
)


def make_job(
    index: int = 1,
    *,
    first_found_date: str | None = None,
    is_new_discovery: bool = False,
) -> Job:
    return Job(
        id=str(index),
        company=f"Company {index}",
        title=f"Software Engineer {index}",
        location="Boston, MA",
        description="Python backend software engineering role.",
        url=f"https://example.com/jobs/{index}",
        date_posted=None,
        source="test",
        eligibility_status="likely_compatible",
        description_similarity=0.05,
        score=90.0,
        why_matched=["Strong CS/Math degree relevance (+15)", "Role match"],
        first_found_date=first_found_date,
        is_new_discovery=is_new_discovery,
    )


def build_report(
    jobs: list[Job],
    *,
    health_records: list[SourceHealth] | None = None,
    total_jobs_collected: int = 1,
    qualified_jobs: int | None = None,
    additional_qualified_jobs: int = 0,
    rank_start: int = 1,
) -> str:
    return build_daily_email_report(
        health_records=health_records or [],
        total_jobs_collected=total_jobs_collected,
        qualified_jobs=qualified_jobs if qualified_jobs is not None else len(jobs),
        top_ranked_jobs=jobs,
        additional_qualified_jobs=additional_qualified_jobs,
        rank_start=rank_start,
    )


def test_format_report_date():
    assert format_report_date(date(2026, 6, 16)) == "Tuesday - June 16, 2026"


def test_format_subject_date():
    assert format_subject_date(date(2026, 6, 16)) == "6/16/2026"


def test_format_work_authorization_signal():
    assert format_work_authorization_signal("likely_compatible") == "Likely compatible"
    assert format_work_authorization_signal("unclear") == "Needs review"
    assert format_work_authorization_signal("likely_incompatible") == "Likely incompatible"


def test_format_opportunity_type():
    job = make_job()

    assert format_opportunity_type(job) == "General early-career review"

    job.is_new_grad = True
    assert format_opportunity_type(job) == "New-grad / early-career aligned"

    job.is_internship = True
    assert format_opportunity_type(job) == "Internship / new-grad aligned"

    job.is_new_grad = False
    assert format_opportunity_type(job) == "Internship"


def test_format_discovery_label_marks_new_jobs():
    job = make_job(is_new_discovery=True)

    assert format_discovery_label(job) == "New 🚨"


def test_format_discovery_label_shows_original_discovery_date():
    job = make_job(first_found_date="2026-06-20")

    assert format_discovery_label(job) == "First found: June 20, 2026"


def test_daily_email_report_uses_live_ranking_wording():
    report = build_report(
        [make_job(is_new_discovery=True)],
        qualified_jobs=40,
        additional_qualified_jobs=15,
    )

    assert report.startswith("Dear Ceren,")
    assert "jobs it successfully observed today" in report
    assert "25 best current matches CareerEngine found today" in report
    assert "Active qualified opportunities ranked: 40" in report
    assert "Additional qualified opportunities attached: 15" in report
    assert "Recommended jobs before deduplication" not in report
    assert "Duplicate recommendations removed" not in report
    assert "Best of luck,\nCareerEngine" in report


def test_daily_email_report_shows_new_discovery_label():
    report = build_report([make_job(is_new_discovery=True)])

    assert "#1. Company 1 — Software Engineer 1 [New 🚨]" in report


def test_daily_email_report_shows_first_found_date_for_existing_job():
    report = build_report([make_job(first_found_date="2026-06-20")])

    assert (
        "#1. Company 1 — Software Engineer 1 "
        "[First found: June 20, 2026]"
    ) in report


def test_daily_email_report_uses_clear_recommendation_field_names():
    report = build_report([make_job(is_new_discovery=True)])

    assert "Location: Boston, MA" in report
    assert "CareerEngine recommendation: Excellent match" in report
    assert "CareerEngine score: 90.00" in report
    assert "Profile wording alignment: 0.050" in report
    assert "Work authorization review: Likely compatible" in report
    assert "Opportunity type: General early-career review" in report
    assert "Application link: https://example.com/jobs/1" in report
    assert "Why CareerEngine selected this role:" in report
    assert "- Strong CS/Math degree relevance (+15)" in report


def test_daily_email_report_handles_no_ranked_recommendations():
    report = build_report(
        [],
        total_jobs_collected=0,
        qualified_jobs=0,
        additional_qualified_jobs=0,
    )

    assert "No ranked opportunities found with the current filters." in report
    assert "Best of luck,\nCareerEngine" in report


def test_daily_email_report_summarizes_source_health_section():
    report = build_report(
        [make_job(is_new_discovery=True)],
        total_jobs_collected=10,
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
            SourceHealth(
                company="BrokenCo",
                source="greenhouse",
                status="http_error",
                http_code=500,
                jobs_found=0,
                reason="Server error.",
            ),
        ],
    )

    assert "1 successful sources omitted from detailed list." in report
    assert "1 disabled sources listed below." in report
    assert "1 sources need attention." in report
    assert "- DisabledCo: Disabled for test." in report
    assert "- BrokenCo: http_error (HTTP: 500, Jobs: 0)" in report


def test_daily_email_report_supports_global_rank_start():
    report = build_report(
        [make_job(is_new_discovery=True)],
        rank_start=26,
    )

    assert "#26. Company 1 — Software Engineer 1 [New 🚨]" in report
