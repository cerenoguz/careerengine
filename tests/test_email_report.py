from datetime import date

from src.models import Job, SourceHealth
from src.reporting.email_report import (
    build_daily_email_report,
    format_opportunity_type,
    format_report_date,
    format_subject_date,
    format_work_authorization_signal,
)


def make_job(index: int = 1) -> Job:
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


def test_daily_email_report_uses_formal_company_style_without_separator_lines():
    report = build_daily_email_report(
        health_records=[],
        total_jobs_collected=1,
        recommended_jobs_before_deduplication=1,
        new_recommended_jobs=[make_job()],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
    )

    assert report.startswith("Dear Ceren,")
    assert "Here is your CareerEngine Daily Opportunity Report for" in report
    assert "CareerEngine reviewed your configured company sources" in report
    assert "Recommended opportunities are listed below in ranked order." in report
    assert "Best of luck,\nCareerEngine" in report
    assert "Top Ranked Opportunities:" in report

    assert "Summary:" in report
    assert "Score Guide:" in report
    assert "Description Similarity Guide:" in report
    assert "Source Health:" in report

    assert "-------" not in report
    assert "====" not in report


def test_daily_email_report_uses_clear_recommendation_field_names():
    report = build_daily_email_report(
        health_records=[],
        total_jobs_collected=1,
        recommended_jobs_before_deduplication=1,
        new_recommended_jobs=[make_job()],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
    )

    assert "#1. Company 1 — Software Engineer 1" in report
    assert "Location: Boston, MA" in report
    assert "CareerEngine recommendation: Excellent match" in report
    assert "CareerEngine score: 90.00" in report
    assert "Profile wording alignment: 0.050" in report
    assert "Work authorization review: Likely compatible" in report
    assert "Opportunity type: General early-career review" in report
    assert "Application link: https://example.com/jobs/1" in report
    assert "Why CareerEngine selected this role:" in report
    assert "- Strong CS/Math degree relevance (+15)" in report

    assert "Match strength:" not in report
    assert "Description similarity:" not in report
    assert "Eligibility:" not in report
    assert "Internship:" not in report
    assert "New grad:" not in report


def test_daily_email_report_handles_no_new_recommendations():
    report = build_daily_email_report(
        health_records=[],
        total_jobs_collected=0,
        recommended_jobs_before_deduplication=0,
        new_recommended_jobs=[],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
    )

    assert "No ranked opportunities found with the current filters." in report
    assert "Best of luck,\nCareerEngine" in report


def test_daily_email_report_summarizes_source_health_section():
    report = build_daily_email_report(
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
        total_jobs_collected=10,
        recommended_jobs_before_deduplication=1,
        new_recommended_jobs=[make_job()],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
    )

    assert "Source Health:" in report
    assert "1 successful sources omitted from detailed list." in report
    assert "1 disabled sources listed below." in report
    assert "1 sources need attention." in report
    assert "Disabled Sources:" in report
    assert "- DisabledCo: Disabled for test." in report
    assert "Sources Needing Attention:" in report
    assert "- BrokenCo: http_error (HTTP: 500, Jobs: 0)" in report
    assert "WorkingCo: success" not in report


def test_daily_email_report_supports_global_rank_start():
    report = build_daily_email_report(
        health_records=[],
        total_jobs_collected=1,
        recommended_jobs_before_deduplication=1,
        new_recommended_jobs=[make_job()],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
        rank_start=26,
    )

    assert "#26. Company 1 — Software Engineer 1" in report
