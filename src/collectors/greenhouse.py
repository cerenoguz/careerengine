from typing import Any

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"


def collect_greenhouse_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    """
    Collect jobs from a public Greenhouse job board API.

    This function does not bypass authentication, CAPTCHA, blocked pages,
    or other access controls. It only reads the public JSON endpoint.
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
                source="greenhouse",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="greenhouse",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="greenhouse",
                status="http_error",
                http_code=response.status_code,
                jobs_found=0,
                reason=f"Unexpected HTTP status code: {response.status_code}",
            )

        data = response.json()
        raw_jobs: list[dict[str, Any]] = data.get("jobs", [])

        jobs: list[Job] = []

        for raw_job in raw_jobs:
            title = raw_job.get("title", "").strip()
            url = raw_job.get("absolute_url", "").strip()
            location = _extract_location(raw_job)
            description = raw_job.get("content", "") or ""
            date_posted = raw_job.get("updated_at")

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
                source="greenhouse",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="greenhouse",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Greenhouse response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="greenhouse",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )

    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="greenhouse",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )

    except ValueError:
        return [], SourceHealth(
            company=company,
            source="greenhouse",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _extract_location(raw_job: dict[str, Any]) -> str:
    location = raw_job.get("location") or {}

    if isinstance(location, dict):
        return location.get("name", "Unknown").strip()

    if isinstance(location, str):
        return location.strip()

    return "Unknown"
