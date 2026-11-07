from __future__ import annotations

from src.ranking.match_score import BANDS


def classify_dashboard_bucket(match_score: float | None) -> str:
    """
    Dashboard buckets from the unified 0-100 match score.

    Eligibility (seniority, internships, work-authorization restrictions,
    location) is enforced before ranking, so every job that reaches the
    dashboard is eligible; the bucket only reflects how good the match is.

      apply_now: strong or excellent match
      review:    good match, worth a look
      archive:   fair match, lower priority
    """
    score = float(match_score or 0)
    thresholds = {name: minimum for minimum, name in BANDS}

    if score >= thresholds["strong"]:
        return "apply_now"

    if score >= thresholds["good"]:
        return "review"

    return "archive"
