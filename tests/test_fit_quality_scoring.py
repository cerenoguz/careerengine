"""The match score reflects fit to the candidate's experience, nothing else."""

from src.main import enrich_jobs
from src.models import Job
from src.ranking.pipeline import rank_jobs
from src.ranking.rule_score import is_new_grad

PROFILE = (
    "Backend engineer experienced with Python, SQL, PostgreSQL, REST APIs, AWS, Docker "
    "and distributed systems."
)

MATCHING = "Build backend services using Python, SQL, PostgreSQL, REST APIs, AWS and Docker."
UNRELATED = "Build services using Scala, Kafka, Spark, Terraform and Kubernetes."


def make_job(job_id: str, title: str, description: str) -> Job:
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


def scored(*specs) -> dict[str, Job]:
    jobs = [make_job(f"job-{i}", title, description) for i, (title, description) in enumerate(specs)]
    enrich_jobs(jobs)
    rank_jobs(jobs, PROFILE)
    return {job.id: job for job in jobs}


def test_role_matching_the_candidates_skills_outranks_one_that_does_not():
    jobs = scored(("Software Engineer", UNRELATED), ("Software Engineer", MATCHING))

    assert jobs["job-1"].score > jobs["job-0"].score


def test_entry_level_label_does_not_change_the_score():
    jobs = scored(
        ("New Grad Software Engineer", MATCHING),
        ("Software Engineer I", MATCHING),
        ("Software Engineer", MATCHING),
        ("Software Engineer II", MATCHING),
    )

    assert len({round(job.score, 6) for job in jobs.values()}) == 1


def test_a_skill_matched_level_two_role_outranks_a_poorly_matched_new_grad_role():
    jobs = scored(("New Grad Software Engineer", UNRELATED), ("Software Engineer II", MATCHING))

    assert jobs["job-1"].score > jobs["job-0"].score


def test_sponsorship_wording_does_not_change_the_score():
    jobs = scored(
        ("Software Engineer", MATCHING + " Visa sponsorship is available."),
        ("Software Engineer", MATCHING + " Visa sponsorship is not available."),
        ("Software Engineer", MATCHING),
    )

    assert len({round(job.score, 6) for job in jobs.values()}) == 1
    assert jobs["job-1"].sponsorship_language == "unavailable"
    assert jobs["job-0"].sponsorship_language == "available"


def test_principal_software_engineer_i_is_not_new_grad():
    assert is_new_grad("Principal Software Engineer I - Snowhouse Foundation", MATCHING) is False
