import re
from pathlib import Path
from typing import Any

import yaml

from src.collectors.factory import collect_jobs_for_company
from src.models import Job, SourceHealth
from src.ranking.description_similarity import compute_description_similarity
from src.ranking.opt_signals import classify_eligibility
from src.ranking.rule_score import (
    classify_cs_relevance,
    has_unrealistic_seniority,
    is_excluded_role,
    is_internship,
    is_new_grad,
    score_job,
)
from src.reporting.email_report import build_daily_email_report
from src.reporting.email_sender import send_email_report
from src.reporting.report_writer import save_daily_report
from src.storage.database import filter_new_jobs, initialize_database, save_seen_jobs


CONFIG_PATH = Path("config/companies.yaml")
CANDIDATE_PROFILE_PATH = Path("config/candidate_profile.txt")

MAX_RECOMMENDATIONS = 25
DESCRIPTION_SIMILARITY_WEIGHT = 30
SHOW_DESCRIPTION_SIMILARITY_DEBUG = False

RECOMMENDABLE_CS_STATUSES = {
    "strong_cs_relevance",
    "cs_adjacent",
}

US_LOCATION_SIGNALS = [
    "usa",
    "u.s.",
    "united states",
    "remote us",
    "remote, us",
    "remote - us",
    "remote united states",
    "united states, remote",
]

US_STATE_NAMES = [
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
    "district of columbia",
]

US_STATE_ABBREVIATIONS = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
]


def load_company_configs() -> list[dict[str, Any]]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    return data.get("companies", [])


def load_candidate_profile() -> str:
    if not CANDIDATE_PROFILE_PATH.exists():
        raise FileNotFoundError(
            "Missing config/candidate_profile.txt. "
            "Create this file before running CareerEngine."
        )

    with CANDIDATE_PROFILE_PATH.open("r", encoding="utf-8") as file:
        return file.read()


def is_us_opt_location(location: str) -> bool:
    """
    Positive-only location filter for a U.S. OPT-focused job search.

    A job is considered location-compatible only if it contains a U.S. signal,
    a U.S. state name, a U.S. state abbreviation, or a U.S.-remote signal.
    """
    normalized_location = location.lower()

    if any(signal in normalized_location for signal in US_LOCATION_SIGNALS):
        return True

    if any(state in normalized_location for state in US_STATE_NAMES):
        return True

    for abbreviation in US_STATE_ABBREVIATIONS:
        pattern = rf"(^|[^A-Za-z]){abbreviation}([^A-Za-z]|$)"
        if re.search(pattern, location):
            return True

    return False


def is_recommendable_job(job: Job) -> bool:
    """
    Decide whether a job should appear in the final recommendation list.

    A job must:
    - not be in an excluded role category based on title
    - have a positive score
    - not be likely incompatible with OPT/work authorization
    - be clearly or defensibly related to CS/Math based on title + description
    - be U.S.-based or U.S.-remote
    - be realistic for a new-grad / early-career candidate
    """
    # Excluded role category should be title-based.
    # The description may mention sales/marketing/support as partner teams,
    # but that does not make the role itself a sales/marketing/support job.
    if is_excluded_role(job.title, ""):
        return False

    if job.score <= 0:
        return False

    if job.eligibility_status == "likely_incompatible":
        return False

    if not is_us_opt_location(job.location):
        return False

    if has_unrealistic_seniority(job.title, job.description):
        return False

    cs_relevance_status, _ = classify_cs_relevance(job.title, job.description)

    return cs_relevance_status in RECOMMENDABLE_CS_STATUSES


def enrich_jobs(jobs: list[Job], candidate_profile: str) -> None:
    """
    Add classification, rule-based score, and description-only similarity score
    to each collected job.
    """
    for job in jobs:
        job_text = f"{job.title} {job.description}"

        eligibility_status, _positive_signals, _negative_signals = classify_eligibility(job_text)
        job.eligibility_status = eligibility_status

        job.is_internship = is_internship(job.title, job.description)
        job.is_new_grad = is_new_grad(job.title, job.description)

        score, reasons = score_job(
            title=job.title,
            description=job.description,
            eligibility_status=job.eligibility_status,
        )

        description_similarity = compute_description_similarity(
            candidate_profile=candidate_profile,
            job_description=job.description,
        )

        similarity_points = description_similarity * DESCRIPTION_SIMILARITY_WEIGHT

        score += similarity_points
        reasons.append(
            f"Description similarity: {description_similarity:.3f} (+{similarity_points:.1f})"
        )

        job.description_similarity = description_similarity
        job.score = score
        job.why_matched = reasons


def print_source_health(health_records: list[SourceHealth]) -> None:
    print("SOURCE HEALTH")
    print("-------------")

    for health in health_records:
        print(
            f"{health.company} | {health.source} | {health.status} | "
            f"HTTP: {health.http_code} | Jobs: {health.jobs_found} | Reason: {health.reason}"
        )


