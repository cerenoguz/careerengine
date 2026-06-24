from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileFitResult:
    score: float
    band: str
    reasons: list[str]


def classify_profile_fit(score: float) -> str:
    if score >= 70:
        return "strong"
    if score >= 60:
        return "moderate"
    if score >= 50:
        return "lower_priority"
    return "weak"


def calculate_profile_fit_score(
    *,
    semantic_similarity: float,
    description_similarity: float,
    cs_relevance_status: str,
    is_internship: bool,
    is_new_grad: bool,
    required_years_min: int | None,
    years_requirement_type: str,
    title_description_conflict: bool,
    required_years_max: int | None = None,
    senior_title_signal: bool = False,
) -> ProfileFitResult:
    """
    Produce a calibrated CareerEngine profile-fit score from 0–100.

    This is a CareerEngine fit score, not a literal probability of qualifying.
    Sentence-BERT contributes bounded semantic evidence; deterministic signals
    such as technical relevance and early-career eligibility remain important.
    """
    score = 0.0
    reasons: list[str] = []

    semantic_component = max(0.0, min(1.0, semantic_similarity)) * 40
    score += semantic_component
    reasons.append(f"AI semantic profile alignment (+{semantic_component:.1f})")

    wording_component = max(0.0, min(1.0, description_similarity)) * 20
    score += wording_component
    reasons.append(f"Profile wording alignment (+{wording_component:.1f})")

    relevance_points = {
        "strong_cs_relevance": 40,
        "cs_adjacent": 25,
        "possibly_cs_adjacent": 12,
    }.get(cs_relevance_status, 0)

    score += relevance_points
    if relevance_points:
        reasons.append(f"Technical/domain relevance (+{relevance_points})")

    if is_internship:
        score += 12
        reasons.append("Internship/co-op eligibility (+12)")

    if is_new_grad:
        score += 14
        reasons.append("New-grad / early-career eligibility (+14)")

    if (
        required_years_min in {3, 4}
        or required_years_max in {3, 4}
    ):
        penalty = 12 if years_requirement_type == "required" else 6
        score -= penalty
        reasons.append(f"3–4 year experience gap (-{penalty})")

    if senior_title_signal and not title_description_conflict:
        score -= 18
        reasons.append("Senior-title signal without junior evidence (-18)")

    if title_description_conflict:
        score += 8
        reasons.append(
            "Junior-friendly description overrides senior-looking title (+8)"
        )

    score = max(0.0, min(100.0, score))

    return ProfileFitResult(
        score=score,
        band=classify_profile_fit(score),
        reasons=reasons,
    )


def profile_fit_ranking_adjustment(score: float) -> tuple[float, str]:
    """
    Convert the calibrated profile-fit band into a bounded live-ranking change.

    This affects ordering only. It does not override hard exclusions and does
    not remove lower-scoring roles from the current qualified pool.
    """
    if score >= 70:
        return 25.0, "Strong AI profile fit (+25)"
    if score >= 60:
        return 12.0, "Moderate AI profile fit (+12)"
    if score >= 50:
        return 0.0, "Lower-priority AI profile fit (no adjustment)"
    return -12.0, "Lower-confidence AI profile fit (-12)"
