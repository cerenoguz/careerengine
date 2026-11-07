from src.main import enrich_jobs, is_recommendable_job
from src.models import Job
from src.ranking.pipeline import dedupe_jobs, rank_jobs

PROFILE = "Python backend engineer with SQL, APIs and cloud experience."
DESCRIPTION = "Build Python backend services and SQL APIs on AWS."


def make_job(job_id: str, title: str, location: str = "Boston, MA", description: str = DESCRIPTION) -> Job:
    return Job(
        id=job_id, company="Acme", title=title, location=location, description=description,
        url=f"https://example.com/{job_id}", date_posted=None, source="test",
    )


def test_same_role_listed_per_office_is_merged_with_all_locations():
    jobs = dedupe_jobs([
        make_job("1", "Software Engineer, Early Career (NYC)", "New York, NY"),
        make_job("2", "Software Engineer, Early Career (SF)", "San Francisco, CA"),
    ])

    assert len(jobs) == 1
    assert jobs[0].id == "1"
    assert jobs[0].location == "New York, NY; San Francisco, CA"


def test_different_descriptions_are_not_merged():
    jobs = dedupe_jobs([
        make_job("1", "Software Engineer (Payments)", description="Payments work."),
        make_job("2", "Software Engineer (Payments)", description="Fraud work."),
    ])

    assert len(jobs) == 2


def test_different_companies_are_not_merged():
    other = make_job("2", "Software Engineer")
    other.company = "Globex"

    assert len(dedupe_jobs([make_job("1", "Software Engineer"), other])) == 2


def test_many_locations_are_summarised():
    jobs = dedupe_jobs([make_job(str(i), "Software Engineer", f"City {i}, MA") for i in range(6)])

    assert jobs[0].location.endswith("(+3 more)")


def test_rank_jobs_orders_best_first_and_fills_every_field():
    jobs = [
        make_job("plain", "Software Engineer"),
        make_job("grad", "New Grad Software Engineer"),
        make_job("level2", "Software Engineer II"),
    ]
    enrich_jobs(jobs)
    assert all(is_recommendable_job(job) for job in jobs)

    status = rank_jobs(jobs, PROFILE)

    assert status in {"disabled", "available", "unavailable"}
    assert [job.id for job in jobs][0] == "grad"
    assert jobs[0].score > jobs[1].score >= jobs[2].score
    for job in jobs:
        assert 0.0 <= job.score <= 100.0
        assert job.profile_fit_score == job.score
        assert job.profile_fit_band in {"excellent", "strong", "good", "fair"}
        assert set(job.match_components) == {"level", "role", "skills", "semantic", "authorization"}
        assert job.why_matched


def test_ties_are_broken_deterministically():
    jobs = [make_job("b", "Software Engineer"), make_job("a", "Software Engineer")]
    enrich_jobs(jobs)
    rank_jobs(jobs, PROFILE)

    first = [job.id for job in jobs]
    rank_jobs(jobs, PROFILE)

    assert [job.id for job in jobs] == first


def test_empty_pool_is_handled():
    assert rank_jobs([], PROFILE) == "no_jobs"
