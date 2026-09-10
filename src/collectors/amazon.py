from typing import Any

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"
JOB_BASE_URL = "https://www.amazon.jobs"


def collect_amazon_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    """
    Collect jobs from Amazon's public jobs search JSON endpoint
    (https://www.amazon.jobs/en/search.json), the same API the
    amazon.jobs search page uses. Not blocked by amazon.jobs/robots.txt.

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
                source="amazon",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="amazon",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="amazon",
                status="http_error",
                http_code=response.status_code,
                jobs_found=0,
                reason=f"Unexpected HTTP status code: {response.status_code}",
            )

        data = response.json()
        raw_jobs: list[dict[str, Any]] = data.get("jobs", [])

        jobs: list[Job] = []

        for raw_job in raw_jobs:
            title = str(raw_job.get("title", "")).strip()
            url = _extract_url(raw_job)
            location = _extract_location(raw_job)
            description = _extract_description(raw_job)
            date_posted = raw_job.get("posted_date")

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
                source="amazon",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="amazon",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Amazon jobs response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="amazon",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )
    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="amazon",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )
    except ValueError:
        return [], SourceHealth(
            company=company,
            source="amazon",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _extract_url(raw_job: dict[str, Any]) -> str:
    job_path = str(raw_job.get("job_path", "")).strip()

    if job_path:
        return f"{JOB_BASE_URL}{job_path}"

    return ""


def _extract_location(raw_job: dict[str, Any]) -> str:
    location = raw_job.get("normalized_location") or raw_job.get("location")

    if isinstance(location, str) and location.strip():
        return location.strip()

    return "Unknown"


def _extract_description(raw_job: dict[str, Any]) -> str:
    parts = [
        raw_job.get("description"),
        raw_job.get("basic_qualifications"),
        raw_job.get("preferred_qualifications"),
    ]

    return "\n\n".join(str(part) for part in parts if part)
