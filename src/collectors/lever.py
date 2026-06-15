from typing import Any

import requests

from src.models import Job, SourceHealth
from src.utils.hashing import create_job_id


USER_AGENT = "CareerEngineJobMonitor/1.0 (+personal job search project)"


def collect_lever_jobs(company: str, source_url: str) -> tuple[list[Job], SourceHealth]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        response = requests.get(source_url, headers=headers, timeout=20)

        if response.status_code == 403:
            return [], SourceHealth(
                company=company,
                source="lever",
                status="blocked_403",
                http_code=403,
                jobs_found=0,
                reason="Access denied. CareerEngine did not attempt bypass.",
            )

        if response.status_code == 429:
            return [], SourceHealth(
                company=company,
                source="lever",
                status="rate_limited_429",
                http_code=429,
                jobs_found=0,
                reason="Rate limited. CareerEngine did not attempt bypass.",
            )

        if response.status_code != 200:
            return [], SourceHealth(
                company=company,
                source="lever",
                status="http_error",
                http_code=response.status_code,
                jobs_found=0,
                reason=f"Unexpected HTTP status code: {response.status_code}",
            )

        data = response.json()
        raw_jobs = _extract_raw_jobs(data)

        jobs: list[Job] = []

        for raw_job in raw_jobs:
            title = str(raw_job.get("text", "")).strip()
            url = str(raw_job.get("hostedUrl") or raw_job.get("applyUrl") or "").strip()
            location = _extract_location(raw_job)
            description = _extract_description(raw_job)
            date_posted = _extract_date_posted(raw_job)

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
                source="lever",
            )

            jobs.append(job)

        status = "success" if jobs else "no_jobs_found"

        return jobs, SourceHealth(
            company=company,
            source="lever",
            status=status,
            http_code=response.status_code,
            jobs_found=len(jobs),
            reason=None if jobs else "No jobs found in Lever response.",
        )

    except requests.Timeout:
        return [], SourceHealth(
            company=company,
            source="lever",
            status="timeout",
            http_code=None,
            jobs_found=0,
            reason="Request timed out.",
        )
    except requests.RequestException as exc:
        return [], SourceHealth(
            company=company,
            source="lever",
            status="network_error",
            http_code=None,
            jobs_found=0,
            reason=str(exc),
        )
    except ValueError:
        return [], SourceHealth(
            company=company,
            source="lever",
            status="parse_error",
            http_code=response.status_code if "response" in locals() else None,
            jobs_found=0,
            reason="Response was not valid JSON.",
        )


def _extract_raw_jobs(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        postings = data.get("postings") or data.get("jobs") or []
        if isinstance(postings, list):
            return postings

    return []


def _extract_location(raw_job: dict[str, Any]) -> str:
    categories = raw_job.get("categories")

    if isinstance(categories, dict):
        location = categories.get("location")
        if location:
            return str(location).strip()

    location = raw_job.get("location")

    if isinstance(location, str):
        return location.strip()

    if isinstance(location, dict):
        name = location.get("name") or location.get("location")
        if name:
            return str(name).strip()

    return "Unknown"


def _extract_description(raw_job: dict[str, Any]) -> str:
    parts: list[str] = []

    description_plain = raw_job.get("descriptionPlain")
    description = raw_job.get("description")

    if description_plain:
        parts.append(str(description_plain))
    elif description:
        parts.append(str(description))

    lists = raw_job.get("lists")

    if isinstance(lists, list):
        for item in lists:
            if not isinstance(item, dict):
                continue

            heading = item.get("text")
            content = item.get("content")

            if heading:
                parts.append(str(heading))

            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                parts.extend(str(entry) for entry in content)

    additional = raw_job.get("additionalPlain")
    if additional:
        parts.append(str(additional))

    return "\n".join(parts)


def _extract_date_posted(raw_job: dict[str, Any]) -> str | None:
    created_at = raw_job.get("createdAt")

    if created_at is None:
        return None

    return str(created_at)
