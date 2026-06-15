from typing import Any

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"


def collect_ashby_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        response = requests.get(source_url, headers=headers, timeout=20)

        if response.status_code == 403:
            return [], SourceHealth(
                company=company,
                source="ashby",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="ashby",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="ashby",
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
            url = str(raw_job.get("jobUrl") or raw_job.get("url") or "").strip()
            location = _extract_location(raw_job)
            description = _extract_description(raw_job)
            date_posted = raw_job.get("publishedAt") or raw_job.get("updatedAt")

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
                source="ashby",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="ashby",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Ashby response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="ashby",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )
    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="ashby",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )
    except ValueError:
        return [], SourceHealth(
            company=company,
            source="ashby",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _extract_raw_jobs(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        jobs = data.get("jobs") or data.get("results") or data.get("postings") or []
        if isinstance(jobs, list):
            return jobs

    if isinstance(data, list):
        return data

    return []


def _extract_location(raw_job: dict[str, Any]) -> str:
    location = raw_job.get("location")

    if isinstance(location, str):
        return location.strip()

    if isinstance(location, dict):
        name = location.get("name") or location.get("location") or "Unknown"
        return str(name).strip()

    locations = raw_job.get("locations")

    if isinstance(locations, list) and locations:
        names: list[str] = []

        for item in locations:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("location")
                if name:
                    names.append(str(name))

        if names:
            return ", ".join(names)

    return "Unknown"


def _extract_description(raw_job: dict[str, Any]) -> str:
    description = (
        raw_job.get("descriptionHtml")
        or raw_job.get("description")
        or raw_job.get("content")
        or ""
    )

    return str(description)
