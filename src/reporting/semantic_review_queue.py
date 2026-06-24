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
    "profile_fit_score",
    "profile_fit_band",
    "lexical_similarity",
    "semantic_similarity",
    "experience_fit",
    "required_years_min",
    "years_requirement_type",
    "hard_no",
    "citizenship_required",
    "permanent_resident_required",
    "clearance_required",
    "export_control_restriction",
    "sponsorship_language",
    "evaluation_reason",
    "evaluation_evidence",
    "profile_fit_reasons",
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
    limit: int = 50,
) -> Path:
    """
    Save a review queue for checking AI profile-fit calibration.

    This is diagnostic only. It does not affect score, ranking, delivery,
    or job discovery state.
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
                    "profile_fit_score": f"{job.profile_fit_score:.1f}",
                    "profile_fit_band": job.profile_fit_band,
                    "lexical_similarity": f"{job.description_similarity:.3f}",
                    "semantic_similarity": f"{job.semantic_similarity:.3f}",
                    "experience_fit": job.experience_fit,
                    "required_years_min": (
                        "" if job.required_years_min is None
                        else str(job.required_years_min)
                    ),
                    "years_requirement_type": job.years_requirement_type,
                    "hard_no": str(job.hard_no).lower(),
                    "citizenship_required": job.citizenship_required,
                    "permanent_resident_required": job.permanent_resident_required,
                    "clearance_required": job.clearance_required,
                    "export_control_restriction": job.export_control_restriction,
                    "sponsorship_language": job.sponsorship_language,
                    "evaluation_reason": job.evaluation_reason,
                    "evaluation_evidence": " | ".join(job.evaluation_evidence[:3]),
                    "profile_fit_reasons": " | ".join(job.profile_fit_reasons),
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
            "profile_fit_top",
            sorted(jobs, key=lambda job: job.profile_fit_score, reverse=True),
            15,
        ),
        (
            "early_career",
            sorted(
                [job for job in jobs if job.is_internship or job.is_new_grad],
                key=lambda job: (job.profile_fit_score, job.score),
                reverse=True,
            ),
            12,
        ),
        (
            "profile_fit_borderline",
            sorted(
                [
                    job for job in jobs
                    if 45 <= job.profile_fit_score < 70
                ],
                key=lambda job: job.profile_fit_score,
                reverse=True,
            ),
            12,
        ),
        (
            "rule_ai_disagreement",
            sorted(
                jobs,
                key=lambda job: (
                    job.profile_fit_score
                    - min(max(job.score, 0.0), 100.0)
                ),
                reverse=True,
            ),
            11,
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
