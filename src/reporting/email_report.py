import html
import os
from datetime import date

from src.models import Job, SourceHealth
from src.ranking.match_score import BANDS, band_for

_BG_PAGE = "#EFEFF2"
_BG_CARD = "#FFFFFF"
_TEXT_PRIMARY = "#0B0B0E"
_TEXT_SECONDARY = "#6B6B76"
_TEXT_TERTIARY = "#9A9AA3"
_BORDER = "#E6E6EA"
_ACCENT = "#F7C7DB"
_ACCENT_TINT = "#FCEEF3"
_ACCENT_INK = "#C24B82"
_BUTTON_TEXT = "#4A1A32"
_TILE_BG = "#FAFAFB"
_FONT_STACK = "'Segoe UI', Helvetica, Arial, sans-serif"
_MONO_STACK = "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace"

EMAIL_JOB_LIST_LIMIT = 5
MAX_HIGHLIGHTS = 3

# Reasons that restate the title or say nothing; the card already shows the title.
_UNINFORMATIVE_REASONS = ("Role:", "Few technologies named", "Skill gaps")

# (background, text) per match band, drawn from the email's existing palette.
_BAND_COLORS = {
    "excellent": (_ACCENT, _BUTTON_TEXT),
    "strong": (_ACCENT_TINT, _ACCENT_INK),
    "good": ("#F2F2F4", _TEXT_SECONDARY),
    "fair": ("#F2F2F4", _TEXT_TERTIARY),
}

def _recipient_name() -> str:
    return os.getenv("CAREERENGINE_RECIPIENT_NAME", "there")


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
        return "New today"

    first_found_date = getattr(job, "first_found_date", None)
    if first_found_date:
        return f"First found: {first_found_date}"

    return "Previously discovered"


def format_top_role_line(rank: int, job: Job) -> str:
    new_marker = " (New)" if getattr(job, "is_new_discovery", False) else ""
    location = job.location or "Location not listed"

    return f"{rank}. {job.company} — {job.title} — {location}{new_marker}"


def band_ranges() -> list[tuple[str, str]]:
    """(band, range label) from highest to lowest, e.g. ("excellent", "80+")."""
    ranges: list[tuple[str, str]] = []
    for index, (minimum, name) in enumerate(BANDS):
        is_lowest = index == len(BANDS) - 1
        if is_lowest:
            ranges.append((name, f"below {BANDS[index - 1][0]:.0f}"))
        else:
            ranges.append((name, f"{minimum:.0f}+"))
    return ranges


def format_score_legend() -> str:
    bands = " · ".join(f"{name.title()} {label}" for name, label in band_ranges())
    return f"Match scores are out of 100: {bands}."


SCORE_BASIS = "Each score reflects how closely the role matches your skills and experience."


def job_highlights(job: Job) -> list[str]:
    """The reasons worth showing for a match: matching skills and similarity to the candidate's experience."""
    return [
        reason
        for reason in job.why_matched
        if not reason.startswith(_UNINFORMATIVE_REASONS)
    ][:MAX_HIGHLIGHTS]


def format_match_summary(job: Job) -> str:
    return f"Match {job.score:.0f}/100 ({band_for(job.score).title()})"


def _job_url(job: Job) -> str | None:
    return job.url if job.url.startswith(("http://", "https://")) else None


