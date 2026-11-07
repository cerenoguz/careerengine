import re

from src.ranking.level import has_senior_title


# -----------------------------
# Opportunity type patterns
# -----------------------------

INTERNSHIP_PATTERNS = [
    r"\bintern\b",
    r"\binternship\b",
    r"\bco-op\b",
    r"\bcoop\b",
    r"\buniversity intern\b",
    r"\bfall internship\b",
    r"\boff-cycle internship\b",
]

NEW_GRAD_PATTERNS = [
    r"\bnew grad\b",
    r"\bnew graduate\b",
    r"\buniversity graduate\b",
    r"\bearly career\b",
    r"\bentry level\b",
    r"\bentry-level\b",
    r"\bassociate software engineer\b",
    r"\bsoftware engineer\s+i\b(?!i)",
    r"\bgraduate software engineer\b",
    r"\brotational program\b",
]

# -----------------------------
# Roles to remove entirely
# -----------------------------
# These are not just "lower priority"; for this project we do not want them
# recommended because they are not aligned with CS/Math OPT goals.

EXCLUDED_ROLE_PATTERNS = [
    r"\bhelp desk\b",
    r"\bgeneral technician\b",
    r"\bfield technician\b",
    r"\bdesktop support\b",
    r"\bmaintenance assistant\b",
    r"\bsales\b",
    r"\baccount executive\b",
    r"\bbusiness development\b",
    r"\bmarketing\b",
    r"\bhuman resources\b",
    r"\bhr\b",
    r"\bfinance\b",
    r"\blegal\b",
    r"\brecruiter\b",
    r"\brecruiting\b",
    r"\btalent acquisition\b",
    r"\bexecutive assistant\b",
    r"\badministrative assistant\b",
]


# -----------------------------
# CS / Math relevance patterns
# -----------------------------

CS_STRONG_ROLE_PATTERNS = [
    r"\bsoftware engineer\b",
    r"\bsoftware developer\b",
    r"\bbackend engineer\b",
    r"\bback-end engineer\b",
    r"\bfull stack engineer\b",
    r"\bfull-stack engineer\b",
    r"\bdata engineer\b",
    r"\bmachine learning engineer\b",
    r"\bml engineer\b",
    r"\bai engineer\b",
    r"\bapplication developer\b",
    r"\bapplication engineer\b",
    r"\bautomation engineer\b",
    r"\bsdet\b",
    r"\bqa engineer\b",
    r"\bsoftware engineering intern\b",
    r"\bsoftware engineer intern\b",
    r"\bbackend intern\b",
    r"\bfull stack intern\b",
    r"\bfull-stack intern\b",
    r"\bdata engineering intern\b",
    r"\bmachine learning intern\b",
    r"\bml intern\b",
    r"\bai intern\b",
]

CS_ADJACENT_ROLE_PATTERNS = [
    r"\btechnical support engineer\b",
    r"\bdeveloper support engineer\b",
    r"\btechnical escalations engineer\b",
    r"\bescalations engineer\b",
    r"\bsolutions engineer\b",
    r"\bapplication systems analyst\b",
    r"\bbusiness systems analyst\b",
    r"\bsystems analyst\b",
    r"\bdata analyst\b",
    r"\bimplementation engineer\b",
    r"\bintegration engineer\b",
    r"\bplatform support engineer\b",
    r"\bcloud support engineer\b",
]


CS_DUTY_PATTERNS = [
    r"\bpython\b",
    r"\bjava\b",
    r"\btypescript\b",
    r"\bjavascript\b",
    r"\bsql\b",
    r"\bpostgresql\b",
    r"\bmysql\b",
    r"\brest api\b",
    r"\brest apis\b",
    r"\bapi\b",
    r"\bdebugging\b",
    r"\btroubleshooting production\b",
    r"\blogs\b",
    r"\bbackend\b",
    r"\bdatabase\b",
    r"\bdata pipeline\b",
    r"\bdistributed systems\b",
    r"\bcloud\b",
    r"\bdocker\b",
    r"\bkubernetes\b",
    r"\bautomation\b",
    r"\bscripting\b",
    r"\bmachine learning\b",
    r"\bml\b",
    r"\bai\b",
    r"\bsoftware\b",
    r"\bsystems\b",
]


