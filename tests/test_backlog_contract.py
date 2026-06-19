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
        eligibility_status="likely_compatible",
        description_similarity=0.05,
        score=score,
        why_matched=[],
    )


def configure_temp_database(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "careerengine.sqlite")
    database.initialize_database()


def rank(jobs: list[Job]) -> list[Job]:
    return sorted(jobs, key=lambda job: job.score, reverse=True)


def test_day_one_marks_only_email_body_jobs_seen(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    day_one_jobs = [
        make_job(f"day-one-{index}", score=1000 - index)
        for index in range(50)
    ]

    ranked_day_one = rank(day_one_jobs)
    email_body_jobs = ranked_day_one[:25]
    attachment_jobs = ranked_day_one[25:]

    database.save_seen_jobs(email_body_jobs)
    database.sync_pending_jobs(attachment_jobs)

    assert database.get_seen_job_count() == 25
    assert database.filter_new_jobs(attachment_jobs) == attachment_jobs
    assert database.get_pending_job_ids() == {
        job.id for job in attachment_jobs
    }


def test_day_two_ranks_old_backlog_and_new_jobs_together(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    day_one_jobs = [
        make_job(f"day-one-{index}", score=1000 - index)
        for index in range(50)
    ]

    ranked_day_one = rank(day_one_jobs)
    database.save_seen_jobs(ranked_day_one[:25])
    database.sync_pending_jobs(ranked_day_one[25:])

    new_high_priority_jobs = [
        make_job(f"day-two-high-{index}", score=2000 - index)
        for index in range(10)
    ]
    new_lower_priority_jobs = [
        make_job(f"day-two-low-{index}", score=500 - index)
        for index in range(20)
    ]

    day_two_candidate_pool = database.filter_new_jobs(
        ranked_day_one[25:]
        + new_high_priority_jobs
        + new_lower_priority_jobs
    )

    ranked_day_two = rank(day_two_candidate_pool)
    email_body_jobs = ranked_day_two[:25]
    attachment_jobs = ranked_day_two[25:]

    assert [job.id for job in email_body_jobs[:10]] == [
        job.id for job in new_high_priority_jobs
    ]

    database.save_seen_jobs(email_body_jobs)
    database.sync_pending_jobs(attachment_jobs)

    assert database.get_seen_job_count() == 50
    assert database.filter_new_jobs(attachment_jobs) == attachment_jobs
    assert database.get_pending_job_ids() == {
        job.id for job in attachment_jobs
    }
    assert len(attachment_jobs) == 30


def test_closed_or_no_longer_qualified_pending_job_is_removed(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    closed_job = make_job("closed-job", score=60.0)
    active_job = make_job("active-job", score=55.0)

    database.sync_pending_jobs([closed_job, active_job])
    database.sync_pending_jobs([active_job])

    assert database.get_pending_job_ids() == {"active-job"}


def test_only_one_successful_delivery_can_be_recorded_per_date(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    delivery_date = "2026-06-19"

    database.record_successful_delivery(
        delivery_date=delivery_date,
        run_id="run-one",
        environment="test",
    )
    database.record_successful_delivery(
        delivery_date=delivery_date,
        run_id="run-two",
        environment="test",
    )

    with database.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM daily_deliveries WHERE delivery_date = ?;",
            (delivery_date,),
        ).fetchone()[0]

    assert count == 1
