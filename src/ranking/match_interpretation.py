from src.ranking.match_score import band_for


_LABELS = {
    "excellent": "Excellent match",
    "strong": "Strong match",
    "good": "Good match",
    "fair": "Fair match",
}


def get_match_strength_label(score: float) -> str:
    """Human-readable label for a 0-100 match score."""
    return _LABELS[band_for(score)]
