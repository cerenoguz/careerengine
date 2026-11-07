"""How close a job title is to the kinds of roles an early-career software
engineer is searching for.

This is deliberately title-based and explicit: a title is the most reliable
statement of what the job is, and a transparent family table is easier to
reason about (and to change) than a learned score.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RoleFit:
    score: float
    family: str


# (pattern, score, family). The best-scoring match in the title wins, so more
# specific families can be listed in any order.
_FAMILIES: list[tuple[re.Pattern[str], float, str]] = [
    (re.compile(r"\b(?:backend|back[\s-]end)\b", re.I), 1.0, "backend"),
    (re.compile(r"\bfull[\s-]?stack\b", re.I), 1.0, "full-stack"),
    (
        re.compile(
            r"\bsoftware (?:engineer|developer)\b|\bsde\b|\bswe\b|"
            r"\bmember of technical staff\b|\bapplication (?:engineer|developer)\b|"
            r"\bprogrammer\b|\bsoftware development engineer\b",
            re.I,
        ),
        0.95,
        "software engineer",
    ),
    (re.compile(r"\bdata (?:engineer|platform|infrastructure)\b|\banalytics engineer\b", re.I), 0.9, "data engineering"),
    (
        re.compile(
            r"\b(?:machine learning|ml|ai|applied ai|llm|nlp|genai)\b.{0,25}\b(?:engineer|developer)\b|"
            r"\b(?:engineer|developer)\b.{0,15}\b(?:machine learning|ml|ai|llm)\b",
            re.I,
        ),
        0.9,
        "ML/AI engineering",
    ),
    (
        re.compile(
            r"\b(?:platform|infrastructure|systems|tooling)\b.{0,40}\b(?:engineer|developer)\b|"
            r"\b(?:engineer|developer)\b.{0,40}\b(?:platform|infrastructure)\b|"
            r"\bdeveloper (?:productivity|experience|tools|tooling)\b|"
            r"\bsre\b|\bdevops\b|\bsite reliability\b|\breliability engineer",
            re.I,
        ),
        0.75,
        "platform/infrastructure",
    ),
    (re.compile(r"\bfront[\s-]?end\b|\bui engineer\b|\bweb (?:developer|engineer)\b", re.I), 0.8, "front-end"),
    (re.compile(r"\bsdet\b|\bqa\b|\bquality\b|\btest(?:ing)? (?:engineer|automation)\b|\bautomation engineer\b", re.I), 0.65, "QA/automation"),
    (re.compile(r"\b(?:ios|android|mobile)\b", re.I), 0.55, "mobile"),
    (re.compile(r"\b(?:security|appsec|devsecops)\b", re.I), 0.55, "security"),
    (
        re.compile(
            r"\b(?:solutions?|forward[\s-]deployed|customer|technical support|support|"
            r"implementation|integration|escalations?|sales)\s+engineer\b",
            re.I,
        ),
        0.5,
        "solutions/support engineering",
    ),
    (re.compile(r"\b(?:research|applied) (?:scientist|engineer)\b|\bdata scientist\b", re.I), 0.45, "research/data science"),
    (re.compile(r"\b(?:data|business|systems|product) analyst\b", re.I), 0.4, "analyst"),
    (
        re.compile(
            r"\b(?:embedded|firmware|hardware|fpga|asic|rtl|mechanical|electrical|"
            r"robotics|autonomy|perception|simulation|manufacturing|optical)\b",
            re.I,
        ),
        0.3,
        "hardware/specialized",
    ),
]

_ADVOCACY = re.compile(r"\b(?:advocate|evangelist|relations|community manager)\b", re.I)

_GENERIC_ENGINEER = re.compile(r"\b(?:engineer|developer)\b", re.I)


def assess_role_fit(title: str) -> RoleFit:
    best = RoleFit(0.0, "other")

    for pattern, score, family in _FAMILIES:
        if pattern.search(title) and score > best.score:
            best = RoleFit(score, family)

    # Advocacy / developer-relations roles talk about developers and AI but are
    # not engineering roles.
    if _ADVOCACY.search(title):
        return RoleFit(0.25, "developer relations")

    # A hardware/specialized word anywhere in the title caps an otherwise
    # generic match ("Embedded Software Engineer" is not a core SWE target).
    specialized = next((s for p, s, f in _FAMILIES if f == "hardware/specialized" and p.search(title)), None)
    if specialized is not None and best.score > specialized and best.family == "software engineer":
        return RoleFit(max(specialized + 0.1, 0.4), "hardware/specialized")

    if best.score == 0.0 and _GENERIC_ENGINEER.search(title):
        return RoleFit(0.35, "other engineering")

    return best
