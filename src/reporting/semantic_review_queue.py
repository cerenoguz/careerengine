import csv
import re
from pathlib import Path

from src.models import Job


REVIEW_COLUMNS = [
    "job_id",
    "selection_reason",
    "company",
    "title",
    "location",
    "url",
    "opportunity_type",
    "current_score",
    "lexical_similarity",
    "semantic_similarity",
    "description_excerpt",
    "technical_fit",
    "application_priority",
    "reason_codes",
    "notes",
]


def save_semantic_review_queue(
    *,
    path: Path,
    jobs: list[Job],
    status: str,
    limit: int = 40,
) -> Path:
    """
    Save a review queue for gathering personal fit labels.

    The queue is diagnostic only. It does not affect score, ranking, delivery,
    or job deduplication.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()

        if status != "available":
            return path

        for job, selection_reason in _select_review_jobs(jobs, limit=limit):
            writer.writerow(
                {
                    "job_id": job.id,
                    "selection_reason": selection_reason,
                    "company": job.company,
                    "title": job.title,
                    "location": job.location,
                    "url": job.url,
                    "opportunity_type": _opportunity_type(job),
                    "current_score": f"{job.score:.2f}",
                    "lexical_similarity": f"{job.description_similarity:.3f}",
                    "semantic_similarity": f"{job.semantic_similarity:.3f}",
                    "description_excerpt": _description_excerpt(job.description),
                    "technical_fit": "",
                    "application_priority": "",
                    "reason_codes": "",
                    "notes": "",
                }
            )

    return path


def _select_review_jobs(
    jobs: list[Job],
    *,
    limit: int,
) -> list[tuple[Job, str]]:
    if limit <= 0:
        return []

    selected: list[tuple[Job, str]] = []
    selected_ids: set[str] = set()

    buckets = [
        (
            "semantic_top",
            sorted(jobs, key=lambda job: job.semantic_similarity, reverse=True),
            12,
        ),
        (
            "early_career",
            sorted(
                [
                    job
                    for job in jobs
                    if job.is_internship or job.is_new_grad
                ],
                key=lambda job: (job.semantic_similarity, job.score),
                reverse=True,
            ),
            12,
        ),
        (
            "rule_score_top",
            sorted(jobs, key=lambda job: job.score, reverse=True),
            8,
        ),
        (
            "semantic_rule_disagreement",
            sorted(
                jobs,
                key=lambda job: (
                    job.semantic_similarity
                    - min(max(job.score, 0.0), 100.0) / 100.0
                ),
                reverse=True,
            ),
            8,
        ),
    ]

    for selection_reason, candidates, bucket_limit in buckets:
        added_in_bucket = 0

        for job in candidates:
            if job.id in selected_ids:
                continue

            selected.append((job, selection_reason))
            selected_ids.add(job.id)
            added_in_bucket += 1

            if len(selected) >= limit or added_in_bucket >= bucket_limit:
                break

        if len(selected) >= limit:
            return selected

    for job in sorted(
        jobs,
        key=lambda job: (job.semantic_similarity, job.score),
        reverse=True,
    ):
        if job.id in selected_ids:
            continue

        selected.append((job, "remaining_semantic_priority"))
        selected_ids.add(job.id)

        if len(selected) >= limit:
            break

    return selected


def _opportunity_type(job: Job) -> str:
    if job.is_internship:
        return "internship"

    if job.is_new_grad:
        return "new_grad"

    return "general"


def _description_excerpt(description: str, limit: int = 600) -> str:
    normalized = re.sub(r"\s+", " ", description or "").strip()

    if len(normalized) <= limit:
        return normalized

    return normalized[:limit].rstrip() + "..."
