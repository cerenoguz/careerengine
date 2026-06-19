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

    return f"{report_date.strftime('%A')} - {report_date.strftime('%B')} {report_date.day}, {report_date.year}"


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

    return labels.get(eligibility_status, eligibility_status.replace("_", " ").title())


def format_opportunity_type(job: Job) -> str:
    if job.is_internship and job.is_new_grad:
        return "Internship / new-grad aligned"

    if job.is_internship:
        return "Internship"

    if job.is_new_grad:
        return "New-grad / early-career aligned"

    return "General early-career review"


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    recommended_jobs_before_deduplication: int,
    new_recommended_jobs: list[Job],
    duplicate_recommendations_removed: int | None = None,
    recommendations_hidden_by_email_cap: int | None = None,
    rank_start: int = 1,
) -> str:
    """
    Build the plain-text daily email report.

    duplicate_recommendations_removed:
        Jobs that passed all filters but were already sent before.

    recommendations_hidden_by_email_cap:
        Jobs that passed all filters and were not duplicates, but were not included
        because the daily email is capped.
    """
    if duplicate_recommendations_removed is None:
        duplicate_recommendations_removed = (
            recommended_jobs_before_deduplication - len(new_recommended_jobs)
        )

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

    lines: list[str] = []

    lines.append(f"Dear {REPORT_RECIPIENT_NAME},")
    lines.append("")
    lines.append(
        "Here is your CareerEngine Daily Opportunity Report for "
        f"{format_report_date()}."
    )
    lines.append("")
    lines.append(
        "CareerEngine reviewed your configured company sources and evaluated "
        "active roles against your background."
    )
    lines.append("")
    lines.append("Recommended opportunities are listed below in ranked order.")
    lines.append("")

    lines.append("Summary:")
    lines.append(f"Companies checked: {len(health_records)}")
    lines.append(f"Successful sources: {successful_sources}")
    lines.append(f"Disabled sources: {disabled_sources}")

    if sources_needing_attention:
        lines.append(f"Sources needing attention: {sources_needing_attention}")

    lines.append(f"Total jobs collected: {total_jobs_collected}")
    lines.append(
        "Recommended jobs before deduplication: "
        f"{recommended_jobs_before_deduplication}"
    )
    lines.append(f"Duplicate recommendations removed: {duplicate_recommendations_removed}")

    if recommendations_hidden_by_email_cap is not None:
        lines.append(
            "Additional qualified opportunities attached: "
            f"{recommendations_hidden_by_email_cap}"
        )

    lines.append(
        f"Top-ranked opportunities in email: {len(new_recommended_jobs)}"
    )
    lines.append("")

    lines.append("Score Guide:")
    lines.append("70+ = excellent match")
    lines.append("55-69 = strong match")
    lines.append("45-54 = relevant / worth checking")
    lines.append("Below 45 = lower-priority match")
    lines.append("")

    lines.append("Description Similarity Guide:")
    lines.append("0.120+ = strong wording overlap")
    lines.append("0.070-0.119 = moderate wording overlap")
    lines.append("0.040-0.069 = low wording overlap")
    lines.append("Below 0.040 = very low wording overlap")
    lines.append("")

    lines.append("Source Health:")
    lines.append(
        f"{successful_sources} successful sources omitted from detailed list."
    )
    lines.append(f"{disabled_sources} disabled sources listed below.")
    lines.append(f"{sources_needing_attention} sources need attention.")
    lines.append("")

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

    lines.append("Best of luck,")
    lines.append("CareerEngine")
    lines.append("")

    lines.append("Top Ranked Opportunities:")
    lines.append("")

    if not new_recommended_jobs:
        lines.append("No ranked opportunities found with the current filters.")
        return "\n".join(lines).rstrip()

    for rank, job in enumerate(new_recommended_jobs, start=rank_start):
        lines.append(f"#{rank}. {job.company} — {job.title}")
        lines.append(f"Location: {job.location}")
        lines.append(f"CareerEngine recommendation: {get_match_strength_label(job.score)}")
        lines.append(f"CareerEngine score: {job.score:.2f}")
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
