from pathlib import Path

from src.models import Job
from src.ranking.match_score import BANDS, WEIGHTS


def _title_case(value: str) -> str:
    return value.replace("_", " ").title()


def save_match_report(
    *,
    path: Path,
    jobs: list[Job],
    semantic_status: str,
) -> Path:
    """
    Save a diagnostic breakdown of today's ranking: the score distribution and,
    for the top jobs, each component that went into the match score.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "CareerEngine Match Report",
        "",
        "Match score (0-100) = weighted average of five components, each 0-1:",
        *[f"- {name}: {weight:.0%}" for name, weight in WEIGHTS.items()],
        "",
        f"Semantic scoring: {semantic_status}",
        *(
            ["Semantic component gets neutral credit when semantic scoring is not available."]
            if semantic_status != "available"
            else []
        ),
        f"Eligible jobs ranked: {len(jobs)}",
        "",
        "Distribution:",
    ]

    for minimum, name in BANDS:
        lines.append(
            f"- {name.title()} ({minimum:.0f}+): "
            f"{sum(job.profile_fit_band == name for job in jobs)}"
        )

    lines.extend(["", "Top matches:", ""])

    for index, job in enumerate(jobs[:60], start=1):
        components = ", ".join(
            f"{name} {value:.2f}" for name, value in job.match_components.items()
        )
        lines.extend(
            [
                f"{index}. {job.company} — {job.title}",
                f"Location: {job.location}",
                f"Match: {job.score:.1f} ({job.profile_fit_band})",
                f"Components: {components}",
                f"Level: {job.level} | Role: {job.role_family}",
                f"Semantic cosine: {job.semantic_similarity:.3f}",
                f"Sponsorship language: {_title_case(job.sponsorship_language)}",
                f"Eligibility: {_title_case(job.eligibility_status)}",
            ]
        )

        for reason in job.profile_fit_reasons:
            lines.append(f"- {reason}")

        lines.extend([f"URL: {job.url}", ""])

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
