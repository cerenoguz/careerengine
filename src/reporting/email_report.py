from datetime import date

from src.models import Job, SourceHealth


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


def format_discovery_label(job: Job) -> str:
    if getattr(job, "is_new_discovery", False):
        return "🚨 New today"

    first_found_date = getattr(job, "first_found_date", None)
    if first_found_date:
        return f"First found: {first_found_date}"

    return "Previously discovered"


def format_top_role_line(rank: int, job: Job) -> str:
    new_marker = " 🚨 New" if getattr(job, "is_new_discovery", False) else ""
    location = job.location or "Location not listed"

    return f"{rank}. {job.company} — {job.title} — {location}{new_marker}"


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    qualified_jobs: int,
    top_ranked_jobs: list[Job],
    additional_qualified_jobs: int,
    newly_found_jobs: int,
    dashboard_url: str,
    top_roles_to_show: int = 5,
) -> str:
    successful_sources = sum(
        1 for record in health_records if record.status == "success"
    )

    disabled_records = [
        record for record in health_records if record.status == "disabled"
    ]

    dashboard_line = (
        dashboard_url
        if dashboard_url
        else "Dashboard URL not configured. Set CAREERENGINE_DASHBOARD_URL."
    )

    lines = [
        f"Dear {REPORT_RECIPIENT_NAME},",
        "",
        "Your CareerEngine job queue has been updated.",
        "",
        "Open dashboard:",
        dashboard_line,
        "",
        f"Newly found jobs today: {newly_found_jobs}",
        "",
        "Top 5 ranked roles:",
    ]

    if top_ranked_jobs:
        for rank, job in enumerate(top_ranked_jobs[:top_roles_to_show], start=1):
            lines.append(format_top_role_line(rank, job))
    else:
        lines.append("No ranked opportunities found with the current filters.")

    lines.extend(
        [
            "",
            "Summary:",
            f"Successful company sources: {successful_sources} / {len(health_records)}",
            f"Total jobs collected: {total_jobs_collected}",
            f"Active qualified opportunities ranked: {qualified_jobs}",
            "",
            f"Disabled Sources ({len(disabled_records)}):",
        ]
    )

    if disabled_records:
        for record in disabled_records:
            lines.append(f"- {record.company}: {record.reason or 'Disabled.'}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "Best of luck,",
            "CareerEngine",
        ]
    )

    return "\n".join(lines).rstrip()
