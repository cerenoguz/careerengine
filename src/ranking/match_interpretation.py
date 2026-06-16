def get_match_strength_label(score: float) -> str:
    """
    Convert CareerEngine's point-based score into a human-readable label.

    The score is not a percentage. It is an additive ranking score.
    """
    if score >= 70:
        return "Excellent match"

    if score >= 55:
        return "Strong match"

    if score >= 45:
        return "Relevant / worth checking"

    return "Lower-priority match"


def get_description_similarity_label(description_similarity: float) -> str:
    """
    Convert lexical description similarity into a human-readable label.

    This is based on wording overlap between candidate_profile.txt and the job
    description. It is not a full semantic AI match.
    """
    if description_similarity >= 0.120:
        return "Strong wording overlap"

    if description_similarity >= 0.070:
        return "Moderate wording overlap"

    if description_similarity >= 0.040:
        return "Low wording overlap"

    return "Very low wording overlap"
