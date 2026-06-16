from typing import Any
from urllib.parse import urlparse

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"


def collect_workable_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    """
    Collect jobs from Workable's public published-jobs endpoint.

    This collector does not use Workable's token-based ATS API, does not log in,
    and does not bypass authentication, CAPTCHA, blocked pages, or access controls.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    api_url = _normalize_workable_source_url(source_url)

    try:
        response = requests.get(api_url, headers=headers, timeout=20)

        if response.status_code == 403:
            return [], SourceHealth(
                company=company,
                source="workable",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="workable",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="workable",
                status="http_error",
                http_code=response.status_code,
                jobs_found=0,
                reason=f"Unexpected HTTP status code: {response.status_code}",
            )

        data = response.json()
        raw_jobs = _extract_raw_jobs(data)

        jobs: list[Job] = []

        for raw_job in raw_jobs:
            title = str(raw_job.get("title", "")).strip()
            url = _extract_url(raw_job, source_url)
            location = _extract_location(raw_job)
            description = _extract_description(raw_job)
            date_posted = _extract_date_posted(raw_job)

            if not title:
                continue

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
                source="workable",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="workable",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Workable response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="workable",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )
    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="workable",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )
    except ValueError:
        return [], SourceHealth(
            company=company,
            source="workable",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _normalize_workable_source_url(source_url: str) -> str:
    """
    Accept either a Workable careers page URL or the public API URL.

    Examples:
    - https://apply.workable.com/huggingface/
    - https://www.workable.com/api/accounts/huggingface?details=true
    """
    source_url = source_url.strip()

    if "/api/accounts/" in source_url:
        return source_url

    parsed = urlparse(source_url)
    path_parts = [part for part in parsed.path.split("/") if part]

    if path_parts:
        account_slug = path_parts[0]
        return f"https://www.workable.com/api/accounts/{account_slug}?details=true"

    return source_url


def _extract_raw_jobs(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        jobs = data.get("jobs") or data.get("results") or []
        if isinstance(jobs, list):
            return [job for job in jobs if isinstance(job, dict)]

    if isinstance(data, list):
        return [job for job in data if isinstance(job, dict)]

    return []


def _extract_location(raw_job: dict[str, Any]) -> str:
    location = raw_job.get("location")

    if isinstance(location, str) and location.strip():
        return location.strip()

    if isinstance(location, dict):
        for key in ("location_str", "name", "city", "country", "region"):
            value = location.get(key)
            if value:
                return str(value).strip()

        parts = [
            str(location.get(key)).strip()
            for key in ("city", "region", "country")
            if location.get(key)
        ]
        if parts:
            return ", ".join(parts)

    locations = raw_job.get("locations")

    if isinstance(locations, list):
        names: list[str] = []
        for item in locations:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = (
                    item.get("location_str")
                    or item.get("name")
                    or item.get("city")
                    or item.get("country")
                )
                if name:
                    names.append(str(name))
        if names:
            return ", ".join(names)

    return "Unknown"


def _extract_description(raw_job: dict[str, Any]) -> str:
    parts: list[str] = []

    for key in (
        "description",
        "full_description",
        "requirements",
        "benefits",
        "employment_type",
        "department",
        "function",
    ):
        value = raw_job.get(key)
        if value:
            parts.append(str(value))

    return "\n".join(parts)


def _extract_url(raw_job: dict[str, Any], source_url: str) -> str:
    for key in ("url", "shortlink", "application_url", "apply_url"):
        value = raw_job.get(key)
        if value:
            return str(value).strip()

    shortcode = raw_job.get("shortcode")
    if shortcode:
        parsed = urlparse(source_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        account_slug = path_parts[0] if path_parts else ""
        if account_slug:
            return f"https://apply.workable.com/{account_slug}/j/{shortcode}/"

    return source_url


def _extract_date_posted(raw_job: dict[str, Any]) -> str | None:
    for key in ("published_on", "published_at", "created_at", "updated_at"):
        value = raw_job.get(key)
        if value:
            return str(value)

    return None
