"""Ordering guarantees of the unified match score, on realistic job pairs."""

from src.main import enrich_jobs
from src.models import Job
from src.ranking.pipeline import rank_jobs
from src.ranking.rule_score import is_new_grad

PROFILE = "Python backend engineer with SQL, APIs, cloud and distributed systems experience."

DESCRIPTION = """
Build backend services using Python, Java, SQL, APIs, databases, cloud systems,
and distributed systems.
"""


def make_job(job_id: str, title: str, description: str = DESCRIPTION) -> Job:
    return Job(
        id=job_id,
        company="Test Company",
        title=title,
        location="Boston, MA",
        description=description,
        url=f"https://example.com/{job_id}",
        date_posted=None,
        source="test",
    )


def ranked(*titles_and_descriptions) -> list[Job]:
    jobs = [
        make_job(f"job-{index}", title, description)
        for index, (title, description) in enumerate(titles_and_descriptions)
    ]
    enrich_jobs(jobs)
    rank_jobs(jobs, PROFILE)
    return jobs


def test_software_engineer_i_outranks_close_level_two_role():
    jobs = {job.title: job for job in ranked(
        ("Software Engineer I (Quality)", DESCRIPTION),
        ("Software Engineer II (Backend, Platform)", DESCRIPTION),
    )}

    assert jobs["Software Engineer I (Quality)"].score > jobs["Software Engineer II (Backend, Platform)"].score


def test_new_grad_outranks_skill_richer_level_two_role():
    new_grad, level_two = ranked(
        ("New Grad Software Engineer", "Build services using Python and APIs."),
        ("Software Engineer (L2)", DESCRIPTION),
    )[0:2]

    assert new_grad.title == "New Grad Software Engineer"
    assert new_grad.score > level_two.score


def test_explicit_early_career_beats_unlabelled_role_with_same_content():
    early, plain = ranked(
        ("Software Engineer, Early Career", DESCRIPTION),
        ("Software Engineer", DESCRIPTION),
    )

    assert early.score > plain.score


def test_asking_for_three_years_ranks_below_the_same_role_without_it():
    plain, three_years = ranked(
        ("Software Engineer", DESCRIPTION),
        ("Software Engineer", DESCRIPTION + "\nRequirements\n- 3+ years of professional software engineering experience"),
    )

    assert plain.score > three_years.score


def test_principal_software_engineer_i_is_not_new_grad():
    assert is_new_grad("Principal Software Engineer I - Snowhouse Foundation", DESCRIPTION) is False
