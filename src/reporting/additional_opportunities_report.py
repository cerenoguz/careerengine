from datetime import date
from pathlib import Path

from src.models import Job


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


def save_additional_opportunities_report(
    *,
    path: Path,
    additional_recommendations: list[Job],
    rank_start: int = 26,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "CareerEngine Additional Qualified Opportunities",
        "",
        (
            "These are active qualified opportunities that did not make today's "
            "top-25 email body."
        ),
        (
            "They are ranked below the email list using the same current "
            "CareerEngine scoring system."
        ),
        "Ranks continue from the main email report.",
        "",
        f"Count: {len(additional_recommendations)}",
        "",
    ]

    if not additional_recommendations:
        lines.append("No additional qualified opportunities today.")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    for rank, job in enumerate(additional_recommendations, start=rank_start):
        lines.extend([
            f"#{rank}. {job.company} — {job.title} [{format_discovery_label(job)}]",
            f"Location: {job.location}",
            f"CareerEngine score: {job.score:.2f}",
            (
                f"AI profile fit: {job.profile_fit_score:.1f} / 100 "
                f"— {job.profile_fit_band.replace('_', ' ').title()}"
            ),
            f"Profile wording alignment: {job.description_similarity:.3f}",
            f"Work authorization review: {job.eligibility_status}",
            f"Application link: {job.url}",
            "Why CareerEngine selected this role:",
        ])

        for reason in job.why_matched[:8]:
            lines.append(f"- {reason}")

        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
