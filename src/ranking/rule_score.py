import re


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

SENIOR_TITLE_BLOCKING_PATTERNS = [
    r"\bsenior\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bdistinguished\b",
    r"\barchitect\b",
    r"\bvp\b",
    r"\bhead of\b",
]


def has_senior_title_blocker(title: str) -> bool:
    normalized_title = title.lower()
    return any(
        re.search(pattern, normalized_title)
        for pattern in SENIOR_TITLE_BLOCKING_PATTERNS
    )



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
# Scoring dictionaries
# -----------------------------

ROLE_KEYWORDS = {
    "software engineering intern": 12,
    "software engineer intern": 12,
    "software engineer internship": 12,
    "backend intern": 10,
    "full stack intern": 10,
    "full-stack intern": 10,
    "data engineering intern": 10,
    "machine learning intern": 10,
    "ml intern": 10,
    "ai intern": 10,
    "new grad software engineer": 14,
    "graduate software engineer": 12,
    "software engineer": 10,
    "software engineer i": 12,
    "associate software engineer": 12,
    "software developer": 10,
    "backend engineer": 10,
    "full stack engineer": 8,
    "full-stack engineer": 8,
    "data engineer": 8,
    "machine learning engineer": 8,
    "ml engineer": 8,
    "ai engineer": 8,
    "application developer": 7,
    "automation engineer": 7,
    "qa engineer": 6,
    "sdet": 6,
}

CS_ADJACENT_ROLE_KEYWORDS = {
    "technical support engineer": 6,
    "developer support engineer": 6,
    "technical escalations engineer": 6,
    "escalations engineer": 5,
    "solutions engineer": 5,
    "application systems analyst": 5,
    "business systems analyst": 5,
    "systems analyst": 5,
    "data analyst": 5,
    "implementation engineer": 4,
    "integration engineer": 4,
    "cloud support engineer": 4,
    "platform support engineer": 4,
}

TECH_KEYWORDS = {
    "python": 5,
    "java": 5,
    "typescript": 4,
    "javascript": 3,
    "sql": 5,
    "postgresql": 5,
    "mysql": 4,
    "rest api": 4,
    "rest apis": 4,
    "api": 3,
    "backend": 5,
    "database": 4,
    "data pipeline": 4,
    "machine learning": 4,
    "distributed systems": 4,
    "cloud": 3,
    "docker": 3,
    "kubernetes": 3,
    "automation": 3,
    "scripting": 3,
}

INDUSTRY_KEYWORDS = {
    "healthcare": 4,
    "developer tools": 4,
    "infrastructure": 4,
    "saas": 3,
    "ai": 4,
    "machine learning": 4,
    "data platform": 4,
}

