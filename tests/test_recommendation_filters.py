from src.main import is_recommendable_job, is_us_opt_location
from src.models import Job


def make_job(
    title: str,
    location: str,
    description: str,
    score: float = 50.0,
    eligibility_status: str = "unclear",
) -> Job:
    return Job(
        id="test-id",
        company="Test Company",
        title=title,
        location=location,
        description=description,
        url="https://example.com/job",
        date_posted=None,
        source="test",
        score=score,
        eligibility_status=eligibility_status,
    )


def test_us_location_with_state_abbreviation_passes() -> None:
    assert is_us_opt_location("Boston, MA") is True


def test_us_location_with_state_name_passes() -> None:
    assert is_us_opt_location("New York, New York, USA") is True


def test_us_remote_location_passes() -> None:
    assert is_us_opt_location("Remote, US") is True


def test_non_us_location_fails() -> None:
    assert is_us_opt_location("Lisbon, Portugal") is False


def test_early_career_software_engineer_in_us_is_recommendable() -> None:
    job = make_job(
        title="Software Engineer - Early Career",
        location="Boston, MA",
        description=(
            "Build backend services using Python, SQL, REST APIs, databases, "
            "debugging, distributed systems, and software engineering best practices."
        ),
    )

    assert is_recommendable_job(job) is True


def test_non_us_early_career_software_engineer_is_not_recommendable() -> None:
    job = make_job(
        title="Software Engineer - Early Career",
        location="Lisbon, Portugal",
        description=(
            "Build backend services using Python, SQL, REST APIs, databases, "
            "and distributed systems."
        ),
    )

    assert is_recommendable_job(job) is False


def test_senior_software_engineer_is_not_recommendable() -> None:
    job = make_job(
        title="Senior Backend Software Engineer",
        location="New York, NY",
        description=(
            "Build backend systems using Python, SQL, REST APIs, databases, "
            "and distributed systems."
        ),
    )

    assert is_recommendable_job(job) is False


def test_technical_escalations_engineer_with_cs_duties_is_recommendable() -> None:
    job = make_job(
        title="Technical Escalations Engineer",
        location="New York, NY",
        description=(
            "Debug production issues involving Java, APIs, backend systems, logs, "
            "databases, SQL, cloud infrastructure, and distributed systems."
        ),
    )

    assert is_recommendable_job(job) is True


def test_help_desk_role_is_not_recommendable() -> None:
    job = make_job(
        title="Help Desk Technician",
        location="Boston, MA",
        description=(
            "Provide help desk support, password resets, device setup, "
            "desktop troubleshooting, and office IT assistance."
        ),
    )

    assert is_recommendable_job(job) is False


def test_marketing_role_is_not_recommendable() -> None:
    job = make_job(
        title="Marketing Associate",
        location="New York, NY",
        description="Support campaign planning, marketing operations, and brand strategy.",
    )

    assert is_recommendable_job(job) is False


def test_likely_incompatible_authorization_is_not_recommendable() -> None:
    job = make_job(
        title="Software Engineer - Early Career",
        location="Boston, MA",
        description=(
            "Build backend services using Python, SQL, REST APIs, databases, "
            "and distributed systems."
        ),
        eligibility_status="likely_incompatible",
    )

    assert is_recommendable_job(job) is False

from src.main import is_us_opt_location


def test_location_filter_rejects_country_prefixes_that_look_like_us_states():
    assert is_us_opt_location("DE-Berlin-Trion Building") is False
    assert is_us_opt_location("CA-Ontario-Toronto") is False
    assert is_us_opt_location("IN-Pune") is False


def test_location_filter_still_accepts_us_locations_with_state_codes():
    assert is_us_opt_location("US-CA-Menlo Park") is True
    assert is_us_opt_location("Boston, MA") is True
    assert is_us_opt_location("Remote - US") is True
