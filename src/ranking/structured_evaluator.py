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

REQUIRED_CONTEXT_PATTERNS = [
    r"\brequired\b",
    r"\bmust\s+have\b",
    r"\bminimum\s+of\b",
    r"\bat\s+least\b",
]

PREFERRED_CONTEXT_PATTERNS = [
    r"\bpreferred\b",
    r"\bnice\s+to\s+have\b",
    r"\bplus\b",
    r"\bideally\b",
]

YEAR_PATTERN = re.compile(
    r"\b(?P<minimum>[0-9]+)\s*"
    r"(?:(?P<plus>\+)|[-–]\s*(?P<maximum>[0-9]+))?\s*"
    r"years?(?:\s+of)?(?:\s+[a-zA-Z/,& -]+)?\s+experience\b",
    flags=re.IGNORECASE,
)


@dataclass
class StructuredEvaluation:
    required_years_min: int | None = None
    required_years_max: int | None = None
    years_requirement_type: str = "unclear"
    new_grad_signal: str = "no"
    internship_signal: str = "no"

    citizenship_required: str = "no"
    permanent_resident_required: str = "no"
    clearance_required: str = "no"
    export_control_restriction: str = "no"
    sponsorship_language: str = "unclear"

    hard_no: bool = False
    title_description_conflict: bool = False
    experience_fit: str = "unclear"
    reason: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0


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


def _classify_years_requirement(
    description: str,
) -> tuple[int | None, int | None, str, list[str]]:
    matches = list(YEAR_PATTERN.finditer(description))
    if not matches:
        return None, None, "unclear", []

    minimum = min(int(match.group("minimum")) for match in matches)

    maximum_values = [
        int(match.group("maximum"))
        for match in matches
        if match.group("maximum") is not None
    ]
    maximum = max(maximum_values) if maximum_values else None

    evidence: list[str] = []
    requirement_types: list[str] = []

    for match in matches:
        sentence_start = max(
            description.rfind(".", 0, match.start()),
            description.rfind(";", 0, match.start()),
            description.rfind("\n", 0, match.start()),
        ) + 1

        sentence_end_candidates = [
            position
            for position in [
                description.find(".", match.end()),
                description.find(";", match.end()),
                description.find("\n", match.end()),
            ]
            if position != -1
        ]
        sentence_end = (
            min(sentence_end_candidates)
            if sentence_end_candidates
            else len(description)
        )

        sentence = " ".join(description[sentence_start:sentence_end].split())
        evidence.append(sentence)

        normalized_sentence = sentence.lower()
        if _contains_any(normalized_sentence, PREFERRED_CONTEXT_PATTERNS):
            requirement_types.append("preferred")
        elif _contains_any(normalized_sentence, REQUIRED_CONTEXT_PATTERNS):
            requirement_types.append("required")
        else:
            requirement_types.append("unclear")

    if "required" in requirement_types:
        requirement_type = "required"
    elif "preferred" in requirement_types:
        requirement_type = "preferred"
    else:
        requirement_type = "unclear"

    return minimum, maximum, requirement_type, evidence


def evaluate_job_description(title: str, description: str) -> StructuredEvaluation:
    text = f"{title}\n{description}"
    normalized = text.lower()

    result = StructuredEvaluation()

    (
        result.required_years_min,
        result.required_years_max,
        result.years_requirement_type,
        years_evidence,
    ) = _classify_years_requirement(description)
    result.evidence.extend(years_evidence)

    title_normalized = title.lower()
    description_normalized = description.lower()

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

    hard_no_evidence: list[str] = []

    for field_name, patterns in HARD_AUTH_PATTERNS.items():
        evidence = _matching_evidence(normalized, patterns)

        if evidence:
            setattr(result, field_name, "yes")
            hard_no_evidence.extend(evidence)

    result.evidence.extend(hard_no_evidence)

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

    explicit_five_plus_required = (
        result.required_years_min is not None
        and result.required_years_min >= 5
        and result.years_requirement_type == "required"
    )

    authorization_hard_no = any(
        getattr(result, field_name) == "yes"
        for field_name in HARD_AUTH_PATTERNS
    )

    result.hard_no = authorization_hard_no or explicit_five_plus_required

    senior_title_signal = bool(
        re.search(
            r"\b(?:senior|staff|principal|lead|engineer\s+ii|engineer\s*\(l2\)|\bl2\b)\b",
            title,
            flags=re.IGNORECASE,
        )
    )

    entry_level_years_signal = (
        result.required_years_min is not None
        and result.required_years_min <= 2
        and (
            result.required_years_max is None
            or result.required_years_max <= 2
        )
    )

    junior_description_signal = (
        result.new_grad_signal == "yes"
        or result.internship_signal == "yes"
        or entry_level_years_signal
    )

    result.title_description_conflict = senior_title_signal and junior_description_signal

    if result.hard_no:
        result.experience_fit = "unlikely"
        if authorization_hard_no:
            result.reason = "Excluded because the description contains a clear work-authorization restriction."
        else:
            result.reason = "Excluded because the description explicitly requires 5+ years of experience."
        result.confidence = 0.95
        return result

    if result.internship_signal == "yes" or result.new_grad_signal == "yes":
        result.experience_fit = "strong"
        result.reason = "Strong early-career fit based on internship or new-grad language."
        result.confidence = 0.90
        return result

    if entry_level_years_signal:
        result.experience_fit = "strong"
        result.reason = "Strong experience fit because the posting asks for 0–2 years."
        result.confidence = 0.85
        return result

    if (
        result.required_years_min in {3, 4}
        or result.required_years_max in {3, 4}
    ):
        result.experience_fit = "possible"
        result.reason = "Possible fit: the posting asks for 3–4 years, so it should be demoted rather than excluded."
        result.confidence = 0.80
        return result

    result.experience_fit = "unclear"
    result.reason = "Experience requirement is not explicit; profile fit should determine ranking."
    result.confidence = 0.60
    return result
