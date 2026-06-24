from src.models import Job
from src.reporting.additional_opportunities_report import (
    save_additional_opportunities_report,
)


def make_job() -> Job:
    return Job(
        id="job-1",
        company="Test Company",
        title="Software Engineer",
        location="Boston, MA",
        description="Python backend role.",
        url="https://example.com/job-1",
        date_posted=None,
        source="test",
        eligibility_status="likely_compatible",
        description_similarity=0.08,
        score=71.5,
        why_matched=["Role match: software engineer (+10)"],
    )


def test_attachment_contains_only_current_additional_opportunities(tmp_path):
    path = tmp_path / "additional.txt"

    save_additional_opportunities_report(
        path=path,
        additional_recommendations=[make_job()],
    )

    content = path.read_text(encoding="utf-8")

    assert "Additional Qualified Opportunities" in content
    assert "Test Company — Software Engineer" in content
    assert "Already-sent duplicate recommendations" not in content


def test_attachment_explains_when_no_extra_jobs_exist(tmp_path):
    path = tmp_path / "additional.txt"

    save_additional_opportunities_report(
        path=path,
        additional_recommendations=[],
    )

    content = path.read_text(encoding="utf-8")

    assert "No additional qualified opportunities today." in content


def test_attachment_supports_global_rank_start(tmp_path):
    path = tmp_path / "additional.txt"

    save_additional_opportunities_report(
        path=path,
        additional_recommendations=[make_job()],
        rank_start=31,
    )

    content = path.read_text(encoding="utf-8")

    assert "#31. Test Company — Software Engineer" in content
    assert "CareerEngine score: 71.50" in content


def test_attachment_shows_new_discovery_label(tmp_path):
    job = make_job()
    job.is_new_discovery = True

    path = tmp_path / "additional.txt"
    save_additional_opportunities_report(
        path=path,
        additional_recommendations=[job],
    )

    content = path.read_text(encoding="utf-8")

    assert "#26. Test Company — Software Engineer [New 🚨]" in content


def test_attachment_shows_first_found_date_for_existing_job(tmp_path):
    job = make_job()
    job.first_found_date = "2026-06-20"

    path = tmp_path / "additional.txt"
    save_additional_opportunities_report(
        path=path,
        additional_recommendations=[job],
    )

    content = path.read_text(encoding="utf-8")

    assert (
        "#26. Test Company — Software Engineer "
        "[First found: June 20, 2026]"
    ) in content
