import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from src.collectors.factory import collect_jobs_for_company
from src.models import Job, SourceHealth
from src.ranking.level import LevelAssessment, assess_level
from src.ranking.match_interpretation import get_match_strength_label
from src.ranking.opt_signals import classify_eligibility
from src.ranking.role_fit import assess_role_fit
from src.ranking.pipeline import dedupe_jobs, rank_jobs
from src.ranking.structured_evaluator import evaluate_job_description
from src.ranking.rule_score import (
    classify_cs_relevance,
    is_excluded_role,
    is_internship,
    is_new_grad,
)
from src.ranking.text_clean import clean_description
from src.reporting.email_report import (
    build_daily_email_html,
    build_daily_email_report,
    format_subject_date,
)
from src.reporting.email_sender import send_email_report
from src.reporting.report_writer import save_daily_report
from src.reporting.match_report import save_match_report
from src.reporting.semantic_review_queue import save_semantic_review_queue
from src.reporting.additional_opportunities_report import save_additional_opportunities_report
from src.dashboard.supabase_sync import sync_jobs_to_supabase
from src.storage.database import (
    current_new_york_date,
    get_job_discoveries,
    has_successful_delivery_for_date,
    initialize_database,
    record_run_audit,
    record_successful_delivery,
    save_job_discoveries,
)


CONFIG_PATH = Path("config/companies.yaml")
CANDIDATE_PROFILE_PATH = Path("config/candidate_profile.txt")
ADDITIONAL_OPPORTUNITIES_REPORT_PATH = Path("reports/additional_qualified_opportunities.txt")
MATCH_REPORT_PATH = Path("reports/match_report.txt")
SEMANTIC_REVIEW_QUEUE_PATH = Path("reports/semantic_review_queue.csv")

MAX_RECOMMENDATIONS = 25
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


EXCLUDED_GRAD_YEAR_PATTERN = re.compile(r"\b2027\b")


def targets_excluded_grad_year(title: str) -> bool:
    return bool(EXCLUDED_GRAD_YEAR_PATTERN.search(title))


def level_of(job: Job) -> LevelAssessment:
    """The job's level assessment, computed on demand for hand-built jobs."""
    if job.level_assessment is None:
        job.level_assessment = assess_level(
            job.title, clean_description(job.description)
        )
    return job.level_assessment


def is_recommendable_job(job: Job) -> bool:
    """
    Decide whether a job is eligible to be ranked at all.

    Eligibility is a set of hard gates, applied before any scoring and never
    traded off against it. A job must:
    - not be in an excluded role category based on title
    - not be an internship, and not target the excluded grad year (2027)
    - not carry a hard work-authorization restriction
    - pass the level gate: no senior-level title (a junior-sounding
      description never overrides it) and no requirement of more than
      `MAX_REQUIRED_YEARS` years of experience
    - have an engineering or data job title
    - be U.S.-based or U.S.-remote
    - be clearly or defensibly related to CS/Math based on title + description
    """
    return not get_rejection_reasons(job)


def get_rejection_reasons(job: Job) -> list[str]:
    """Explain why a job did not pass the eligibility gates (empty if it did)."""
    rejection_reasons: list[str] = []

    # Excluded role category should be title-based.
    # The description may mention sales/marketing/support as partner teams,
    # but that does not make the role itself a sales/marketing/support job.
    if is_excluded_role(job.title, ""):
        rejection_reasons.append("excluded role category based on title")

    if job.is_internship or is_internship(job.title, ""):
        rejection_reasons.append("internship roles are excluded")

    if targets_excluded_grad_year(job.title):
        rejection_reasons.append("targets excluded grad year (2027)")

    if job.hard_no:
        rejection_reasons.append(job.evaluation_reason or "explicit hard requirement")

    level = level_of(job)
    if level.gate:
        rejection_reasons.append(f"not entry-level: {level.gate_reason}")

    if assess_role_fit(job.title).score == 0.0:
        rejection_reasons.append("title is not an engineering or data role")

    if not is_us_opt_location(job.location):
        rejection_reasons.append("location is not clearly U.S./OPT-compatible")

    cs_relevance_status, _ = classify_cs_relevance(job.title, job.description)
    if cs_relevance_status not in RECOMMENDABLE_CS_STATUSES:
        rejection_reasons.append(f"not CS/Math relevant enough: {cs_relevance_status}")

    return rejection_reasons


def print_rejection_debug(all_jobs: list[Job]) -> None:
    """Print a sample of rejected jobs and why, so the gates can be tuned safely."""
    if not SHOW_REJECTION_DEBUG:
        return

    print()
    print("REJECTED JOBS DEBUG")
    print("-------------------")

    rejected = [(job, get_rejection_reasons(job)) for job in all_jobs]
    rejected = [(job, reasons) for job, reasons in rejected if reasons]

    if not rejected:
        print("No rejected jobs found.")
        return

    for job, reasons in rejected[:15]:
        print(f"{job.company} | {job.title} | {job.location}")
        print("Rejected because:")
        for reason in reasons:
            print(f"  - {reason}")
        print(job.url)
        print()


