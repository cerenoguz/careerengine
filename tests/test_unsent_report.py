from pathlib import Path

from src.models import Job
from src.reporting.unsent_report import save_unsent_recommendations_report


def make_job(index: int, title: str) -> Job:
    return Job(
        id=str(index),
        company=f"Company {index}",
        title=title,
        location="Boston, MA",
        description="Python backend software engineering role.",
        url=f"https://example.com/jobs/{index}",
        date_posted=None,
        source="test",
        eligibility_status="likely_compatible",
        description_similarity=0.05,
        score=75.0,
        why_matched=["Role match"],
    )


def test_unsent_report_has_duplicate_and_hidden_by_cap_sections(tmp_path: Path):
    report_path = tmp_path / "unsent_recommendations.txt"

    saved_path = save_unsent_recommendations_report(
        path=report_path,
        duplicate_recommendations=[
            make_job(1, "Already Sent Software Engineer"),
        ],
        hidden_by_email_cap_recommendations=[
            make_job(2, "Held By Cap Backend Engineer"),
        ],
    )

    report = report_path.read_text(encoding="utf-8")

    assert saved_path == report_path
    assert "CareerEngine Unsent Recommendations Report" in report
    assert "Section 1: Already-sent duplicate recommendations" in report
    assert "Already Sent Software Engineer" in report
    assert "Section 2: Qualified recommendations held because of daily email cap" in report
    assert "Held By Cap Backend Engineer" in report
    assert "They should remain eligible for future reports." in report


def test_unsent_report_handles_empty_sections(tmp_path: Path):
    report_path = tmp_path / "unsent_recommendations.txt"

    save_unsent_recommendations_report(
        path=report_path,
        duplicate_recommendations=[],
        hidden_by_email_cap_recommendations=[],
    )

    report = report_path.read_text(encoding="utf-8")

    assert "No already-sent duplicate recommendations." in report
    assert "No qualified recommendations were held by the email cap." in report
