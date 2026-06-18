from pathlib import Path

from src.models import Job
from src.ranking.delivery_queue import prioritize_pending_jobs
from src.storage import database


def make_job(job_id: str, score: float = 70.0) -> Job:
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


def test_cap_held_job_is_pending_but_not_seen(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    held_job = make_job("held-job")

    database.save_pending_jobs([held_job])

    assert held_job.id in database.get_pending_job_ids()
    assert database.filter_new_jobs([held_job]) == [held_job]


def test_successfully_emailed_job_is_seen_and_removed_from_pending(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    emailed_job = make_job("emailed-job")

    database.save_pending_jobs([emailed_job])
    database.save_seen_jobs([emailed_job])
    database.remove_pending_jobs([emailed_job.id])

    assert emailed_job.id not in database.get_pending_job_ids()
    assert database.filter_new_jobs([emailed_job]) == []


def test_pending_jobs_are_prioritized_before_fresh_jobs():
    fresh_high_score = make_job("fresh-high", score=95.0)
    held_lower_score = make_job("held-lower", score=60.0)

    ordered = prioritize_pending_jobs(
        [fresh_high_score, held_lower_score],
        {"held-lower"},
    )

    assert [job.id for job in ordered] == ["held-lower", "fresh-high"]


def test_only_one_successful_delivery_can_be_recorded_per_date(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    delivery_date = "2026-06-18"

    assert database.has_successful_delivery_for_date(delivery_date) is False

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

    assert database.has_successful_delivery_for_date(delivery_date) is True

    with database.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM daily_deliveries WHERE delivery_date = ?;",
            (delivery_date,),
        ).fetchone()[0]

    assert count == 1
