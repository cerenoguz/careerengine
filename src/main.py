import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.collectors.factory import collect_jobs_for_company
from src.models import Job, SourceHealth
from src.ranking.description_similarity import compute_description_similarity
from src.ranking.semantic_similarity import compute_semantic_similarities
from src.ranking.profile_fit import (
    calculate_profile_fit_score,
    profile_fit_ranking_adjustment,
)
from src.ranking.match_interpretation import get_description_similarity_label, get_match_strength_label
from src.ranking.opt_signals import classify_eligibility
from src.ranking.structured_evaluator import evaluate_job_description
from src.ranking.rule_score import (
    classify_cs_relevance,
    is_excluded_role,
    has_senior_title_blocker,
    is_internship,
    is_new_grad,
    score_job,
)
from src.reporting.email_report import build_daily_email_report, format_subject_date
from src.reporting.email_sender import send_email_report
from src.reporting.report_writer import save_daily_report
from src.reporting.semantic_shadow_report import save_semantic_shadow_report
from src.reporting.semantic_review_queue import save_semantic_review_queue
from src.reporting.additional_opportunities_report import save_additional_opportunities_report
from src.dashboard.supabase_sync import sync_jobs_to_supabase
from src.storage.database import (
    current_new_york_date,
    has_successful_delivery_for_date,
    initialize_database,
    record_job_discoveries,
    record_run_audit,
    record_successful_delivery,
)


CONFIG_PATH = Path("config/companies.yaml")
CANDIDATE_PROFILE_PATH = Path("config/candidate_profile.txt")
ADDITIONAL_OPPORTUNITIES_REPORT_PATH = Path("reports/additional_qualified_opportunities.txt")
SEMANTIC_SHADOW_REPORT_PATH = Path("reports/semantic_shadow_report.txt")
SEMANTIC_REVIEW_QUEUE_PATH = Path("reports/semantic_review_queue.csv")

MAX_RECOMMENDATIONS = 25
DESCRIPTION_SIMILARITY_WEIGHT = 30
SHOW_DESCRIPTION_SIMILARITY_DEBUG = False
SHOW_REJECTION_DEBUG = False

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

