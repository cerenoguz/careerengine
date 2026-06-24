from datetime import date

from src.models import Job, SourceHealth
from src.ranking.match_interpretation import (
    get_description_similarity_label,
    get_match_strength_label,
)


REPORT_RECIPIENT_NAME = "Ceren"


def format_report_date(report_date: date | None = None) -> str:
    if report_date is None:
        report_date = date.today()

    return (
        f"{report_date.strftime('%A')} - "
        f"{report_date.strftime('%B')} {report_date.day}, {report_date.year}"
    )


def format_subject_date(report_date: date | None = None) -> str:
    if report_date is None:
        report_date = date.today()

    return f"{report_date.month}/{report_date.day}/{report_date.year}"


def format_work_authorization_signal(eligibility_status: str) -> str:
    labels = {
        "likely_compatible": "Likely compatible",
        "unclear": "Needs review",
        "likely_incompatible": "Likely incompatible",
    }
    return labels.get(
        eligibility_status,
        eligibility_status.replace("_", " ").title(),
    )


def format_opportunity_type(job: Job) -> str:
    if job.is_internship and job.is_new_grad:
        return "Internship / new-grad aligned"
    if job.is_internship:
        return "Internship"
    if job.is_new_grad:
        return "New-grad / early-career aligned"
    return "General early-career review"


def format_discovery_label(job: Job) -> str:
    if job.is_new_discovery:
        return "New 🚨"

    if job.first_found_date:
        found_date = date.fromisoformat(job.first_found_date)
        return (
            f"First found: "
            f"{found_date.strftime('%B')} {found_date.day}, {found_date.year}"
        )

    return "First found: unavailable"


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    qualified_jobs: int,
    top_ranked_jobs: list[Job],
    additional_qualified_jobs: int,
    rank_start: int = 1,
) -> str:
    successful_sources = sum(
        1 for record in health_records if record.status == "success"
    )
    disabled_sources = sum(
        1 for record in health_records if record.status == "disabled"
    )
    sources_needing_attention = sum(
        1
        for record in health_records
        if record.status not in {"success", "disabled"}
    )

    disabled_records = [
        record for record in health_records if record.status == "disabled"
    ]
    attention_records = [
        record
        for record in health_records
        if record.status not in {"success", "disabled"}
    ]

    lines = [
        f"Dear {REPORT_RECIPIENT_NAME},",
        "",
        (
            "Here is your CareerEngine Daily Opportunity Report for "
            f"{format_report_date()}."
        ),
        "",
        (
            "CareerEngine reviewed the jobs it successfully observed today, "
            "filtered out clearly unsuitable roles, and ranked the remaining "
            "qualified opportunities for your profile."
        ),
        "",
        "The jobs below are the 25 best current matches CareerEngine found today.",
        "",
        "Summary:",
        f"Companies checked: {len(health_records)}",
        f"Successful sources: {successful_sources}",
        f"Disabled sources: {disabled_sources}",
        f"Total jobs collected: {total_jobs_collected}",
        f"Active qualified opportunities ranked: {qualified_jobs}",
        f"Additional qualified opportunities attached: {additional_qualified_jobs}",
        f"Top-ranked opportunities in email: {len(top_ranked_jobs)}",
        "",
        "Score Guide:",
        "70+ = excellent match",
        "55-69 = strong match",
        "45-54 = relevant / worth checking",
        "Below 45 = lower-priority match",
        "",
        "Description Similarity Guide:",
        "0.120+ = strong wording overlap",
        "0.070-0.119 = moderate wording overlap",
        "0.040-0.069 = low wording overlap",
        "Below 0.040 = very low wording overlap",
        "",
        "Source Health:",
        f"{successful_sources} successful sources omitted from detailed list.",
        f"{disabled_sources} disabled sources listed below.",
        f"{sources_needing_attention} sources need attention.",
        "",
    ]

    if disabled_records:
        lines.append("Disabled Sources:")
        for record in disabled_records:
            lines.append(f"- {record.company}: {record.reason or 'Disabled.'}")
        lines.append("")

    if attention_records:
        lines.append("Sources Needing Attention:")
        for record in attention_records:
            lines.append(
                f"- {record.company}: {record.status} "
                f"(HTTP: {record.http_code}, Jobs: {record.jobs_found})"
            )
            if record.reason:
                lines.append(f"  Reason: {record.reason}")
        lines.append("")

    lines.extend([
        "Best of luck,",
        "CareerEngine",
        "",
        "Top Ranked Opportunities:",
        "",
    ])

    if not top_ranked_jobs:
        lines.append("No ranked opportunities found with the current filters.")
        return "\n".join(lines).rstrip()

    for rank, job in enumerate(top_ranked_jobs, start=rank_start):
        lines.append(
            f"#{rank}. {job.company} — {job.title} "
            f"[{format_discovery_label(job)}]"
        )
        lines.append(f"Location: {job.location}")
        lines.append(
            f"CareerEngine recommendation: {get_match_strength_label(job.score)}"
        )
        lines.append(f"CareerEngine score: {job.score:.2f}")
        lines.append(
            f"AI profile fit: {job.profile_fit_score:.1f} / 100 "
            f"— {job.profile_fit_band.replace('_', ' ').title()}"
        )
        lines.append(
            f"Profile wording alignment: {job.description_similarity:.3f} "
            f"({get_description_similarity_label(job.description_similarity)})"
        )
        lines.append(
            "Work authorization review: "
            f"{format_work_authorization_signal(job.eligibility_status)}"
        )
        lines.append(f"Opportunity type: {format_opportunity_type(job)}")
        lines.append(f"Application link: {job.url}")

        if job.why_matched:
            lines.append("Why CareerEngine selected this role:")
            for reason in job.why_matched[:5]:
                lines.append(f"- {reason}")

        lines.append("")

    return "\n".join(lines).rstrip()
