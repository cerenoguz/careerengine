import pytest

from src import main as main_module
from src.models import Job, SourceHealth
from src.storage import database


def make_job() -> Job:
    return Job(
        id="job-1",
        company="Test Company",
        title="New Grad Software Engineer",
        location="Boston, MA",
        description="Python backend role.",
        url="https://example.com/job-1",
        date_posted=None,
        source="test",
    )


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    """Run main() against one fake job, a temp database, and a temp cwd."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "careerengine.sqlite")
    monkeypatch.delenv("CAREERENGINE_ENABLE_SEMANTIC_SHADOW", raising=False)

    monkeypatch.setattr(main_module, "load_company_configs", lambda: [{"name": "Test Company"}])
    monkeypatch.setattr(main_module, "load_candidate_profile", lambda: "python backend")
    monkeypatch.setattr(
        main_module,
        "collect_jobs_for_company",
        lambda config: (
            [make_job()],
            SourceHealth("Test Company", "test", "success", 200, 1),
        ),
    )
    monkeypatch.setattr(main_module, "sync_jobs_to_supabase", lambda *a, **k: None)

    return monkeypatch


def stored_discovery_count() -> int:
    with database.get_connection() as connection:
        return connection.execute("SELECT COUNT(*) FROM job_discoveries;").fetchone()[0]


def test_failed_email_send_does_not_mark_jobs_as_discovered(pipeline):
    def failing_send(**kwargs):
        raise RuntimeError("SMTP unavailable")

    pipeline.setattr(main_module, "send_email_report", failing_send)

    with pytest.raises(RuntimeError):
        main_module.main()

    assert stored_discovery_count() == 0
    _, is_new = database.get_job_discoveries([make_job()])["job-1"]
    assert is_new is True


def test_job_is_still_new_in_the_email_after_a_failed_send_is_retried(pipeline):
    sent_bodies: list[str] = []

    def failing_send(**kwargs):
        raise RuntimeError("SMTP unavailable")

    def successful_send(**kwargs):
        sent_bodies.append(kwargs["body"])
        return True

    pipeline.setattr(main_module, "send_email_report", failing_send)
    with pytest.raises(RuntimeError):
        main_module.main()

    pipeline.setattr(main_module, "send_email_report", successful_send)
    main_module.main()

    assert "Newly found jobs today: 1" in sent_bodies[0]


def test_successful_send_marks_jobs_as_discovered(pipeline):
    pipeline.setattr(main_module, "send_email_report", lambda **kwargs: True)

    main_module.main()

    assert stored_discovery_count() == 1
    _, is_new = database.get_job_discoveries([make_job()])["job-1"]
    assert is_new is False


def test_discoveries_are_still_saved_when_email_is_disabled(pipeline):
    pipeline.setattr(main_module, "send_email_report", lambda **kwargs: False)

    main_module.main()

    assert stored_discovery_count() == 1
