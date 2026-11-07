from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import date
from typing import Any, Iterable

from src.dashboard.buckets import classify_dashboard_bucket


DASHBOARD_TABLE = "careerengine_jobs"
MIN_JOBS_TO_DEACTIVATE_STALE = 10


def _get(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _stable_job_id(job: Any) -> str:
    existing = _get(job, "job_id") or _get(job, "id")
    if existing:
        return str(existing)

    company = _get(job, "company", "")
    title = _get(job, "title", "")
    url = _get(job, "url") or _get(job, "application_link") or _get(job, "apply_url") or ""

    raw = f"{company}|{title}|{url}".lower().strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_float(job: Any, *names: str) -> float | None:
    """First field that holds a number; a legitimate 0.0 is kept, not skipped."""
    for name in names:
        value = _as_float(_get(job, name, None))
        if value is not None:
            return value
    return None


def _work_auth_review(job: Any) -> str:
    explicit = str(
        _get(job, "work_authorization_review", "")
        or _get(job, "work_auth_review", "")
    )
    if explicit:
        return explicit

    if _get(job, "sponsorship_language", "") == "unavailable":
        return "Sponsorship unavailable"

    if _get(job, "eligibility_status", "") == "likely_compatible":
        return "Likely compatible"

    return "Unclear"


def _opportunity_type(job: Any) -> str:
    explicit = str(_get(job, "opportunity_type", ""))
    if explicit:
        return explicit

    if _get(job, "is_new_grad", False):
        return "New Grad"

    if _get(job, "level", "") == "entry":
        return "Early Career"

    return ""


def _payload_for_job(job: Any, rank: int, run_date: date) -> dict[str, Any]:
    title = str(_get(job, "title", ""))

    # One number: the unified match score. `final_score` and `ai_profile_fit`
    # are both kept populated because existing rows, and the dashboard's sort,
    # use them.
    match_score = _first_float(
        job, "score", "ai_profile_fit", "profile_fit_score", "careerengine_score"
    )

    reasons = _get(job, "why_matched", None) or _get(job, "profile_fit_reasons", None) or []
    reason = str(_get(job, "reason", "") or _get(job, "selection_reason", "") or " · ".join(reasons))

    return {
        "job_id": _stable_job_id(job),
        "company": str(_get(job, "company", "")),
        "title": title,
        "location": str(_get(job, "location", "")),
        "url": str(
            _get(job, "url", "")
            or _get(job, "application_link", "")
            or _get(job, "apply_url", "")
        ),
        "source": str(_get(job, "source", "")),
        "first_found_date": str(_get(job, "first_found_date", run_date)),
        "last_seen_date": str(run_date),
        "is_active": True,
        "current_rank": rank,
        "bucket": classify_dashboard_bucket(match_score),
        "final_score": match_score,
        "ai_profile_fit": match_score,
        "profile_fit_band": str(_get(job, "profile_fit_band", "")),
        "work_auth_review": _work_auth_review(job),
        "opportunity_type": _opportunity_type(job),
        "reason": reason,
    }


def _request(method: str, url: str, service_key: str, body: Any, prefer: str) -> None:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method=method,
        headers={
            "apikey": service_key,
            "Content-Type": "application/json",
            "Prefer": prefer,
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()


def sync_jobs_to_supabase(ranked_jobs: Iterable[Any], run_date: date | None = None) -> None:
    if os.getenv("CAREERENGINE_DASHBOARD_ENABLED", "").lower() != "true":
        print("Dashboard sync skipped: CAREERENGINE_DASHBOARD_ENABLED is not true.")
        return

    supabase_url = os.environ["SUPABASE_URL"].rstrip("/")
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    run_date = run_date or date.today()

    payloads = [
        _payload_for_job(job, rank=index + 1, run_date=run_date)
        for index, job in enumerate(ranked_jobs)
    ]

    if not payloads:
        print("Dashboard sync skipped: no ranked jobs.")
        return

    table_url = f"{supabase_url}/rest/v1/{DASHBOARD_TABLE}"

    _request(
        "POST",
        f"{table_url}?on_conflict=job_id",
        service_key,
        payloads,
        "resolution=merge-duplicates",
    )

    print(f"Dashboard sync complete: {len(payloads)} jobs synced to Supabase.")

    # Jobs that were not in today's ranking (filled, removed, or no longer
    # eligible) must stop showing as active; otherwise old rows, scored on an
    # older scale, mix with today's. The guard keeps one bad collection run
    # from emptying the board; deactivated rows come back on the next sync
    # that includes them.
    if len(payloads) < MIN_JOBS_TO_DEACTIVATE_STALE:
        print(
            "Stale-row cleanup skipped: only "
            f"{len(payloads)} jobs ranked (minimum {MIN_JOBS_TO_DEACTIVATE_STALE})."
        )
        return

    _request(
        "PATCH",
        f"{table_url}?is_active=eq.true&last_seen_date=lt.{run_date.isoformat()}",
        service_key,
        {"is_active": False},
        "return=minimal",
    )
    print("Dashboard stale-row cleanup complete.")
