"""Score and order the pool of jobs that passed eligibility.

The score reflects fit to the candidate's experience only; level and work
authorization are gates and dashboard indicators, not score components.
"""

import hashlib
import re

from src.models import Job
from src.ranking.match_score import compute_match
from src.ranking.role_fit import assess_role_fit
from src.ranking.semantic_similarity import compute_semantic_similarities
from src.ranking.skills import candidate_skills, job_skill_weights, match_skills
from src.ranking.text_clean import role_text

MAX_MERGED_LOCATIONS = 3


def _normalised_title(title: str) -> str:
    """Lower-cased title without parenthetical tags such as "(NYC)" or "(SF)"."""
    without_tags = re.sub(r"\([^)]*\)", " ", title.lower())
    return re.sub(r"[^a-z0-9]+", " ", without_tags).strip()


def _description_key(description: str) -> str:
    return hashlib.sha1(description[:1500].encode("utf-8")).hexdigest()


def dedupe_jobs(jobs: list[Job]) -> list[Job]:
    """Merge postings that are the same role listed once per location.

    ATS boards often publish one requisition per office. They share a company,
    title (ignoring parenthetical tags like "(NYC)") and description, so they
    would otherwise occupy several adjacent ranks. The first posting is kept
    and the distinct locations are combined.
    """
    kept: dict[tuple[str, str, str], Job] = {}
    locations: dict[tuple[str, str, str], list[str]] = {}

    for job in jobs:
        key = (
            job.company.lower(),
            _normalised_title(job.title),
            _description_key(job.description),
        )
        if key not in kept:
            kept[key] = job
            locations[key] = [job.location]
        elif job.location and job.location not in locations[key]:
            locations[key].append(job.location)

    merged: list[Job] = []
    for key, job in kept.items():
        distinct = [location for location in locations[key] if location]
        if len(distinct) > 1:
            shown = distinct[:MAX_MERGED_LOCATIONS]
            extra = len(distinct) - len(shown)
            job.location = "; ".join(shown) + (f" (+{extra} more)" if extra else "")
        merged.append(job)

    return merged


def rank_jobs(pool: list[Job], candidate_profile: str) -> str:
    """Score every job in the pool and sort it best-first, in place.

    Returns the semantic-scoring status ("available", "disabled",
    "unavailable" or "no_jobs"). When semantic scoring is not available the
    semantic component gets neutral credit rather than skewing the ranking.
    """
    skills_of_candidate = candidate_skills(candidate_profile)

    cosines, status = compute_semantic_similarities(
        candidate_profile,
        [role_text(job.title, job.description) for job in pool],
    )
    semantic_available = status == "available"

    for job, cosine in zip(pool, cosines):
        role = assess_role_fit(job.title)
        skills = match_skills(
            job_skill_weights(job.title, job.description), skills_of_candidate
        )

        result = compute_match(
            role=role,
            skills=skills,
            semantic_cosine=cosine if semantic_available else None,
        )

        job.semantic_similarity = cosine if semantic_available else 0.0
        job.role_family = role.family
        job.match_components = result.components
        job.score = result.score
        job.profile_fit_score = result.score
        job.profile_fit_band = result.band
        job.profile_fit_reasons = result.reasons
        job.why_matched = result.reasons

    pool.sort(key=lambda job: (-job.score, -job.match_components["skills"], job.title))

    return status
