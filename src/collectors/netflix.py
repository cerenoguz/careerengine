from datetime import datetime, timezone
from typing import Any

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"
DETAIL_URL_TEMPLATE = "https://explore.jobs.netflix.net/api/apply/v2/jobs/{job_id}?domain=netflix.com"
MAX_DETAIL_REQUESTS = 25


def collect_netflix_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    """
    Collect jobs from Netflix's public Eightfold-hosted careers site
    (https://explore.jobs.netflix.net), the same API the site's own
    job search uses. explore.jobs.netflix.net/robots.txt explicitly
    allows /api/apply.

    This function does not bypass authentication, CAPTCHA, blocked pages,
    or other access controls. It only reads the public JSON endpoints.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        response = requests.get(source_url, headers=headers, timeout=20)

        if response.status_code == 403:
            return [], SourceHealth(
                company=company,
                source="netflix",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="netflix",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="netflix",
                status="http_error",
                http_code=response.status_code,
                jobs_found=0,
                reason=f"Unexpected HTTP status code: {response.status_code}",
            )

        data = response.json()
        raw_jobs: list[dict[str, Any]] = data.get("positions", [])

        jobs: list[Job] = []

        for raw_job in raw_jobs[:MAX_DETAIL_REQUESTS]:
            title = str(raw_job.get("name", "")).strip()
            url = str(raw_job.get("canonicalPositionUrl", "")).strip()
            location = _extract_location(raw_job)
            description = _fetch_description(raw_job, headers=headers)
            date_posted = _format_timestamp(raw_job.get("t_create"))

            job_id = create_job_id(
                company=company,
                title=title,
                location=location,
                url=url,
            )

            job = Job(
                id=job_id,
                company=company,
                title=title,
                location=location,
                description=description,
                url=url,
                date_posted=date_posted,
                source="netflix",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="netflix",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Netflix jobs response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="netflix",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )
    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="netflix",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )
    except ValueError:
        return [], SourceHealth(
            company=company,
            source="netflix",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _fetch_description(raw_job: dict[str, Any], *, headers: dict[str, str]) -> str:
    list_description = str(raw_job.get("job_description") or "").strip()

    if list_description:
        return list_description

    job_id = raw_job.get("id")

    if not job_id:
        return ""

    try:
        detail_response = requests.get(
            DETAIL_URL_TEMPLATE.format(job_id=job_id),
            headers=headers,
            timeout=20,
        )

        if detail_response.status_code != 200:
            return ""

        detail_data = detail_response.json()
        return str(detail_data.get("job_description") or "").strip()

    except (requests.RequestException, ValueError):
        return ""


def _extract_location(raw_job: dict[str, Any]) -> str:
    location = raw_job.get("location")

    if isinstance(location, str) and location.strip():
        return location.strip()

    locations = raw_job.get("locations")

    if isinstance(locations, list) and locations:
        return ", ".join(str(item) for item in locations if item)

    return "Unknown"


def _format_timestamp(value: Any) -> str | None:
    if not value:
        return None

    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None
