from src.main import is_recommendable_job
from src.models import Job
from src.ranking.rule_score import classify_cs_relevance, score_job

PARTNER_TEAM_DESCRIPTION = (
    "Build Python backend APIs for payments. "
    "Partner with the finance, legal, sales, and marketing teams."
)


def make_job(title: str, description: str) -> Job:
    score, _ = score_job(title, description, "unclear")

    return Job(
        id="job-1",
        company="Test Company",
        title=title,
        location="Boston, MA",
        description=description,
        url="https://example.com/job-1",
        date_posted=None,
        source="test",
        score=score,
    )


def test_partner_team_mentions_in_description_do_not_exclude_engineering_role():
    score, _ = score_job(
        "Software Engineer, Payments",
        PARTNER_TEAM_DESCRIPTION,
        "unclear",
    )

    assert score > 0


def test_partner_team_mentions_do_not_change_cs_relevance():
    status, _ = classify_cs_relevance(
        "Software Engineer, Payments",
        PARTNER_TEAM_DESCRIPTION,
    )

    assert status == "strong_cs_relevance"


def test_engineering_role_mentioning_partner_teams_is_recommendable():
    job = make_job("Software Engineer, Payments", PARTNER_TEAM_DESCRIPTION)

    assert is_recommendable_job(job) is True


def test_sales_title_is_still_excluded():
    score, _ = score_job("Sales Engineer", "Python and APIs.", "unclear")

    assert score == -999.0
    assert classify_cs_relevance("Sales Engineer", "Python and APIs.")[0] == "excluded"
    assert is_recommendable_job(make_job("Sales Engineer", "Python and APIs.")) is False
