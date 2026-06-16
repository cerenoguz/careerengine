from pathlib import Path

from src.models import Job


def save_unsent_recommendations_report(
    *,
    path: Path,
    duplicate_recommendations: list[Job],
    hidden_by_email_cap_recommendations: list[Job],
) -> Path:
    """
    Save a transparency report for qualified recommendations not included in
    the email body.

    duplicate_recommendations:
        Qualified jobs already sent in a previous report.

    hidden_by_email_cap_recommendations:
        Qualified jobs that were not sent only because the daily email is capped.
        These should remain eligible for future reports.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    lines.append("CareerEngine Unsent Recommendations Report")
    lines.append("")
    lines.append(
        "This file explains which qualified recommendations were not included "
        "in today's email body."
    )
    lines.append("")
    lines.append("Section 1: Already-sent duplicate recommendations")
    lines.append("")
    lines.append(f"Count: {len(duplicate_recommendations)}")
    lines.append("")

    if duplicate_recommendations:
        for index, job in enumerate(duplicate_recommendations, start=1):
            lines.extend(_format_job(index, job))
    else:
        lines.append("No already-sent duplicate recommendations.")
        lines.append("")

    lines.append("Section 2: Qualified recommendations held because of daily email cap")
    lines.append("")
    lines.append(f"Count: {len(hidden_by_email_cap_recommendations)}")
    lines.append("")
    lines.append(
        "These jobs passed the filters and were not duplicates. They were not "
        "included only because the email body is capped. They should remain "
        "eligible for future reports."
    )
    lines.append("")

    if hidden_by_email_cap_recommendations:
        for index, job in enumerate(hidden_by_email_cap_recommendations, start=1):
            lines.extend(_format_job(index, job))
    else:
        lines.append("No qualified recommendations were held by the email cap.")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _format_job(index: int, job: Job) -> list[str]:
    return [
        f"{index}. {job.company} — {job.title}",
        f"Location: {job.location}",
        f"Score: {job.score:.2f}",
        f"Eligibility: {job.eligibility_status}",
        f"Internship: {job.is_internship}",
        f"New grad: {job.is_new_grad}",
        f"URL: {job.url}",
        "",
    ]
