from src.ranking.profile_fit import (
    calculate_profile_fit_score,
    profile_fit_ranking_adjustment,
)


def test_new_grad_technical_role_scores_strongly():
    result = calculate_profile_fit_score(
        semantic_similarity=0.85,
        description_similarity=0.30,
        is_internship=False,
        is_new_grad=True,
        required_years_min=0,
        years_requirement_type="required",
        title_description_conflict=False,
    )

    assert result.score >= 45
    assert result.band == "strong"


def test_three_year_required_role_is_demoted_but_not_zeroed():
    result = calculate_profile_fit_score(
        semantic_similarity=0.75,
        description_similarity=0.20,
        is_internship=False,
        is_new_grad=True,
        required_years_min=3,
        years_requirement_type="required",
        title_description_conflict=False,
    )

    assert 0 < result.score < 45
    assert result.band in {"moderate", "lower_priority"}


def test_l2_role_with_junior_description_receives_conflict_credit():
    result = calculate_profile_fit_score(
        semantic_similarity=0.70,
        description_similarity=0.15,
        is_internship=False,
        is_new_grad=True,
        required_years_min=1,
        years_requirement_type="required",
        title_description_conflict=True,
    )

    assert result.score >= 45
    assert "Junior-friendly description overrides senior-looking title (+8)" in result.reasons


def test_weak_nontechnical_role_stays_below_threshold():
    result = calculate_profile_fit_score(
        semantic_similarity=0.20,
        description_similarity=0.02,
        is_internship=False,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
    )

    assert result.score < 35
    assert result.band == "weak"


def test_profile_fit_result_exposes_score_band_and_reasons():
    result = calculate_profile_fit_score(
        semantic_similarity=0.60,
        description_similarity=0.10,
        is_internship=True,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
    )

    assert result.score > 0
    assert result.band in {"strong", "moderate", "lower_priority", "weak"}
    assert result.reasons


def test_senior_title_is_demoted_without_junior_evidence():
    result = calculate_profile_fit_score(
        semantic_similarity=0.60,
        description_similarity=0.10,
        is_internship=False,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
        senior_title_signal=True,
    )

    assert result.score < 35
    assert "Senior-title signal without junior evidence (-18)" in result.reasons


def test_profile_fit_score_does_not_double_count_cs_relevance():
    """
    calculate_profile_fit_score no longer accepts cs_relevance_status: that
    signal is already scored once in rule_score.score_job() and used again to
    gate admission via is_recommendable_job(), so adding it a third time here
    would double-count it in the final ranking. A weak-semantic, weak-wording,
    no-eligibility-bonus job should score near zero -- there is no hidden
    domain-relevance floor propping the score up.
    """
    result = calculate_profile_fit_score(
        semantic_similarity=0.0,
        description_similarity=0.0,
        is_internship=False,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
    )

    assert result.score == 0.0
    assert result.band == "weak"


def test_live_ranking_adjustment_bands():
    assert profile_fit_ranking_adjustment(50) == (
        25.0,
        "Strong AI profile fit (+25)",
    )
    assert profile_fit_ranking_adjustment(42) == (
        12.0,
        "Moderate AI profile fit (+12)",
    )
    assert profile_fit_ranking_adjustment(37) == (
        0.0,
        "Lower-priority AI profile fit (no adjustment)",
    )
    assert profile_fit_ranking_adjustment(20) == (
        -12.0,
        "Lower-confidence AI profile fit (-12)",
    )


def test_ranking_adjustment_bands_match_classify_profile_fit_thresholds():
    """
    profile_fit_ranking_adjustment derives its bands from
    classify_profile_fit() rather than duplicating thresholds, so the two
    can never drift out of sync the way the old hardcoded 70/60/50 pairs
    could.
    """
    from src.ranking.profile_fit import classify_profile_fit

    for score in [0, 20, 34, 35, 39, 40, 44, 45, 60, 100]:
        band = classify_profile_fit(score)
        _, reason = profile_fit_ranking_adjustment(score)

        if band == "strong":
            assert "+25" in reason
        elif band == "moderate":
            assert "+12" in reason
        elif band == "lower_priority":
            assert "no adjustment" in reason
        else:
            assert "-12" in reason