LOW_CS_RELEVANCE_PATTERNS = [
    r"\bit support technician\b",
    r"\bdesktop support technician\b",
    r"\boffice support\b",
    r"\bdevice setup\b",
    r"\bpassword reset\b",
    r"\bhardware support\b",
]


# -----------------------------
# Matching helpers
# -----------------------------

def contains_phrase(text: str, phrase: str) -> bool:
    """
    Match a phrase as a real phrase, not as letters inside another word.

    Example:
    - "ai" should match "AI Engineer"
    - "ai" should NOT match "maintenance assistant"
    """
    escaped_phrase = re.escape(phrase)
    pattern = rf"(?<![a-zA-Z0-9]){escaped_phrase}(?![a-zA-Z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def matches_any_pattern(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


# -----------------------------
# Classification helpers
# -----------------------------

def is_internship(title: str, description: str) -> bool:
    """
    Classify internship status from the role title only.

    Job descriptions often mention separate internship/new-grad programs,
    university recruiting, or eligibility language. That should not make a
    normal full-time role appear as an internship.
    """
    return matches_any_pattern(title, INTERNSHIP_PATTERNS)


def is_new_grad(title: str, description: str) -> bool:
    """
    Classify new-grad / entry-level status from the role title only.

    A senior title prevents titles such as Principal Software Engineer I from
    being classified as new-grad just because they contain Software Engineer I.
    """
    if has_senior_title(title):
        return False

    return matches_any_pattern(title, NEW_GRAD_PATTERNS)


def is_excluded_role(title: str, description: str) -> bool:
    text = f"{title} {description}"
    return matches_any_pattern(text, EXCLUDED_ROLE_PATTERNS)


def classify_cs_relevance(title: str, description: str) -> tuple[str, list[str]]:
    """
    Classify whether a role is plausibly related to the user's CS/Math degree.

    This is important for OPT because the role should be related to the
    candidate's field of study, not merely open to OPT in general.
    """
    text = f"{title} {description}"
    reasons: list[str] = []

    # Title-only: descriptions routinely mention finance/legal/sales/marketing
    # as partner teams, which must not exclude an engineering role.
    if is_excluded_role(title, ""):
        return "excluded", ["Role category is excluded from CareerEngine recommendations"]

    strong_role_match = matches_any_pattern(text, CS_STRONG_ROLE_PATTERNS)
    adjacent_role_match = matches_any_pattern(text, CS_ADJACENT_ROLE_PATTERNS)
    cs_duty_match = matches_any_pattern(text, CS_DUTY_PATTERNS)
    low_relevance_match = matches_any_pattern(text, LOW_CS_RELEVANCE_PATTERNS)

    if strong_role_match:
        reasons.append("Role title or description strongly relates to Computer Science")
        return "strong_cs_relevance", reasons

    if adjacent_role_match and cs_duty_match:
        reasons.append(
            "Role is CS-adjacent and description mentions software, systems, data, APIs, debugging, or technical duties"
        )
        return "cs_adjacent", reasons

    if adjacent_role_match:
        reasons.append(
            "Role is CS-adjacent, but description should be reviewed for CS/Math degree relevance"
        )
        return "possibly_cs_adjacent", reasons

    if cs_duty_match and not low_relevance_match:
        reasons.append(
            "Description contains CS-related duties, but title is not an obvious target role"
        )
        return "unclear_but_possible", reasons

    if low_relevance_match:
        reasons.append("Role appears weakly related to Computer Science or Mathematics")
        return "low_cs_relevance", reasons

    return "unclear_cs_relevance", ["CS/Math degree relationship is unclear"]


