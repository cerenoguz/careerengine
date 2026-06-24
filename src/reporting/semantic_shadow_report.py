from pathlib import Path

from src.models import Job


def _opportunity_type(job: Job) -> str:
    if job.is_internship:
        return "Internship"
    if job.is_new_grad:
        return "New grad / early career"
    return "General"


def _yes_no(value: str) -> str:
    return value.replace("_", " ").title()


def save_semantic_shadow_report(
    *,
    path: Path,
    jobs: list[Job],
    status: str,
) -> Path:
    """
    Save profile-fit and semantic diagnostics without affecting live ranking.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "CareerEngine AI Profile-Fit Shadow Report",
        "",
        "Sentence-BERT and profile-fit scoring are diagnostic only in this version.",
        "They do not change CareerEngine ranking, filtering, email order, or top 25.",
        "",
        f"Semantic status: {status}",
        f"Qualified jobs evaluated: {len(jobs)}",
        "",
    ]

    if status != "available":
        lines.extend(
            [
                "AI semantic scores were not available for this run.",
                "CareerEngine continued using rule-based ranking only.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    band_counts = {
        "strong": sum(job.profile_fit_band == "strong" for job in jobs),
        "moderate": sum(job.profile_fit_band == "moderate" for job in jobs),
        "lower_priority": sum(
            job.profile_fit_band == "lower_priority" for job in jobs
        ),
        "weak": sum(job.profile_fit_band == "weak" for job in jobs),
    }

    lines.extend(
        [
            "Profile-fit distribution across all qualified jobs:",
            f"- Strong (70+): {band_counts['strong']}",
            f"- Moderate (60–69): {band_counts['moderate']}",
            f"- Lower priority (50–59): {band_counts['lower_priority']}",
            f"- Weak (below 50): {band_counts['weak']}",
            "",
            "Top AI profile-fit jobs:",
            "",
        ]
    )

    profile_ranked_jobs = sorted(
        jobs,
        key=lambda job: (job.profile_fit_score, job.semantic_similarity),
        reverse=True,
    )

    for index, job in enumerate(profile_ranked_jobs[:60], start=1):
        lines.extend(
            [
                f"{index}. {job.company} — {job.title}",
                f"Location: {job.location}",
                f"Current CareerEngine score: {job.score:.2f}",
                f"AI profile-fit score: {job.profile_fit_score:.1f} ({job.profile_fit_band})",
                f"Semantic alignment: {job.semantic_similarity:.3f}",
                f"Lexical wording alignment: {job.description_similarity:.3f}",
                f"Opportunity type: {_opportunity_type(job)}",
                f"Experience fit: {_yes_no(job.experience_fit)}",
                (
                    "Years requirement: "
                    f"{job.required_years_min if job.required_years_min is not None else 'Not stated'} "
                    f"({job.years_requirement_type})"
                ),
                f"Hard exclusion: {'Yes' if job.hard_no else 'No'}",
                f"Citizenship required: {_yes_no(job.citizenship_required)}",
                f"Permanent resident required: {_yes_no(job.permanent_resident_required)}",
                f"Clearance required: {_yes_no(job.clearance_required)}",
                f"Export-control restriction: {_yes_no(job.export_control_restriction)}",
                f"Sponsorship language: {_yes_no(job.sponsorship_language)}",
                f"Evaluation: {job.evaluation_reason}",
            ]
        )

        if job.evaluation_evidence:
            lines.append("Evidence:")
            for evidence in job.evaluation_evidence[:3]:
                lines.append(f"- {evidence}")

        if job.profile_fit_reasons:
            lines.append("Profile-fit factors:")
            for reason in job.profile_fit_reasons:
                lines.append(f"- {reason}")

        lines.extend(
            [
                f"URL: {job.url}",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
