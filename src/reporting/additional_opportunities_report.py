from pathlib import Path

from src.models import Job


def save_additional_opportunities_report(
    *,
    path: Path,
    additional_recommendations: list[Job],
    rank_start: int = 26,
) -> Path:
    """
    Save the active qualified backlog below the email's top-25 cutoff.

    These jobs remain unseen and will be ranked again with newly discovered
    active jobs on the next run.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "CareerEngine Additional Qualified Opportunities",
        "",
        (
            "These jobs are active, fit your profile, and did not make today's "
            "top-25 email body."
        ),
        (
            "They remain eligible and will be ranked again with newly found "
            "jobs in the next report."
        ),
        "Ranks continue from the main email report; this is not a separate queue.",
        "",
        f"Count: {len(additional_recommendations)}",
        "",
    ]

    if not additional_recommendations:
        lines.append("No additional qualified opportunities today.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    for rank, job in enumerate(additional_recommendations, start=rank_start):
        lines.extend(_format_job(rank, job))

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _format_job(rank: int, job: Job) -> list[str]:
    opportunity_type = (
        "Internship"
        if job.is_internship
        else "New-grad / early-career"
        if job.is_new_grad
        else "General early-career review"
    )

    lines = [
        f"#{rank}. {job.company} — {job.title}",
        f"Location: {job.location}",
        f"CareerEngine score: {job.score:.2f}",
        f"Profile wording alignment: {job.description_similarity:.3f}",
        f"Work authorization review: {job.eligibility_status}",
        f"Opportunity type: {opportunity_type}",
        f"Application link: {job.url}",
        "Why CareerEngine selected this role:",
    ]

    for reason in job.why_matched[:8]:
        lines.append(f"- {reason}")

    lines.append("")
    return lines
