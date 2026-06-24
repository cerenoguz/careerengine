from pathlib import Path

from src.models import Job
from src.storage import database


def make_job(job_id: str) -> Job:
    return Job(
        id=job_id,
        company="Test Company",
        title="Software Engineer",
        location="Boston, MA",
        description="Python backend role.",
        url=f"https://example.com/{job_id}",
        date_posted=None,
        source="test",
        score=70.0,
    )


def configure_temp_database(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "careerengine.sqlite")
    database.initialize_database()


def test_first_discovery_is_marked_new(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    discovery_info = database.record_job_discoveries([make_job("job-1")])

    first_found_date, is_new = discovery_info["job-1"]

    assert first_found_date == database.current_new_york_date()
    assert is_new is True


def test_existing_job_keeps_original_first_found_date(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    job = make_job("job-1")

    first_run = database.record_job_discoveries([job])
    second_run = database.record_job_discoveries([job])

    assert second_run["job-1"][0] == first_run["job-1"][0]
    assert second_run["job-1"][1] is False


def test_only_discovered_jobs_are_stored(monkeypatch, tmp_path):
    configure_temp_database(monkeypatch, tmp_path)

    database.record_job_discoveries([make_job("job-1"), make_job("job-2")])

    with database.get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM job_discoveries;"
        ).fetchone()[0]

    assert count == 2