def build_daily_email_report(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    qualified_jobs: int,
    newly_discovered_jobs: list[Job],
    additional_qualified_jobs: int,
    dashboard_url: str,
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

    jobs_to_list = newly_discovered_jobs[:EMAIL_JOB_LIST_LIMIT]
    remaining_count = len(newly_discovered_jobs) - len(jobs_to_list)

    lines = [
        f"Hello {_recipient_name()},",
        "",
        "Your CareerEngine job queue has been updated.",
        "",
        format_score_legend(),
        SCORE_BASIS,
        "",
        "Open dashboard:",
        dashboard_line,
        "",
        f"New postings today: {len(newly_discovered_jobs)}",
        "",
        "Top matches among today's new postings:",
    ]

    if jobs_to_list:
        for rank, job in enumerate(jobs_to_list, start=1):
            lines.append(format_top_role_line(rank, job))
            lines.append("   " + " · ".join([format_match_summary(job), *job_highlights(job)]))
            if _job_url(job):
                lines.append(f"   {job.url}")
        if remaining_count > 0:
            lines.append(f"...and {remaining_count} more. See the dashboard for the full list.")
    else:
        lines.append("No new job postings were found today.")

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
            "Kind regards,",
            "CareerEngine",
        ]
    )

    return "\n".join(lines).rstrip()


def _html_job_row(job: Job, *, is_last: bool) -> str:
    company = html.escape(job.company)
    title = html.escape(job.title)
    location = html.escape(job.location or "Location not listed")
    border = "" if is_last else f"border-bottom:1px solid {_BORDER};"

    band_bg, band_ink = _BAND_COLORS[band_for(job.score)]

    new_badge = (
        f'<span style="font-family:{_MONO_STACK};font-size:10px;letter-spacing:0.03em;'
        f'color:{_ACCENT_INK};background:{_ACCENT_TINT};border-radius:5px;padding:3px 6px;">NEW</span>'
        if getattr(job, "is_new_discovery", False)
        else ""
    )

    highlights = "".join(
        f'<div style="padding-top:3px;">&bull;&nbsp;{html.escape(reason)}</div>'
        for reason in job_highlights(job)
    )

    url = _job_url(job)
    view_link = (
        f'<a href="{html.escape(url, quote=True)}" '
        f'style="color:{_ACCENT_INK};text-decoration:none;font-weight:600;">View role &rarr;</a>'
        if url
        else ""
    )

    return f"""
      <tr>
        <td style="padding:16px;{border}" valign="top">
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
            <tr>
              <td width="46" valign="top" style="padding-right:12px;">
                <div style="background:{band_bg};border-radius:10px;text-align:center;padding:10px 0;">
                  <div style="font-family:{_MONO_STACK};font-size:18px;font-weight:600;color:{band_ink};line-height:1.1;">{job.score:.0f}</div>
                </div>
              </td>
              <td valign="top">
                <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                  <tr>
                    <td style="font-family:{_FONT_STACK};font-size:14px;color:{_TEXT_PRIMARY};padding-bottom:2px;">
                      <strong>{company}</strong>
                      <span style="color:{_TEXT_TERTIARY};">&nbsp;&middot;&nbsp;</span>{title}
                    </td>
                    <td align="right" valign="top" style="white-space:nowrap;padding-left:8px;">{new_badge}</td>
                  </tr>
                  <tr>
                    <td colspan="2" style="font-family:{_FONT_STACK};font-size:12.5px;color:{_TEXT_SECONDARY};">
                      {location}
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2" style="font-family:{_FONT_STACK};font-size:12.5px;line-height:1.5;color:{_TEXT_SECONDARY};padding-top:6px;">
                      {highlights}
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2" style="font-family:{_FONT_STACK};font-size:13px;padding-top:10px;">
                      {view_link}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </td>
      </tr>"""