SENIORITY_PENALTY_KEYWORDS = {
    "senior": -25,
    "staff": -35,
    "principal": -40,
    "lead": -30,
    "manager": -35,
    "director": -45,
    "distinguished": -50,
    "architect": -30,
    "vp": -60,
    "head of": -60,
    "5+ years": -35,
    "6+ years": -40,
    "7+ years": -45,
    "8+ years": -50,
    "10+ years": -60,
}


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

    Senior-title blockers prevent titles such as Principal Software Engineer I
    from being incorrectly classified as new-grad just because they contain
    Software Engineer I.
    """
    if has_senior_title_blocker(title):
        return False

    return matches_any_pattern(title, NEW_GRAD_PATTERNS)


def is_excluded_role(title: str, description: str) -> bool:
    text = f"{title} {description}"
    return matches_any_pattern(text, EXCLUDED_ROLE_PATTERNS)


def is_target_role(title: str, description: str) -> bool:
    text = f"{title} {description}"

    return (
        matches_any_pattern(text, CS_STRONG_ROLE_PATTERNS)
        or matches_any_pattern(text, CS_ADJACENT_ROLE_PATTERNS)
    )

UNREALISTIC_SENIORITY_PATTERNS = [
    r"\bsenior\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\blead\b",
    r"\bmanager\b",
    r"\bdirector\b",
    r"\bdistinguished\b",
    r"\barchitect\b",
    r"\bvp\b",
    r"\bhead of\b",
    r"\b5\+ years\b",
    r"\b6\+ years\b",
    r"\b7\+ years\b",
    r"\b8\+ years\b",
    r"\b10\+ years\b",
]


MID_LEVEL_TITLE_PATTERNS = [
    r"\bsoftware engineer\s+ii\b",
    r"\bbackend engineer\s+ii\b",
    r"\bfull stack engineer\s+ii\b",
    r"\bfull-stack engineer\s+ii\b",
    r"\bdata engineer\s+ii\b",
    r"\bengineer\s+ii\b",
    r"\bsoftware engineer\s*\(l2\)(?=\W|$)",
    r"\bengineer\s*\(l2\)(?=\W|$)",
    r"\bsoftware engineer\s+l2(?=\W|$)",
    r"\bengineer\s+l2(?=\W|$)",
    r"\blevel\s*2\b",
]


def has_mid_level_title(title: str) -> bool:
    """
    Return True for title-level signals that usually indicate a role above
    pure new-grad / entry-level, but not senior enough to exclude entirely.
    """
    return matches_any_pattern(title, MID_LEVEL_TITLE_PATTERNS)


def has_unrealistic_seniority(title: str, description: str) -> bool:
    """
    Return True for roles that are CS-related but unrealistic for a new-grad /
    early-career candidate.

    We still allow internships and new-grad roles even if the description
    mentions mentorship, managers, or senior engineers.
    """
    if is_internship(title, description) or is_new_grad(title, description):
        return False

    title_match = matches_any_pattern(title, UNREALISTIC_SENIORITY_PATTERNS)

    years_required_patterns = [
        r"\b5\+ years\b",
        r"\b6\+ years\b",
        r"\b7\+ years\b",
        r"\b8\+ years\b",
        r"\b10\+ years\b",
        r"\bminimum of 5 years\b",
        r"\bat least 5 years\b",
        r"\b5 years of experience\b",
    ]

    description_years_match = matches_any_pattern(description, years_required_patterns)

    return title_match or description_years_match


def classify_cs_relevance(title: str, description: str) -> tuple[str, list[str]]:
    """
    Classify whether a role is plausibly related to the user's CS/Math degree.

    This is important for OPT because the role should be related to the
    candidate's field of study, not merely open to OPT in general.
    """
    text = f"{title} {description}"
    reasons: list[str] = []

    if is_excluded_role(title, description):
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


# -----------------------------
# Scoring
# -----------------------------

def score_job(title: str, description: str, eligibility_status: str) -> tuple[float, list[str]]:
    """
    Score a job using both title and description.

    The score is not the final legal/OPT decision. It is a ranking signal.
    The CS relevance classifier should also be used before recommending a job.
    """
    text = f"{title} {description}"

    score = 0.0
    reasons: list[str] = []

    if is_excluded_role(title, description):
        return -999.0, ["Excluded role category"]

    cs_relevance_status, cs_relevance_reasons = classify_cs_relevance(title, description)

    if cs_relevance_status == "strong_cs_relevance":
        score += 15
        reasons.append("Strong CS/Math degree relevance (+15)")
    elif cs_relevance_status == "cs_adjacent":
        score += 8
        reasons.append("CS-adjacent role with technical duties (+8)")
    elif cs_relevance_status == "possibly_cs_adjacent":
        score += 3
        reasons.append("Possibly CS-adjacent role; review duties carefully (+3)")
    elif cs_relevance_status == "unclear_but_possible":
        score += 2
        reasons.append("Some CS-related duties found in description (+2)")
    elif cs_relevance_status == "low_cs_relevance":
        score -= 40
        reasons.append("Weak CS/Math degree relevance (-40)")

    for reason in cs_relevance_reasons:
        reasons.append(reason)

    for keyword, points in ROLE_KEYWORDS.items():
        if keyword == "software engineer i":
            if contains_phrase(title, keyword) and not has_senior_title_blocker(title):
                score += points
                reasons.append(f"Role match: {keyword} (+{points})")
            continue

        if contains_phrase(text, keyword):
            score += points
            reasons.append(f"Role match: {keyword} (+{points})")

    for keyword, points in CS_ADJACENT_ROLE_KEYWORDS.items():
        if contains_phrase(text, keyword):
            score += points
            reasons.append(f"CS-adjacent role match: {keyword} (+{points})")

    for keyword, points in TECH_KEYWORDS.items():
        if contains_phrase(text, keyword):
            score += points
            reasons.append(f"Tech/duty match: {keyword} (+{points})")

    for keyword, points in INDUSTRY_KEYWORDS.items():
        if contains_phrase(text, keyword):
            score += points
            reasons.append(f"Industry/context match: {keyword} (+{points})")

    if is_internship(title, description):
        score += 10
        reasons.append("Internship opportunity (+10)")

    if is_new_grad(title, description):
        score += 12
        reasons.append("New grad / early-career opportunity (+12)")

    if (
        has_mid_level_title(title)
        and not is_internship(title, description)
        and not is_new_grad(title, description)
    ):
        score -= 8
        reasons.append("Mid-level title signal (-8)")

    for keyword, points in SENIORITY_PENALTY_KEYWORDS.items():
        if contains_phrase(text, keyword):
            score += points
            reasons.append(f"Seniority penalty: {keyword} ({points})")

    if eligibility_status == "likely_compatible":
        score += 15
        reasons.append("Positive work authorization signal (+15)")

    if eligibility_status == "likely_incompatible":
        score -= 100
        reasons.append("Negative work authorization signal (-100)")

    return score, reasons