"""The single CareerEngine match score (0-100).

The score measures one thing: how well a posting matches the candidate's
experience. It is a weighted average of three components, each already
normalised to [0, 1]:

- skills:   how many of the technologies the role asks for the candidate knows
- semantic: similarity between the candidate's profile and the role's
            responsibilities and requirements
- role:     how close the job title is to the kinds of roles being targeted

Eligibility (seniority, years required, internships, work-authorization
restrictions, location) is decided *before* scoring and is never part of the
number. Whether a role is entry-level, and whether it is friendly to visa
sponsorship, are shown separately (the dashboard's New Grad and Visa
indicators) so that the score stays a pure measure of fit.
"""

from dataclasses import dataclass, field

from src.ranking.role_fit import RoleFit
from src.ranking.skills import SkillMatch


WEIGHTS = {
    "skills": 0.40,
    "semantic": 0.35,
    "role": 0.25,
}

# Sentence-BERT cosine similarity between a profile and a role posting lands in
# a narrow band in practice; these anchors stretch it to [0, 1].
SEMANTIC_LOW = 0.25
SEMANTIC_HIGH = 0.58

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


@dataclass
class MatchResult:
    score: float
    band: str
    components: dict[str, float]
    reasons: list[str] = field(default_factory=list)


def compute_match(
    *,
    role: RoleFit,
    skills: SkillMatch,
    semantic_cosine: float | None,
) -> MatchResult:
    """Combine the three components into a 0-100 score with an explanation.

    `semantic_cosine=None` means semantic scoring was unavailable; that
    component then gets neutral credit instead of silently dragging scores down.
    """
    semantic = 0.5 if semantic_cosine is None else normalise_semantic(semantic_cosine)

    components = {
        "skills": skills.score,
        "semantic": semantic,
        "role": role.score,
    }

    score = 100.0 * sum(WEIGHTS[name] * value for name, value in components.items())
    score = max(0.0, min(100.0, score))

    reasons = [f"Role: {role.family}", skills.summary]

    if semantic_cosine is not None:
        label = "high" if semantic >= 0.66 else "moderate" if semantic >= 0.33 else "low"
        reasons.append(f"Similarity to your experience: {label.title()}")

    return MatchResult(score=score, band=band_for(score), components=components, reasons=reasons)
