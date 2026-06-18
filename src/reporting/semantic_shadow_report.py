from pathlib import Path

from src.models import Job


def save_semantic_shadow_report(
    *,
    path: Path,
    jobs: list[Job],
    status: str,
) -> Path:
    """
    Save semantic-shadow diagnostics without affecting recommendation ranking.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "CareerEngine Semantic Shadow Report",
        "",
        "Sentence-BERT semantic similarity is diagnostic only in this version.",
        "It does not change the CareerEngine score, email order, or top 25.",
        "",
        f"Semantic shadow status: {status}",
        f"Qualified jobs evaluated: {len(jobs)}",
        "",
    ]

    if status != "available":
        lines.extend(
            [
                "Semantic scores were not available for this run.",
                "CareerEngine continued using lexical wording similarity only.",
                "",
            ]
        )
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    lines.extend(
        [
            "Top semantic-alignment jobs:",
            "",
        ]
    )

    semantic_ranked_jobs = sorted(
        jobs,
        key=lambda job: job.semantic_similarity,
        reverse=True,
    )

    for index, job in enumerate(semantic_ranked_jobs[:50], start=1):
        lines.extend(
            [
                f"{index}. {job.company} — {job.title}",
                f"Location: {job.location}",
                f"Current CareerEngine score: {job.score:.2f}",
                f"Lexical wording alignment: {job.description_similarity:.3f}",
                f"Semantic alignment: {job.semantic_similarity:.3f}",
                f"Opportunity type: "
                f"{'Internship' if job.is_internship else 'New grad' if job.is_new_grad else 'General'}",
                f"URL: {job.url}",
                "",
            ]
        )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