US_CITY_SIGNALS = [
    "san francisco",
    "new york",
    "new york city",
    "nyc",
    "boston",
    "seattle",
    "austin",
    "chicago",
    "los angeles",
    "san diego",
    "san jose",
    "mountain view",
    "palo alto",
    "menlo park",
    "redwood city",
    "sunnyvale",
    "santa clara",
    "cupertino",
    "berkeley",
    "oakland",
    "washington dc",
    "washington, dc",
    "district of columbia",
    "atlanta",
    "miami",
    "dallas",
    "houston",
    "denver",
    "portland",
    "philadelphia",
    "phoenix",
    "salt lake city",
    "raleigh",
    "durham",
    "charlotte",
    "nashville",
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
    a U.S. state name, a U.S. city name, a U.S. state abbreviation,
    or a U.S.-remote signal.
    """
    normalized_location = location.lower().strip()
    normalized_location = normalized_location.replace("-", " ")
    normalized_location = normalized_location.replace(",", " ")
    normalized_location = re.sub(r"\s+", " ", normalized_location)

    if any(signal in normalized_location for signal in US_LOCATION_SIGNALS):
        return True

    # Some ATS locations use country/region prefixes that look like U.S. state
    # abbreviations. Examples:
    # - DE-Berlin should not match Delaware.
    # - CA-Ontario-Toronto should not match California.
    # - IN-Pune should not match Indiana.
    non_us_country_prefix_patterns = [
        r"^de[-_]",
        r"^ca[-_]",
        r"^in[-_]",
        r"^uk[-_]",
        r"^gb[-_]",
        r"^ie[-_]",
        r"^nl[-_]",
        r"^fr[-_]",
        r"^es[-_]",
        r"^br[-_]",
        r"^sg[-_]",
        r"^au[-_]",
        r"^jp[-_]",
        r"^kr[-_]",
    ]

    if any(
        re.search(pattern, location.strip(), flags=re.IGNORECASE)
        for pattern in non_us_country_prefix_patterns
    ):
        return False

    if any(state in normalized_location for state in US_STATE_NAMES):
        return True

    if any(city in normalized_location for city in US_CITY_SIGNALS):
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

    if job.hard_no:
        return False

    if not is_us_opt_location(job.location):
        return False

    cs_relevance_status, _ = classify_cs_relevance(job.title, job.description)

    return cs_relevance_status in RECOMMENDABLE_CS_STATUSES

def get_rejection_reasons(job: Job) -> list[str]:
    """
    Explain why a job did not pass the final recommendation filter.
    This is diagnostic only; it does not change ranking or filtering.
    """
    rejection_reasons: list[str] = []

    if is_excluded_role(job.title, ""):
        rejection_reasons.append("excluded role category based on title")

    if job.score <= 0:
        rejection_reasons.append("score is not positive")

    if job.hard_no:
        rejection_reasons.append(job.evaluation_reason or "explicit hard requirement")

    if not is_us_opt_location(job.location):
        rejection_reasons.append("location is not clearly U.S./OPT-compatible")

    cs_relevance_status, _ = classify_cs_relevance(job.title, job.description)
    if cs_relevance_status not in RECOMMENDABLE_CS_STATUSES:
        rejection_reasons.append(f"not CS/Math relevant enough: {cs_relevance_status}")

    return rejection_reasons


def print_rejection_debug(ranked_jobs: list[Job]) -> None:
    """
    Print the highest-scoring rejected jobs so we can tune filters safely.
    """
    if not SHOW_REJECTION_DEBUG:
        return

    rejected_jobs = [
        job for job in ranked_jobs
        if job.score > 0 and not is_recommendable_job(job)
    ]

    print()
    print("TOP REJECTED JOBS DEBUG")
    print("-----------------------")

    if not rejected_jobs:
        print("No high-scoring rejected jobs found.")
        return

    for job in rejected_jobs[:15]:
        rejection_reasons = get_rejection_reasons(job)

        print(
            f"{job.company} | Match: {get_match_strength_label(job.score)} | "
            f"Score: {job.score:.2f} | {job.title} | {job.location}"
        )
        print(f"Eligibility: {job.eligibility_status}")
        print(
            f"Description similarity: {job.description_similarity:.3f} "
            f"({get_description_similarity_label(job.description_similarity)})"
        )
        print("Rejected because:")

        for reason in rejection_reasons:
            print(f"  - {reason}")

        print(job.url)
        print()

def enrich_jobs(jobs: list[Job], candidate_profile: str) -> None:
    """
    Add classification, rule-based score, and description-only similarity score
    to each collected job.
    """
    for job in jobs:
        job_text = f"{job.title} {job.description}"
        evaluation = evaluate_job_description(job.title, job.description)

        job.hard_no = evaluation.hard_no
        job.required_years_min = evaluation.required_years_min
        job.required_years_max = evaluation.required_years_max
        job.years_requirement_type = evaluation.years_requirement_type
        job.new_grad_signal = evaluation.new_grad_signal
        job.internship_signal = evaluation.internship_signal
        job.citizenship_required = evaluation.citizenship_required
        job.permanent_resident_required = evaluation.permanent_resident_required
        job.clearance_required = evaluation.clearance_required
        job.export_control_restriction = evaluation.export_control_restriction
        job.sponsorship_language = evaluation.sponsorship_language
        job.experience_fit = evaluation.experience_fit
        job.evaluation_reason = evaluation.reason
        job.evaluation_evidence = evaluation.evidence
        job.evaluation_confidence = evaluation.confidence

        legacy_status, _positive_signals, _negative_signals = classify_eligibility(job_text)

        if evaluation.hard_no:
            job.eligibility_status = "likely_incompatible"
        elif evaluation.sponsorship_language == "available":
            job.eligibility_status = "likely_compatible"
        elif (
            legacy_status == "likely_compatible"
            and evaluation.sponsorship_language != "unavailable"
        ):
            job.eligibility_status = "likely_compatible"
        else:
            job.eligibility_status = "unclear"

        title_is_internship = is_internship(job.title, job.description)
        title_is_new_grad = is_new_grad(job.title, job.description)

        job.is_internship = (
            title_is_internship
            or evaluation.internship_signal == "yes"
        )
        job.is_new_grad = (
            title_is_new_grad
            or evaluation.new_grad_signal == "yes"
        )

        score, reasons = score_job(
            title=job.title,
            description=job.description,
            eligibility_status=job.eligibility_status,
        )

        if evaluation.internship_signal == "yes" and not title_is_internship:
            score += 20
            reasons.append("Description confirms internship/co-op eligibility (+20)")

        if evaluation.new_grad_signal == "yes" and not title_is_new_grad:
            score += 22
            reasons.append("Description confirms new-grad/early-career eligibility (+22)")

        if evaluation.required_years_min in {3, 4}:
            score -= 15
            reasons.append("3–4 years required: controlled experience-gap demotion (-15)")

        if evaluation.sponsorship_language == "unavailable":
            reasons.append("Sponsorship unavailable; not treated as an OPT hard exclusion")

        reasons.append(
            f"Experience evaluation: {evaluation.experience_fit} — "
            f"{evaluation.reason}"
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
    deduplicated_recommended_jobs: list[Job],
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

    duplicate_recommendations_removed = (
        len(recommended_jobs) - len(deduplicated_recommended_jobs)
    )

    recommendations_hidden_by_email_cap = (
        len(deduplicated_recommended_jobs) - len(new_recommended_jobs)
    )

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
    print(f"Additional qualified opportunities attached: {recommendations_hidden_by_email_cap}")
    print(f"New recommended jobs: {len(new_recommended_jobs)}")

def print_recommended_jobs(recommended_jobs: list[Job]) -> None:
    print()
    print("TOP RANKED JOBS")
    print("-------------------")

    if not recommended_jobs:
        print("No new recommended jobs found with the current filters.")
        return

    for job in recommended_jobs[:MAX_RECOMMENDATIONS]:
        cs_relevance_status, cs_relevance_reasons = classify_cs_relevance(
            job.title,
            job.description,
        )

        print(
            f"{job.company} | Match: {get_match_strength_label(job.score)} | "
            f"Score: {job.score:.2f} | {job.title} | {job.location}"
        )
        print(
            f"Description similarity: {job.description_similarity:.3f} "
            f"({get_description_similarity_label(job.description_similarity)})"
        )
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

def build_duplicate_jobs_report(duplicate_jobs: list[Job]) -> str:
    """
    Build a text report of jobs that passed all filters but were already seen.
    """
    lines = [
        "CareerEngine Duplicate Recommendations",
        "======================================",
        "",
        f"Duplicate jobs found: {len(duplicate_jobs)}",
        "",
    ]

    if not duplicate_jobs:
        lines.append("No duplicate recommended jobs found.")
        return "\n".join(lines)

    for index, job in enumerate(duplicate_jobs, start=1):
        lines.extend(
            [
                f"{index}. {job.company} — {job.title}",
                f"Location: {job.location}",
                f"Score: {job.score:.2f}",
                f"Description similarity: {job.description_similarity:.3f}",
                f"Eligibility: {job.eligibility_status}",
                f"Internship: {job.is_internship}",
                f"New grad: {job.is_new_grad}",
                f"URL: {job.url}",
                "Why matched:",
            ]
        )

        for reason in job.why_matched[:8]:
            lines.append(f"- {reason}")

        lines.append("")

    return "\n".join(lines)



def get_run_context() -> tuple[str, str]:
    if os.getenv("GITHUB_ACTIONS", "").lower() == "true":
        return (
            os.getenv("GITHUB_RUN_ID", "github-unknown"),
            "github_actions",
        )

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"local-{timestamp}", "local"



def main() -> None:
    initialize_database()

    run_id, environment = get_run_context()
    delivery_date = current_new_york_date()

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
        job for job in ranked_jobs
        if is_recommendable_job(job)
    ]

    semantic_scores, semantic_shadow_status = compute_semantic_similarities(
        candidate_profile,
        [job.description or "" for job in recommended_jobs],
    )

    for job, semantic_score in zip(recommended_jobs, semantic_scores):
        job.semantic_similarity = semantic_score

        cs_relevance_status, _ = classify_cs_relevance(
            job.title,
            job.description,
        )

        profile_fit = calculate_profile_fit_score(
            semantic_similarity=semantic_score,
            description_similarity=job.description_similarity,
            cs_relevance_status=cs_relevance_status,
            is_internship=job.is_internship,
            is_new_grad=job.is_new_grad,
            required_years_min=job.required_years_min,
            required_years_max=job.required_years_max,
            years_requirement_type=job.years_requirement_type,
            senior_title_signal=has_senior_title_blocker(job.title),
            title_description_conflict=(
                "Junior-friendly description overrides senior-looking title"
                in job.evaluation_reason
                or (
                    job.is_new_grad
                    and any(
                        marker in job.title.lower()
                        for marker in ["senior", "staff", "principal", "lead", "engineer ii", "(l2)", " l2"]
                    )
                )
            ),
        )

        job.profile_fit_score = profile_fit.score
        job.profile_fit_band = profile_fit.band
        job.profile_fit_reasons = profile_fit.reasons

        if semantic_shadow_status == "available":
            ranking_adjustment, ranking_reason = profile_fit_ranking_adjustment(
                job.profile_fit_score
            )
            job.score += ranking_adjustment
            job.why_matched.append(ranking_reason)

    if semantic_shadow_status == "available":
        recommended_jobs.sort(
            key=lambda job: (job.score, job.profile_fit_score),
            reverse=True,
        )

    semantic_shadow_report_path = save_semantic_shadow_report(
        path=SEMANTIC_SHADOW_REPORT_PATH,
        jobs=recommended_jobs,
        status=semantic_shadow_status,
    )
    print(f"Semantic shadow status: {semantic_shadow_status}")
    print(f"Saved semantic shadow report to: {semantic_shadow_report_path}")

    semantic_review_queue_path = save_semantic_review_queue(
        path=SEMANTIC_REVIEW_QUEUE_PATH,
        jobs=recommended_jobs,
        status=semantic_shadow_status,
    )
    print(f"Saved semantic review queue to: {semantic_review_queue_path}")

    discovery_info = record_job_discoveries(recommended_jobs)

    for job in recommended_jobs:
        first_found_date, is_new_discovery = discovery_info[job.id]
        job.first_found_date = first_found_date
        job.is_new_discovery = is_new_discovery

    try:
        sync_jobs_to_supabase(recommended_jobs, run_date=delivery_date)
    except Exception as exc:
        print(f"Dashboard sync failed: {exc}")

    top_ranked_jobs = recommended_jobs[:MAX_RECOMMENDATIONS]
    additional_ranked_jobs = recommended_jobs[MAX_RECOMMENDATIONS:]

    print_source_health(health_records)
    print()
    print("SUMMARY")
    print("-------")
    print(f"Companies checked: {len(health_records)}")
    print(f"Total jobs collected: {len(all_jobs)}")
    print(f"Active qualified opportunities ranked: {len(recommended_jobs)}")
    print(f"Top-ranked opportunities in email: {len(top_ranked_jobs)}")
    print(
        "Additional qualified opportunities attached: "
        f"{len(additional_ranked_jobs)}"
    )
    print(
        "New discoveries today: "
        f"{sum(job.is_new_discovery for job in recommended_jobs)}"
    )

    print_recommended_jobs(top_ranked_jobs)
    print_description_similarity_debug(all_jobs)
    print_rejection_debug(ranked_jobs)

    email_body = build_daily_email_report(
        health_records=health_records,
        total_jobs_collected=len(all_jobs),
        qualified_jobs=len(recommended_jobs),
        top_ranked_jobs=top_ranked_jobs,
        additional_qualified_jobs=len(additional_ranked_jobs),
        newly_found_jobs=sum(job.is_new_discovery for job in recommended_jobs),
        dashboard_url=os.getenv("CAREERENGINE_DASHBOARD_URL", ""),
    )

    print()
    print("EMAIL PREVIEW")
    print("-------------")
    print(email_body)

    report_path = save_daily_report(email_body)
    print()
    print(f"Saved email report to: {report_path}")

    additional_opportunities_report_path = save_additional_opportunities_report(
        path=ADDITIONAL_OPPORTUNITIES_REPORT_PATH,
        additional_recommendations=additional_ranked_jobs,
        rank_start=len(top_ranked_jobs) + 1,
    )

    already_delivered_today = has_successful_delivery_for_date(delivery_date)
    email_sent = False
    skipped_due_to_daily_delivery = False

    if already_delivered_today:
        skipped_due_to_daily_delivery = True
        print(
            "Email sending skipped because CareerEngine already delivered "
            f"a report for {delivery_date} (America/New_York)."
        )
    else:
        email_sent = send_email_report(
            subject=f"CareerEngine Job Reminder: {format_subject_date()}",
            body=email_body,
            attachment_paths=[additional_opportunities_report_path],
        )

        if email_sent:
            record_successful_delivery(
                delivery_date=delivery_date,
                run_id=run_id,
                environment=environment,
            )
        else:
            print("Email was not sent; no daily delivery record was created.")

    record_run_audit(
        run_id=run_id,
        environment=environment,
        delivery_date=delivery_date,
        seen_jobs_before=0,
        qualified_jobs=len(recommended_jobs),
        duplicate_jobs=0,
        pending_jobs_active=0,
        held_by_email_cap=len(additional_ranked_jobs),
        selected_for_email=len(top_ranked_jobs),
        email_sent=email_sent,
        skipped_due_to_daily_delivery=skipped_due_to_daily_delivery,
        seen_jobs_after=0,
    )

    print()
    print("DELIVERY AUDIT")
    print("--------------")
    print(f"Run ID: {run_id}")
    print(f"Environment: {environment}")
    print(f"Delivery date (New York): {delivery_date}")
    print(f"Jobs ranked today: {len(recommended_jobs)}")
    print(f"Jobs in email body: {len(top_ranked_jobs)}")
    print(f"Jobs in attachment: {len(additional_ranked_jobs)}")
    print(f"Email sent: {email_sent}")
    print(f"Skipped due to prior daily delivery: {skipped_due_to_daily_delivery}")


if __name__ == "__main__":
    main()
