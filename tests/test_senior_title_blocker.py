import pytest

from src.main import enrich_jobs, get_rejection_reasons, is_recommendable_job
from src.models import Job
from src.ranking.level import has_senior_title

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
    enrich_jobs([job])
    return job


@pytest.mark.parametrize(
    "title",
    [
        "Senior Software Engineer - Marketplace",
        "Sr. Software Engineer",
        "Sr Backend Engineer",
        "Senior Embedded Software Engineer",
        "Senior Machine Learning Engineer, Discovery Recommendations",
        "Staff Software Engineer",
        "Principal Backend Engineer",
        "Lead Software Engineer",
        "Engineering Manager, Platform",
        "Software Engineer III",
        "Software Engineer IV, Payments",
        "Software Engineer 5",
        "Software Engineer (L5)",
        "Director of Engineering",
    ],
)
def test_senior_titles_are_not_recommended(title):
    job = enriched_job(title)

    assert is_recommendable_job(job) is False
    assert any(reason.startswith("not entry-level") for reason in get_rejection_reasons(job))


@pytest.mark.parametrize(
    "title",
    ["Senior Software Engineer", "Software Engineer III", "Staff Backend Engineer"],
)
def test_junior_friendly_description_never_overrides_a_senior_title(title):
    """Senior postings routinely carry junior boilerplate (internship programs,
    "0-1 years with Kubernetes"); that must not let them through."""
    job = enriched_job(title, JUNIOR_FRIENDLY_DESCRIPTION)

    assert is_recommendable_job(job) is False


@pytest.mark.parametrize(
    "title",
    [
        "Software Engineer",
        "New Grad Software Engineer",
        "Software Engineer I",
        "Software Engineer II",
        "Member of Technical Staff (AI Software Engineer, Agents)",
    ],
)
def test_non_senior_titles_are_still_recommended(title):
    job = enriched_job(title)

    assert is_recommendable_job(job) is True


def test_member_of_technical_staff_is_not_treated_as_senior():
    assert has_senior_title("Member of Technical Staff") is False
    assert has_senior_title("Staff Software Engineer") is True
    assert has_senior_title("Senior Member of Technical Staff") is True


def test_five_years_required_in_description_blocks_a_plain_title():
    job = enriched_job(
        "Software Engineer",
        GENERIC_DESCRIPTION + "\nRequirements\n- 5+ years of professional software engineering experience",
    )

    assert is_recommendable_job(job) is False
    assert "Requires 5+ years" in " ".join(get_rejection_reasons(job))


def test_phd_titled_roles_are_not_recommended():
    assert is_recommendable_job(enriched_job("PhD University Grad Machine Learning Engineer")) is False


def test_non_engineering_titles_are_not_recommended():
    job = enriched_job("User Experience Researcher, Platform")

    assert "title is not an engineering or data role" in get_rejection_reasons(job)
