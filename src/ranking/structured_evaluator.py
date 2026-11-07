import re
from dataclasses import dataclass, field


HARD_AUTH_PATTERNS = {
    "citizenship_required": [
        r"\bu\.?s\.?\s+citizen(?:ship)?\s+(?:is\s+)?required\b",
        r"\bmust\s+be\s+a\s+u\.?s\.?\s+citizen\b",
        r"\bu\.?s\.?\s+citizens?\s+only\b",
    ],
    "permanent_resident_required": [
        r"\bpermanent\s+resident(?:s)?\s+only\b",
        r"\bgreen\s+card\s+(?:is\s+)?required\b",
        r"\bmust\s+be\s+a\s+permanent\s+resident\b",
    ],
    "clearance_required": [
        r"\bactive\s+(?:security\s+)?clearance\s+required\b",
        r"\bsecurity\s+clearance\s+required\b",
        r"\btop\s+secret\s+clearance\b",
        r"\bts/sci\b",
    ],
    "export_control_restriction": [
        r"\bitar\s+(?:person|eligible|requirement|required)\b",
        r"\bexport\s+control(?:led)?\s+(?:person|eligible|requirement|required)\b",
        r"\bu\.?s\.?\s+person\s+(?:is\s+)?required\b",
    ],
}

NEW_GRAD_PATTERNS = [
    r"\bnew\s+grad(?:uate)?s?\b",
    r"\brecent\s+grad(?:uate)?s?\b",
    r"\bearly[-\s]career\b",
    r"\bentry[-\s]level\b",
    r"\bgraduates?\s+(?:are\s+)?encouraged\b",
]

INTERNSHIP_PATTERNS = [
    r"\binternship\b",
    r"\bintern\b",
    r"\bco[-\s]?op\b",
]

INTERNSHIP_DESCRIPTION_PATTERNS = [
    r"\bthis\s+(?:internship|intern|co[-\s]?op)\b",
    r"\b(?:internship|co[-\s]?op)\s+(?:role|position|opportunity)\b",
    r"\b(?:summer|fall|spring)\s+20\d{2}\s+(?:internship|intern|co[-\s]?op)\b",
]

NEW_GRAD_DESCRIPTION_PATTERNS = [
    r"\bthis\s+(?:role|position|opportunity)\b.{0,80}\b(?:new\s+grad|recent\s+grad|early[-\s]career|entry[-\s]level)\b",
    r"\bnew\s+graduates?\s+(?:are\s+)?encouraged\b",
    r"\brecent\s+graduates?\s+(?:are\s+)?encouraged\b",
]

@dataclass
class StructuredEvaluation:
    new_grad_signal: str = "no"
    internship_signal: str = "no"

    citizenship_required: str = "no"
    permanent_resident_required: str = "no"
    clearance_required: str = "no"
    export_control_restriction: str = "no"
    sponsorship_language: str = "unclear"

    hard_no: bool = False
    reason: str = ""
    evidence: list[str] = field(default_factory=list)


def _matching_evidence(text: str, patterns: list[str]) -> list[str]:
    matches: list[str] = []

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            start = max(0, match.start() - 55)
            end = min(len(text), match.end() + 85)
            excerpt = " ".join(text[start:end].split())
            matches.append(excerpt)

    return matches


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def evaluate_job_description(title: str, clean_description: str) -> StructuredEvaluation:
    """Read work-authorization, sponsorship, new-grad and internship signals.

    Seniority is deliberately not decided here: see `src.ranking.level`.
    `clean_description` should already be plain text (`text_clean.clean_description`).
    """
    normalized = f"{title}\n{clean_description}".lower()
    title_normalized = title.lower()
    description_normalized = clean_description.lower()

    result = StructuredEvaluation()

    if (
        _contains_any(title_normalized, NEW_GRAD_PATTERNS)
        or _contains_any(description_normalized, NEW_GRAD_DESCRIPTION_PATTERNS)
    ):
        result.new_grad_signal = "yes"

    if (
        _contains_any(title_normalized, INTERNSHIP_PATTERNS)
        or _contains_any(description_normalized, INTERNSHIP_DESCRIPTION_PATTERNS)
    ):
        result.internship_signal = "yes"

    for field_name, patterns in HARD_AUTH_PATTERNS.items():
        evidence = _matching_evidence(normalized, patterns)

        if evidence:
            setattr(result, field_name, "yes")
            result.evidence.extend(evidence)

    if re.search(
        r"\bno\s+sponsorship\b"
        r"|\bwill\s+not\s+sponsor\b"
        r"|\bunable\s+to\s+(?:provide|offer)\s+(?:visa\s+)?sponsorship\b"
        r"|\bdoes\s+not\s+provide\s+(?:visa\s+)?sponsorship\b",
        normalized,
    ):
        result.sponsorship_language = "unavailable"
    elif re.search(r"\bsponsorship\s+available\b|\bopen\s+to\s+sponsorship\b", normalized):
        result.sponsorship_language = "available"

    result.hard_no = any(
        getattr(result, field_name) == "yes" for field_name in HARD_AUTH_PATTERNS
    )
    if result.hard_no:
        result.reason = "Excluded because the description contains a clear work-authorization restriction."

    return result
