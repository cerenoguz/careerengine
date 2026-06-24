from pathlib import Path

from src.models import Job
from src.storage import database


def make_job(job_id: str, score: float) -> Job:
    return Job(
        id=job_id,
        company="Test Company",
        title="Software Engineer",
        location="Boston, MA",
        description="Python backend role.",
        url=f"https://example.com/{job_id}",
        date_posted=None,
        source="test",
        score=score,
    )


def configure_temp_database(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "careerengine.sqlite")
    database.initialize_database()


def rank(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: job.score, reverse=True)


def apply_discovery_metadata(jobs: list[Job]) -> None:
    discovery_info = database.record_job_discoveries(jobs)

    for job in jobs:
        first_found_date, is_new_discovery = discovery_info[job.id]
        job.first_found_date = first_found_date
        job.is_new_discovery = is_new_discovery


def test_first_daily_scan_marks_all_current_jobs_new(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    jobs = [
        make_job("job-1", 90.0),
        make_job("job-2", 80.0),
        make_job("job-3", 70.0),
    ]

    apply_discovery_metadata(jobs)

    assert all(job.is_new_discovery for job in jobs)
    assert all(
        job.first_found_date == database.current_new_york_date()
        for job in jobs
    )


def test_next_scan_reranks_all_current_jobs_without_hiding_old_jobs(
    monkeypatch,
    tmp_path,
):
    configure_temp_database(monkeypatch, tmp_path)

    day_one_jobs = [
        make_job("old-high", 90.0),
        make_job("old-low", 40.0),
    ]
    apply_discovery_metadata(day_one_jobs)

    day_two_jobs = [
        make_job("old-high", 75.0),
        make_job("old-low", 95.0),
        make_job("new-job", 85.0),
    ]
    apply_discovery_metadata(day_two_jobs)

    ranked_jobs = rank(day_two_jobs)

    assert [job.id for job in ranked_jobs] == [
        "old-low",
        "new-job",
        "old-high",
    ]

    old_jobs = [job for job in day_two_jobs if job.id.startswith("old-")]
    new_job = next(job for job in day_two_jobs if job.id == "new-job")

    assert all(not job.is_new_discovery for job in old_jobs)
    assert new_job.is_new_discovery is True


def test_jobs_absent_from_todays_scan_are_not_in_todays_ranked_list(
    monkeypatch,
    tmp_path,
):
    configure_temp_database(monkeypatch, tmp_path)

    yesterday_jobs = [
        make_job("still-open", 80.0),
        make_job("removed-from-site", 95.0),
    ]
    apply_discovery_metadata(yesterday_jobs)

    todays_jobs = [make_job("still-open", 80.0)]
    apply_discovery_metadata(todays_jobs)

    assert [job.id for job in rank(todays_jobs)] == ["still-open"]
