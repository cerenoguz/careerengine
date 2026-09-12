"""
Archive dashboard rows for companies that have been removed from
config/companies.yaml. Removing a company from the config only stops
future collection -- it does not retroactively touch jobs already
synced to Supabase from earlier runs. This script marks those rows
inactive/archived so they disappear from every dashboard filter,
without deleting any history.

Usage:
    python scripts/archive_removed_companies.py Company1 Company2 ...
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


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


def archive_companies(companies: list[str]) -> None:
    env = _load_env_local(Path("dashboard/.env.local"))
    supabase_url = env.get("NEXT_PUBLIC_SUPABASE_URL", "").rstrip("/")
    anon_key = env.get("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")

    if not supabase_url or not anon_key:
        raise SystemExit(
            "Missing NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY "
            "in dashboard/.env.local"
        )

    now = datetime.now(timezone.utc).isoformat()
    company_filter = ",".join(urllib.parse.quote(c) for c in companies)
    endpoint = (
        f"{supabase_url}/rest/v1/careerengine_jobs"
        f"?company=in.({company_filter})&is_active=eq.true"
    )

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
        updated_rows = json.loads(response.read().decode("utf-8"))

    print(f"Archived {len(updated_rows)} row(s) for companies: {', '.join(companies)}")
    for row in updated_rows:
        print(f"  - {row.get('company')}: {row.get('title')}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/archive_removed_companies.py Company1 Company2 ...")

    archive_companies(sys.argv[1:])