def build_daily_email_html(
    *,
    health_records: list[SourceHealth],
    total_jobs_collected: int,
    qualified_jobs: int,
    newly_discovered_jobs: list[Job],
    additional_qualified_jobs: int,
    dashboard_url: str,
) -> str:
    successful_sources = sum(
        1 for record in health_records if record.status == "success"
    )

    disabled_records = [
        record for record in health_records if record.status == "disabled"
    ]

    dashboard_href = html.escape(dashboard_url or "#", quote=True)
    dashboard_configured = bool(dashboard_url)

    jobs_to_list = newly_discovered_jobs[:EMAIL_JOB_LIST_LIMIT]
    remaining_count = len(newly_discovered_jobs) - len(jobs_to_list)

    if jobs_to_list:
        job_rows = "".join(
            _html_job_row(job, is_last=(index == len(jobs_to_list) - 1))
            for index, job in enumerate(jobs_to_list)
        )
        more_link = (
            f"""
          <p style="font-family:{_FONT_STACK};font-size:13px;color:{_TEXT_SECONDARY};
                    text-align:center;margin:12px 0 0;">
            <a href="{dashboard_href}" style="color:{_TEXT_SECONDARY};text-decoration:underline;">
              + {remaining_count} more in your dashboard
            </a>
          </p>"""
            if remaining_count > 0 and dashboard_configured
            else ""
        )
        job_list_html = f"""
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                 style="border:1px solid {_BORDER};border-radius:12px;overflow:hidden;">
            {job_rows}
          </table>{more_link}"""
    else:
        job_list_html = f"""
          <p style="font-family:{_FONT_STACK};font-size:14px;color:{_TEXT_SECONDARY};
                    border:1px solid {_BORDER};border-radius:12px;padding:16px;margin:0;">
            No new job postings were found today.
          </p>"""

    if disabled_records:
        disabled_items = "".join(
            f'<li style="margin-bottom:4px;">'
            f'<strong style="color:{_TEXT_SECONDARY};">{html.escape(record.company)}</strong>: '
            f'{html.escape(record.reason or "Disabled.")}</li>'
            for record in disabled_records
        )
        disabled_html = f'<ul style="margin:6px 0 0;padding-left:18px;">{disabled_items}</ul>'
    else:
        disabled_html = f'<p style="margin:6px 0 0;">None.</p>'

    legend_chips = "".join(
        f'<span style="display:inline-block;font-family:{_FONT_STACK};font-size:12px;'
        f'color:{_BAND_COLORS[name][1]};background:{_BAND_COLORS[name][0]};'
        f'border-radius:100px;padding:3px 10px;margin:0 6px 6px 0;white-space:nowrap;">'
        f'<strong>{html.escape(name.title())}</strong>&nbsp;{html.escape(label)}</span>'
        for name, label in band_ranges()
    )
    score_legend_html = f"""
              <div style="margin:0 0 28px;">
                <p style="font-family:{_FONT_STACK};font-size:13px;line-height:1.6;color:{_TEXT_SECONDARY};margin:0 0 8px;">
                  <strong style="color:{_TEXT_PRIMARY};font-weight:600;">Match scores are out of 100.</strong>
                  {html.escape(SCORE_BASIS)}
                </p>
                <div>{legend_chips}</div>
              </div>"""

    cta_button = (
        f'<a href="{dashboard_href}" '
        f'style="display:inline-block;background:{_ACCENT};color:{_BUTTON_TEXT};'
        f'font-family:{_FONT_STACK};font-size:14px;font-weight:600;text-decoration:none;'
        f'padding:13px 24px;border-radius:10px;">View dashboard</a>'
        if dashboard_configured
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CareerEngine Daily Digest</title>
</head>
<body style="margin:0;padding:0;background:{_BG_PAGE};">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:{_BG_PAGE};">
    <tr>
      <td align="center" style="padding:40px 16px 64px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="600"
               style="max-width:600px;width:100%;background:{_BG_CARD};border:1px solid {_BORDER};border-radius:16px;">
          <tr>
            <td style="padding:40px 40px 32px;">

              <!-- Wordmark -->
              <span style="font-family:{_FONT_STACK};font-size:15px;font-weight:600;color:{_TEXT_PRIMARY};">CareerEngine</span>

              <p style="font-family:{_FONT_STACK};font-size:26px;line-height:1.25;font-weight:600;
                        color:{_TEXT_PRIMARY};margin:28px 0 12px;">
                {len(newly_discovered_jobs)} new role{"s" if len(newly_discovered_jobs) != 1 else ""} matched your profile today.
              </p>
              <p style="font-family:{_FONT_STACK};font-size:15px;line-height:1.6;color:{_TEXT_SECONDARY};margin:0 0 20px;max-width:440px;">
                Hello {html.escape(_recipient_name())}, your CareerEngine job queue has been updated.
              </p>
              {score_legend_html}

              {f'<div style="margin-bottom:32px;">{cta_button}</div>' if cta_button else ""}
              {"" if dashboard_configured else f'<p style="font-family:{_FONT_STACK};font-size:13px;color:{_TEXT_TERTIARY};margin:0 0 28px;">Dashboard URL not configured. Set CAREERENGINE_DASHBOARD_URL.</p>'}

              <!-- Stats -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%"
                     style="border:1px solid {_BORDER};border-radius:12px;margin-bottom:32px;">
                <tr>
                  <td width="33%" style="padding:16px 18px;border-right:1px solid {_BORDER};background:{_TILE_BG};border-radius:12px 0 0 12px;">
                    <div style="font-family:{_MONO_STACK};font-size:20px;font-weight:500;color:{_TEXT_PRIMARY};">{successful_sources}/{len(health_records)}</div>
                    <div style="font-family:{_FONT_STACK};font-size:11.5px;color:{_TEXT_SECONDARY};margin-top:3px;">Sources reached</div>
                  </td>
                  <td width="33%" style="padding:16px 18px;border-right:1px solid {_BORDER};background:{_TILE_BG};">
                    <div style="font-family:{_MONO_STACK};font-size:20px;font-weight:500;color:{_TEXT_PRIMARY};">{total_jobs_collected:,}</div>
                    <div style="font-family:{_FONT_STACK};font-size:11.5px;color:{_TEXT_SECONDARY};margin-top:3px;">Jobs collected</div>
                  </td>
                  <td width="34%" style="padding:16px 18px;background:{_TILE_BG};border-radius:0 12px 12px 0;">
                    <div style="font-family:{_MONO_STACK};font-size:20px;font-weight:500;color:{_TEXT_PRIMARY};">{qualified_jobs:,}</div>
                    <div style="font-family:{_FONT_STACK};font-size:11.5px;color:{_TEXT_SECONDARY};margin-top:3px;">Qualified &amp; ranked</div>
                  </td>
                </tr>
              </table>

              <!-- New jobs -->
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
                <tr>
                  <td style="font-family:{_FONT_STACK};font-size:12px;font-weight:600;letter-spacing:0.03em;
                             text-transform:uppercase;color:{_TEXT_SECONDARY};padding-right:8px;">New postings</td>
                  <td style="font-family:{_MONO_STACK};font-size:11px;color:{_ACCENT_INK};background:{_ACCENT_TINT};
                             border-radius:100px;padding:1px 8px;">{len(newly_discovered_jobs)}</td>
                </tr>
              </table>
              {job_list_html}

              <div style="height:1px;background:{_BORDER};margin:32px 0 24px;font-size:1px;line-height:1px;">&nbsp;</div>

              <p style="font-family:{_FONT_STACK};font-size:12.5px;line-height:1.7;color:{_TEXT_TERTIARY};margin:0;">
                <strong style="color:{_TEXT_SECONDARY};font-weight:500;">Disabled sources ({len(disabled_records)}):</strong>
                {disabled_html}
              </p>

              <p style="font-family:{_FONT_STACK};font-size:14px;color:{_TEXT_SECONDARY};margin-top:28px;">
                Kind regards,<br>CareerEngine
              </p>

            </td>
          </tr>
          <tr>
            <td style="padding:18px 40px;background:{_TILE_BG};border-top:1px solid {_BORDER};border-radius:0 0 16px 16px;">
              <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">
                <tr>
                  <td style="font-family:{_FONT_STACK};font-size:11.5px;color:{_TEXT_TERTIARY};">
                    {additional_qualified_jobs} additional qualified opportunit{"y" if additional_qualified_jobs == 1 else "ies"} attached
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
