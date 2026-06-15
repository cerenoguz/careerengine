from src.models import Job, SourceHealth


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    recommended_jobs_before_deduplication: int,
    new_recommended_jobs: list[Job],
) -> str:
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
        f"Recommended jobs before deduplication: "
        f"{recommended_jobs_before_deduplication}"
    )
    lines.append(f"Duplicate recommendations removed: {duplicate_recommendations_removed}")
    lines.append(f"New recommended jobs: {len(new_recommended_jobs)}")
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
        lines.append(f"Score: {job.score:.2f}")
        lines.append(f"Description similarity: {job.description_similarity:.3f}")
        lines.append(f"Eligibility: {job.eligibility_status}")
        lines.append(f"Internship: {job.is_internship}")
        lines.append(f"New grad: {job.is_new_grad}")
        lines.append(f"URL: {job.url}")

        if job.why_matched:
            lines.append("Why matched:")
            for reason in job.why_matched[:5]:
                lines.append(f"- {reason}")

    return "\n".join(lines)