def enrich_jobs(jobs: list[Job]) -> None:
    """
    Clean each description and attach the signals the eligibility gates and the
    match score are built from: level, work authorization, sponsorship language
    and internship / new-grad flags.
    """
    for job in jobs:
        # Greenhouse and others deliver HTML-escaped markup; every downstream
        # reader (regexes, embeddings, reports) wants plain text.
        job.description = clean_description(job.description)
        job_text = f"{job.title} {job.description}"

        evaluation = evaluate_job_description(job.title, job.description)
        level = assess_level(job.title, job.description)

        job.level_assessment = level
        job.level = level.level
        job.level_gate_reason = level.gate_reason
        job.required_years_min = level.years_required
        job.years_requirement_type = "required" if level.years_required is not None else "unclear"
        job.experience_fit = (
            "unlikely" if level.gate
            else "strong" if level.level == "entry"
            else "possible" if level.level in {"junior_mid", "mid"}
            else "unclear"
        )
        job.evaluation_reason = level.summary
        job.evaluation_evidence = [*level.entry_signals, *level.senior_signals]

        job.hard_no = evaluation.hard_no
        job.new_grad_signal = evaluation.new_grad_signal
        job.internship_signal = evaluation.internship_signal
        job.citizenship_required = evaluation.citizenship_required
        job.permanent_resident_required = evaluation.permanent_resident_required
        job.clearance_required = evaluation.clearance_required
        job.export_control_restriction = evaluation.export_control_restriction
        job.sponsorship_language = evaluation.sponsorship_language
        if evaluation.hard_no:
            job.evaluation_reason = evaluation.reason
            job.evaluation_evidence = evaluation.evidence

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

        job.is_internship = (
            is_internship(job.title, job.description)
            or evaluation.internship_signal == "yes"
        )
        job.is_new_grad = (
            is_new_grad(job.title, job.description)
            or evaluation.new_grad_signal == "yes"
        )


def print_source_health(health_records: list[SourceHealth]) -> None:
    print("SOURCE HEALTH")
    print("-------------")

    for health in health_records:
        print(
            f"{health.company} | {health.source} | {health.status} | "
            f"HTTP: {health.http_code} | Jobs: {health.jobs_found} | Reason: {health.reason}"
        )


def print_recommended_jobs(recommended_jobs: list[Job]) -> None:
    print()
    print("TOP RANKED JOBS")
    print("-------------------")

    if not recommended_jobs:
        print("No new recommended jobs found with the current filters.")
        return

    for job in recommended_jobs[:MAX_RECOMMENDATIONS]:
        print(
            f"{job.company} | Match: {job.score:.0f}/100 "
            f"({get_match_strength_label(job.score)}) | "
            f"{job.title} | {job.location}"
        )
        components = " | ".join(
            f"{name} {value:.2f}" for name, value in job.match_components.items()
        )
        print(f"Components: {components}")
        print(f"Level: {job.level} | Eligibility: {job.eligibility_status}")

        print("Why matched:")
        for reason in job.why_matched[:8]:
            print(f"  - {reason}")

        print(job.url)
        print()


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
        enrich_jobs(jobs)
        all_jobs.extend(jobs)
        health_records.append(health)

    eligible_jobs = [job for job in all_jobs if is_recommendable_job(job)]
    recommended_jobs = dedupe_jobs(eligible_jobs)
    semantic_status = rank_jobs(recommended_jobs, candidate_profile)

    match_report_path = save_match_report(
        path=MATCH_REPORT_PATH,
        jobs=recommended_jobs,
        semantic_status=semantic_status,
    )
    print(f"Semantic scoring status: {semantic_status}")
    print(f"Saved match report to: {match_report_path}")

    semantic_review_queue_path = save_semantic_review_queue(
        path=SEMANTIC_REVIEW_QUEUE_PATH,
        jobs=recommended_jobs,
        status=semantic_status,
    )
    print(f"Saved semantic review queue to: {semantic_review_queue_path}")

    # Read-only here: discoveries are only persisted after the delivery step
    # below, so a failed send doesn't mark today's jobs as already seen.
    discovery_info = get_job_discoveries(recommended_jobs)

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
    newly_discovered_jobs = [job for job in recommended_jobs if job.is_new_discovery]

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
    print_rejection_debug(all_jobs)

    email_kwargs = dict(
        health_records=health_records,
        total_jobs_collected=len(all_jobs),
        qualified_jobs=len(recommended_jobs),
        newly_discovered_jobs=newly_discovered_jobs,
        additional_qualified_jobs=len(additional_ranked_jobs),
        dashboard_url=os.getenv("CAREERENGINE_DASHBOARD_URL", ""),
    )
    email_body = build_daily_email_report(**email_kwargs)
    email_html = build_daily_email_html(**email_kwargs)

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
            html_body=email_html,
        )

        if email_sent:
            record_successful_delivery(
                delivery_date=delivery_date,
                run_id=run_id,
                environment=environment,
            )
        else:
            print("Email was not sent; no daily delivery record was created.")

    # Reached only if the send step didn't raise (an SMTP failure propagates
    # and skips this), so jobs from a failed delivery stay "new" for the next
    # run. Disabled-email and already-delivered-today runs still persist.
    save_job_discoveries(recommended_jobs)

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
