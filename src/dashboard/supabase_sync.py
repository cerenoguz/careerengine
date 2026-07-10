from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import date
from typing import Any, Iterable

from src.dashboard.buckets import classify_dashboard_bucket


DASHBOARD_TABLE = "careerengine_jobs"


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


def _payload_for_job(job: Any, rank: int, run_date: date) -> dict[str, Any]:
    title = str(_get(job, "title", ""))
    description = str(_get(job, "description", "") or _get(job, "full_description", ""))

    ai_profile_fit = _as_float(
        _get(job, "ai_profile_fit", None)
        or _get(job, "profile_fit_score", None)
        or _get(job, "semantic_profile_fit", None)
    )

    work_auth_review = str(
        _get(job, "work_authorization_review", "")
        or _get(job, "work_auth_review", "")
    )

    opportunity_type = str(_get(job, "opportunity_type", ""))
    experience_fit = str(_get(job, "experience_fit", ""))
    reason = str(_get(job, "reason", "") or _get(job, "selection_reason", ""))

    bucket = classify_dashboard_bucket(
        title=title,
        description=description,
        ai_profile_fit=ai_profile_fit,
        work_auth_review=work_auth_review,
        opportunity_type=opportunity_type,
        experience_fit=experience_fit,
        reason=reason,
    )

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
        "bucket": bucket,
        "final_score": _as_float(
            _get(job, "score", None)
            or _get(job, "careerengine_score", None)
        ),
        "ai_profile_fit": ai_profile_fit,
        "profile_fit_band": str(_get(job, "profile_fit_band", "")),
        "work_auth_review": work_auth_review,
        "opportunity_type": opportunity_type,
        "reason": reason,
    }


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

    endpoint = f"{supabase_url}/rest/v1/{DASHBOARD_TABLE}?on_conflict=job_id"

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payloads).encode("utf-8"),
        method="POST",
        headers={
            "apikey": service_key,
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()

    print(f"Dashboard sync complete: {len(payloads)} jobs synced to Supabase.")
