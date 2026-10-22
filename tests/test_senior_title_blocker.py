import pytest

from src.main import enrich_jobs, get_rejection_reasons, is_recommendable_job
from src.models import Job
from src.ranking.rule_score import has_unrealistic_senior_title

PROFILE = "Python backend engineer with SQL and distributed systems experience."

GENERIC_DESCRIPTION = (
    "Build Python and C++ backend services and REST APIs on cloud infrastructure "
    "with SQL databases, Docker, Kubernetes and distributed systems. "
    "Bachelor's degree in Computer Science."
)

JUNIOR_FRIENDLY_DESCRIPTION = (
    "Recent graduates are encouraged to apply. Candidates with 0-2 years of "
    "experience are welcome. Build Python backend services and REST APIs with SQL "
    "databases, Docker and distributed systems. Bachelor's degree in Computer Science."
)


def enriched_job(title: str, description: str = GENERIC_DESCRIPTION) -> Job:
    job = Job(
        id="job-1",
        company="Test Company",
        title=title,
        location="Boston, MA",
        description=description,
        url="https://example.com/job-1",
        date_posted=None,
        source="test",
    )
    enrich_jobs([job], PROFILE)
    return job


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer - Marketplace",
        "Senior Embedded Software Engineer",
        "Senior Machine Learning Engineer, Discovery Recommendations",
        "Staff Software Engineer",
        "Principal Backend Engineer",
        "Lead Software Engineer",
        "Engineering Manager, Platform",
    ],
)
def test_senior_titles_are_not_recommended(title):
    job = enriched_job(title)

    assert job.score > 0  # the old filter let these through on score alone
    assert is_recommendable_job(job) is False
    assert "senior-level title without junior-friendly evidence" in get_rejection_reasons(job)


def test_senior_title_with_junior_friendly_description_is_still_recommended():
    job = enriched_job("Senior Software Engineer", JUNIOR_FRIENDLY_DESCRIPTION)

    assert job.title_description_conflict is True
    assert is_recommendable_job(job) is True


@pytest.mark.parametrize(
    "title",
    [
        "Software Engineer",
        "New Grad Software Engineer",
        "Software Engineer I",
        "Member of Technical Staff (AI Software Engineer, Agents)",
    ],
)
def test_non_senior_titles_are_still_recommended(title):
    job = enriched_job(title)

    assert is_recommendable_job(job) is True


def test_member_of_technical_staff_is_not_treated_as_senior():
    assert has_unrealistic_senior_title("Member of Technical Staff") is False
    assert has_unrealistic_senior_title("Staff Software Engineer") is True
    assert has_unrealistic_senior_title("Senior Member of Technical Staff") is True
