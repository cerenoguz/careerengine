from src.models import Job, SourceHealth
from src.reporting.email_report import build_daily_email_report


def test_email_report_includes_summary_and_source_health() -> None:
    health_records = [
        SourceHealth(
            company="Test Company",
            source="greenhouse",
            status="success",
            http_code=200,
            jobs_found=10,
            reason=None,
        )
    ]

    email_body = build_daily_email_report(
        health_records=health_records,
        total_jobs_collected=10,
        recommended_jobs_before_deduplication=0,
        new_recommended_jobs=[],
    )

    assert "CareerEngine Daily Job Report" in email_body
    assert "Companies checked: 1" in email_body
    assert "Total jobs collected: 10" in email_body
    assert "Test Company: success" in email_body
    assert "No new recommended jobs found" in email_body


def test_email_report_includes_recommended_job_details() -> None:
    job = Job(
        id="job-1",
        company="Test Company",
        title="Software Engineer - Early Career",
        location="Boston, MA",
        description="Build backend services using Python, SQL, REST APIs, and databases.",
        url="https://example.com/job-1",
        date_posted=None,
        source="test",
        score=75.5,
        eligibility_status="unclear",
        description_similarity=0.42,
        is_internship=False,
        is_new_grad=True,
        why_matched=["Target role: software engineer", "Strong backend skill match"],
    )

    email_body = build_daily_email_report(
        health_records=[],
        total_jobs_collected=1,
        recommended_jobs_before_deduplication=1,
        new_recommended_jobs=[job],
    )

    assert "Software Engineer - Early Career" in email_body
    assert "Boston, MA" in email_body
    assert "Score: 75.50" in email_body
    assert "Description similarity: 0.420" in email_body
    assert "https://example.com/job-1" in email_body
    assert "Target role: software engineer" in email_body
from src.models import SourceHealth
from src.reporting.email_report import build_daily_email_report


def test_daily_email_report_includes_source_status_counts():
    report = build_daily_email_report(
        health_records=[
            SourceHealth(
                company="WorkingCo",
                source="ashby",
                status="success",
                http_code=200,
                jobs_found=10,
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
        recommended_jobs_before_deduplication=2,
        new_recommended_jobs=[],
        duplicate_recommendations_removed=0,
        recommendations_hidden_by_email_cap=0,
    )

    assert "Companies checked: 3" in report
    assert "Successful sources: 1" in report
    assert "Disabled sources: 1" in report
    assert "Sources needing attention: 1" in report
