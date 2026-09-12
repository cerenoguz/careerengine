"""
One-off cleanup: archive dashboard rows for internships and jobs
targeting the excluded 2027 grad year, matching the same exclusion
rules now applied in src/main.py's is_recommendable_job(). This only
needs to run once to clear out rows synced before that filter existed;
future runs will simply stop syncing these jobs in the first place.

Reuses rule_score.is_internship() (title-based, word-boundary safe) so
this can't produce the false positives a raw SQL ILIKE '%intern%' would
(e.g. matching "International").

Usage:
    python scripts/archive_internships_and_grad_year.py
"""

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from src.ranking.rule_score import is_internship

EXCLUDED_GRAD_YEAR_PATTERN = re.compile(r"\b2027\b")


def _load_env_local(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()

    return values


def _fetch_active_jobs(base_url: str, anon_key: str) -> list[dict]:
    endpoint = (
        f"{base_url}/rest/v1/careerengine_jobs"
        "?select=job_id,title,company&is_active=eq.true&archived_at=is.null&limit=5000"
    )
    request = urllib.request.Request(
        endpoint,
        headers={"apikey": anon_key, "Authorization": f"Bearer {anon_key}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _archive_job_ids(base_url: str, anon_key: str, job_ids: list[str]) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    id_filter = ",".join(job_ids)
    endpoint = f"{base_url}/rest/v1/careerengine_jobs?job_id=in.({id_filter})"

    body = json.dumps(
        {"is_active": False, "archived_at": now, "updated_at": now}
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=body,
        method="PATCH",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {anon_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    env = _load_env_local(Path("dashboard/.env.local"))
    supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    anon_key = env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        raise SystemExit(
            "Missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY "
            "in dashboard/.env.local"
        )

    jobs = _fetch_active_jobs(supabase_url, anon_key)
    print(f"Fetched {len(jobs)} active job(s) to check.")

    to_archive = [
        job
        for job in jobs
        if is_internship(job["title"], "")
        or EXCLUDED_GRAD_YEAR_PATTERN.search(job["title"])
    ]

    if not to_archive:
        print("Nothing to archive.")
        return

    job_ids = [job["job_id"] for job in to_archive]
    archived = _archive_job_ids(supabase_url, anon_key, job_ids)

    print(f"Archived {len(archived)} row(s):")
    for job in to_archive:
        print(f"  - {job['company']}: {job['title']}")


if __name__ == "__main__":
    main()
