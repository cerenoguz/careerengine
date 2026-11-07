import json
from datetime import date

from src.dashboard import supabase_sync
from src.dashboard.buckets import classify_dashboard_bucket
from src.models import Job

RUN_DATE = date(2026, 10, 29)


def make_job(score=80.0, **kwargs) -> Job:
    return Job(
        id="job-1", company="Acme", title="Software Engineer", location="Boston, MA",
        description="Python.", url="https://example.com/1", date_posted=None, source="test",
        score=score, profile_fit_band="strong", why_matched=["Level: entry", "Role: backend"], **kwargs,
    )


def test_score_is_published_in_both_score_columns():
    payload = supabase_sync._payload_for_job(make_job(83.4), rank=1, run_date=RUN_DATE)

    assert payload["final_score"] == payload["ai_profile_fit"] == 83.4
    assert payload["reason"] == "Level: entry · Role: backend"


def test_a_score_of_zero_is_kept_not_dropped():
    payload = supabase_sync._payload_for_job(make_job(0.0), rank=1, run_date=RUN_DATE)

    assert payload["final_score"] == 0.0
    assert payload["ai_profile_fit"] == 0.0


def test_badge_fields_are_populated():
    new_grad = supabase_sync._payload_for_job(make_job(is_new_grad=True, eligibility_status="likely_compatible"), 1, RUN_DATE)
    entry = supabase_sync._payload_for_job(make_job(level="entry"), 1, RUN_DATE)
    no_sponsor = supabase_sync._payload_for_job(make_job(sponsorship_language="unavailable"), 1, RUN_DATE)

    assert new_grad["opportunity_type"] == "New Grad"
    assert new_grad["work_auth_review"] == "Likely compatible"
    assert entry["opportunity_type"] == "Early Career"
    assert no_sponsor["work_auth_review"] == "Sponsorship unavailable"


def test_buckets_follow_the_match_score():
    assert classify_dashboard_bucket(85) == "apply_now"
    assert classify_dashboard_bucket(72) == "apply_now"
    assert classify_dashboard_bucket(65) == "review"
    assert classify_dashboard_bucket(40) == "archive"
    assert classify_dashboard_bucket(None) == "archive"


def test_sync_upserts_then_deactivates_rows_not_seen_today(monkeypatch):
    calls = []
    monkeypatch.setenv("CAREERENGINE_DASHBOARD_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    monkeypatch.setattr(
        supabase_sync, "_request",
        lambda method, url, key, body, prefer: calls.append((method, url, body)),
    )
    jobs = []
    for index in range(12):
        job = make_job(70.0 + index)
        job.id = f"job-{index}"
        jobs.append(job)

    supabase_sync.sync_jobs_to_supabase(jobs, run_date=RUN_DATE)

    assert [call[0] for call in calls] == ["POST", "PATCH"]
    assert len(calls[0][2]) == 12
    assert "last_seen_date=lt.2026-10-29" in calls[1][1]
    assert "is_active=eq.true" in calls[1][1]
    assert calls[1][2] == {"is_active": False}


def test_stale_cleanup_is_skipped_for_a_suspiciously_small_run(monkeypatch):
    calls = []
    monkeypatch.setenv("CAREERENGINE_DASHBOARD_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    monkeypatch.setattr(supabase_sync, "_request", lambda *args: calls.append(args))

    supabase_sync.sync_jobs_to_supabase([make_job()], run_date=RUN_DATE)

    assert [call[0] for call in calls] == ["POST"]


def test_payload_is_json_serialisable():
    json.dumps(supabase_sync._payload_for_job(make_job(), 1, RUN_DATE))


def test_sync_accepts_the_run_date_as_a_string(monkeypatch):
    """main() passes the New York delivery date as an ISO string, not a date."""
    calls = []
    monkeypatch.setenv("CAREERENGINE_DASHBOARD_ENABLED", "true")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    monkeypatch.setattr(supabase_sync, "_request", lambda method, url, key, body, prefer: calls.append((method, url)))
    jobs = []
    for index in range(12):
        job = make_job(70.0 + index)
        job.id = f"job-{index}"
        jobs.append(job)

    supabase_sync.sync_jobs_to_supabase(jobs, run_date="2026-11-06")

    assert [call[0] for call in calls] == ["POST", "PATCH"]
    assert "last_seen_date=lt.2026-11-06" in calls[1][1]