def print_summary(
    all_jobs: list[Job],
    health_records: list[SourceHealth],
    recommended_jobs: list[Job],
    new_recommended_jobs: list[Job],
) -> None:
    # Count excluded roles by title only.
    # This avoids excluding valid engineering jobs just because their descriptions
    # mention sales, marketing, support, recruiting, etc.
    excluded_count = sum(
        1 for job in all_jobs if is_excluded_role(job.title, "")
    )

    cs_relevant_count = sum(
        1
        for job in all_jobs
        if classify_cs_relevance(job.title, job.description)[0] in RECOMMENDABLE_CS_STATUSES
    )

    us_location_count = sum(
        1 for job in all_jobs if is_us_opt_location(job.location)
    )

    unrealistic_seniority_count = sum(
        1 for job in all_jobs if has_unrealistic_seniority(job.title, job.description)
    )

    duplicate_recommendations_removed = len(recommended_jobs) - len(new_recommended_jobs)

    print()
    print("SUMMARY")
    print("-------")
    print(f"Companies checked: {len(health_records)}")
    print(f"Total jobs collected: {len(all_jobs)}")
    print(f"Excluded role-category jobs removed: {excluded_count}")
    print(f"CS/Math OPT-relevant jobs found: {cs_relevant_count}")
    print(f"U.S./OPT-location jobs found: {us_location_count}")
    print(f"Unrealistic seniority jobs removed: {unrealistic_seniority_count}")
    print(f"Recommended jobs before deduplication: {len(recommended_jobs)}")
    print(f"Duplicate recommendations removed: {duplicate_recommendations_removed}")
    print(f"New recommended jobs: {len(new_recommended_jobs)}")


def print_recommended_jobs(recommended_jobs: list[Job]) -> None:
    print()
    print("TOP NEW RANKED JOBS")
    print("-------------------")

    if not recommended_jobs:
        print("No new recommended jobs found with the current filters.")
        return

    for job in recommended_jobs[:MAX_RECOMMENDATIONS]:
        cs_relevance_status, cs_relevance_reasons = classify_cs_relevance(
            job.title,
            job.description,
        )

        print(f"{job.company} | Score: {job.score:.2f} | {job.title} | {job.location}")
        print(f"Description similarity: {job.description_similarity:.3f}")
        print(f"Eligibility: {job.eligibility_status}")
        print(f"CS/Math relevance: {cs_relevance_status}")
        print(f"Internship: {job.is_internship} | New Grad: {job.is_new_grad}")

        print("Why matched:")
        for reason in job.why_matched[:8]:
            print(f"  - {reason}")

        print("CS/Math relevance notes:")
        for reason in cs_relevance_reasons:
            print(f"  - {reason}")

        print(job.url)
        print()


def print_description_similarity_debug(all_jobs: list[Job]) -> None:
    """
    Optional diagnostic output to confirm description-only similarity is working.
    """
    if not SHOW_DESCRIPTION_SIMILARITY_DEBUG:
        return

    print()
    print("TOP RAW JOBS BY DESCRIPTION SIMILARITY")
    print("--------------------------------------")

    similarity_ranked_jobs = sorted(
        all_jobs,
        key=lambda job: job.description_similarity,
        reverse=True,
    )

    for job in similarity_ranked_jobs[:10]:
        print(
            f"{job.company} | Similarity: {job.description_similarity:.3f} | "
            f"Score: {job.score:.2f} | {job.title} | {job.location}"
        )


def main() -> None:
    initialize_database()

    company_configs = load_company_configs()
    candidate_profile = load_candidate_profile()

    all_jobs: list[Job] = []
    health_records: list[SourceHealth] = []

    for company_config in company_configs:
        jobs, health = collect_jobs_for_company(company_config)

        enrich_jobs(jobs, candidate_profile)

        all_jobs.extend(jobs)
        health_records.append(health)

    ranked_jobs = sorted(all_jobs, key=lambda job: job.score, reverse=True)

    recommended_jobs = [
        job for job in ranked_jobs if is_recommendable_job(job)
    ]

    new_recommended_jobs = filter_new_jobs(recommended_jobs)

    print_source_health(health_records)
    print_summary(
        all_jobs=all_jobs,
        health_records=health_records,
        recommended_jobs=recommended_jobs,
        new_recommended_jobs=new_recommended_jobs,
    )
    print_recommended_jobs(new_recommended_jobs)
    print_description_similarity_debug(all_jobs)

    email_body = build_daily_email_report(
        health_records=health_records,
        total_jobs_collected=len(all_jobs),
        recommended_jobs_before_deduplication=len(recommended_jobs),
        new_recommended_jobs=new_recommended_jobs,
    )

    print()
    print("EMAIL PREVIEW")
    print("-------------")
    print(email_body)

    report_path = save_daily_report(email_body)
    print()
    print(f"Saved email report to: {report_path}")

    send_email_report(
        subject="CareerEngine Daily Job Report",
        body=email_body,
    )

    save_seen_jobs(new_recommended_jobs)


if __name__ == "__main__":
    main()