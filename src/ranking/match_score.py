"""The single CareerEngine match score (0-100).

One number replaces the old pair of scores (an additive keyword score and a
separately calibrated "AI Fit"), whose bands did not line up with real data.
The match score is a weighted average of five components, each already
normalised to [0, 1], so it reads as what it is: how well a posting fits an
early-career software search, on level, role, skills, semantics, and
work-authorization language.

Hard eligibility (senior roles, internships, authorization restrictions,
location) is decided *before* scoring and is never traded off against it.
"""

from dataclasses import dataclass, field

from src.ranking.level import LevelAssessment
from src.ranking.role_fit import RoleFit
from src.ranking.skills import SkillMatch


WEIGHTS = {
    "level": 0.30,
    "role": 0.25,
    "skills": 0.20,
    "semantic": 0.15,
    "authorization": 0.10,
}

# Sentence-BERT cosine similarity between a profile and a role posting lands in
# a narrow band in practice; these anchors stretch it to [0, 1].
SEMANTIC_LOW = 0.12
SEMANTIC_HIGH = 0.52

# (minimum score, band name)
BANDS = [
    (80.0, "excellent"),
    (70.0, "strong"),
    (60.0, "good"),
    (0.0, "fair"),
]


def band_for(score: float) -> str:
    for minimum, name in BANDS:
        if score >= minimum:
            return name
    return "fair"


def normalise_semantic(cosine: float) -> float:
    return max(0.0, min(1.0, (cosine - SEMANTIC_LOW) / (SEMANTIC_HIGH - SEMANTIC_LOW)))


def authorization_component(eligibility_status: str, sponsorship_language: str) -> float:
    if sponsorship_language == "available":
        return 1.0
    if sponsorship_language == "unavailable":
        return 0.2
    if eligibility_status == "likely_compatible":
        return 0.85
    if eligibility_status == "likely_incompatible":
        return 0.0
    return 0.55


@dataclass
class MatchResult:
    score: float
    band: str
    components: dict[str, float]
    reasons: list[str] = field(default_factory=list)


def compute_match(
    *,
    level: LevelAssessment,
    role: RoleFit,
    skills: SkillMatch,
    semantic_cosine: float | None,
    eligibility_status: str,
    sponsorship_language: str,
) -> MatchResult:
    """Combine the five components into a 0-100 score with an explanation.

    `semantic_cosine=None` means semantic scoring was unavailable; that
    component then gets neutral credit instead of silently dragging scores down.
    """
    semantic = 0.5 if semantic_cosine is None else normalise_semantic(semantic_cosine)

    components = {
        "level": level.level_score,
        "role": role.score,
        "skills": skills.score,
        "semantic": semantic,
        "authorization": authorization_component(eligibility_status, sponsorship_language),
    }

    score = 100.0 * sum(WEIGHTS[name] * value for name, value in components.items())
    score = max(0.0, min(100.0, score))

    reasons = [level.summary, f"Role: {role.family}", skills.summary]

    if semantic_cosine is not None:
        label = "high" if semantic >= 0.66 else "moderate" if semantic >= 0.33 else "low"
        reasons.append(f"Profile similarity: {label}")

    if sponsorship_language == "available":
        reasons.append("Sponsorship available")
    elif sponsorship_language == "unavailable":
        reasons.append("No sponsorship stated")
    elif eligibility_status == "likely_compatible":
        reasons.append("Work-authorization friendly")

    return MatchResult(score=score, band=band_for(score), components=components, reasons=reasons)
