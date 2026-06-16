from src.models import Job, SourceHealth
from src.ranking.match_interpretation import get_description_similarity_label, get_match_strength_label


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    recommended_jobs_before_deduplication: int,
    new_recommended_jobs: list[Job],
    duplicate_recommendations_removed: int | None = None,
    recommendations_hidden_by_email_cap: int | None = None,
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

    lines: list[str] = []

    lines.append("CareerEngine Daily Job Report")
    lines.append("=" * 29)
    lines.append("")

    lines.append("Summary")
    lines.append("-------")
    lines.append(f"Companies checked: {len(health_records)}")
    lines.append(f"Total jobs collected: {total_jobs_collected}")
    lines.append(
        "Recommended jobs before deduplication: "
        f"{recommended_jobs_before_deduplication}"
    )
    lines.append(f"Duplicate recommendations removed: {duplicate_recommendations_removed}")

    if recommendations_hidden_by_email_cap is not None:
        lines.append(
            "Recommendations hidden by email cap: "
            f"{recommendations_hidden_by_email_cap}"
        )

    lines.append(f"New recommended jobs: {len(new_recommended_jobs)}")
    lines.append("")
    lines.append("Score Guide")
    lines.append("-----------")
    lines.append("70+ = excellent match")
    lines.append("55-69 = strong match")
    lines.append("45-54 = relevant / worth checking")
    lines.append("Below 45 = lower-priority match")
    lines.append("")
    lines.append("Description Similarity Guide")
    lines.append("----------------------------")
    lines.append("0.120+ = strong wording overlap")
    lines.append("0.070-0.119 = moderate wording overlap")
    lines.append("0.040-0.069 = low wording overlap")
    lines.append("Below 0.040 = very low wording overlap")
    lines.append("")

    lines.append("Source Health")
    lines.append("-------------")

    for health in health_records:
        lines.append(
            f"- {health.company}: {health.status} "
            f"(HTTP: {health.http_code}, Jobs: {health.jobs_found})"
        )

        if health.reason:
            lines.append(f"  Reason: {health.reason}")

    lines.append("")

    lines.append("New Recommended Jobs")
    lines.append("--------------------")

    if not new_recommended_jobs:
        lines.append("No new recommended jobs found with the current filters.")
        return "\n".join(lines)

    for index, job in enumerate(new_recommended_jobs, start=1):
        lines.append("")
        lines.append(f"{index}. {job.company} — {job.title}")
        lines.append(f"Location: {job.location}")
        lines.append(f"Match strength: {get_match_strength_label(job.score)}")
        lines.append(f"Score: {job.score:.2f} points")
        lines.append(
            f"Description similarity: {job.description_similarity:.3f} "
            f"({get_description_similarity_label(job.description_similarity)})"
        )
        lines.append(f"Eligibility: {job.eligibility_status}")
        lines.append(f"Internship: {job.is_internship}")
        lines.append(f"New grad: {job.is_new_grad}")
        lines.append(f"URL: {job.url}")

        if job.why_matched:
            lines.append("Why matched:")
            for reason in job.why_matched[:5]:
                lines.append(f"- {reason}")

    return "\n".join(lines)
