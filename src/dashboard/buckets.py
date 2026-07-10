from __future__ import annotations


SENIORITY_WORDS = (
    "senior",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "architect",
)

JUNIOR_FRIENDLY_WORDS = (
    "new grad",
    "new graduate",
    "recent grad",
    "recent graduate",
    "early career",
    "entry level",
    "university grad",
    "university graduate",
    "intern",
    "internship",
    "co-op",
    "0-1 years",
    "0-2 years",
    "1+ years",
)


def _lower(value: object) -> str:
    return str(value or "").lower()


def has_senior_title(title: str) -> bool:
    title_l = _lower(title)
    return any(word in title_l for word in SENIORITY_WORDS)


def has_junior_signal(title: str, description: str = "", opportunity_type: str = "") -> bool:
    combined = f"{title} {description} {opportunity_type}".lower()
    return any(word in combined for word in JUNIOR_FRIENDLY_WORDS)


def is_hard_excluded(
    work_auth_review: str = "",
    experience_fit: str = "",
    reason: str = "",
) -> bool:
    text = f"{work_auth_review} {experience_fit} {reason}".lower()

    hard_no_terms = (
        "citizen only",
        "u.s. citizen",
        "us citizen",
        "permanent resident only",
        "green card only",
        "active clearance",
        "security clearance required",
        "no opt",
        "no f-1",
        "no f1",
        "5+ years required",
        "requires 5+ years",
        "outside u.s.",
        "outside us",
    )

    return any(term in text for term in hard_no_terms)


def classify_dashboard_bucket(
    *,
    title: str,
    description: str = "",
    ai_profile_fit: float | None,
    work_auth_review: str = "",
    opportunity_type: str = "",
    experience_fit: str = "",
    reason: str = "",
) -> str:
    """
    Buckets:
      apply_now: realistic recommendation
      review: possibly relevant but uncertain
      archive: technically related but not worth main attention
      exclude: hard no
    """

    fit = float(ai_profile_fit or 0)
    senior_title = has_senior_title(title)
    junior_signal = has_junior_signal(title, description, opportunity_type)

    if is_hard_excluded(work_auth_review, experience_fit, reason):
        return "exclude"

    if senior_title and not junior_signal:
        return "archive"

    if fit >= 70:
        return "apply_now"

    if 60 <= fit < 70:
        return "review"

    if "unclear" in _lower(work_auth_review) or "needs review" in _lower(work_auth_review):
        return "review"

    return "archive"
