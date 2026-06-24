from src.ranking.profile_fit import calculate_profile_fit_score


def test_new_grad_technical_role_scores_strongly():
    result = calculate_profile_fit_score(
        semantic_similarity=0.65,
        description_similarity=0.20,
        cs_relevance_status="strong_cs_relevance",
        is_internship=False,
        is_new_grad=True,
        required_years_min=0,
        years_requirement_type="required",
        title_description_conflict=False,
    )

    assert result.score >= 70
    assert result.band == "strong"


def test_three_year_required_role_is_demoted_but_not_zeroed():
    result = calculate_profile_fit_score(
        semantic_similarity=0.55,
        description_similarity=0.15,
        cs_relevance_status="strong_cs_relevance",
        is_internship=False,
        is_new_grad=False,
        required_years_min=3,
        years_requirement_type="required",
        title_description_conflict=False,
    )

    assert 50 <= result.score < 70
    assert result.band in {"moderate", "lower_priority"}


def test_l2_role_with_junior_description_receives_conflict_credit():
    result = calculate_profile_fit_score(
        semantic_similarity=0.60,
        description_similarity=0.15,
        cs_relevance_status="strong_cs_relevance",
        is_internship=False,
        is_new_grad=True,
        required_years_min=1,
        years_requirement_type="required",
        title_description_conflict=True,
    )

    assert result.score >= 70
    assert "Junior-friendly description overrides senior-looking title (+8)" in result.reasons


def test_weak_nontechnical_role_stays_below_threshold():
    result = calculate_profile_fit_score(
        semantic_similarity=0.20,
        description_similarity=0.02,
        cs_relevance_status="low_cs_relevance",
        is_internship=False,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
    )

    assert result.score < 50
    assert result.band == "weak"


def test_profile_fit_result_exposes_score_band_and_reasons():
    result = calculate_profile_fit_score(
        semantic_similarity=0.60,
        description_similarity=0.10,
        cs_relevance_status="strong_cs_relevance",
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
        cs_relevance_status="strong_cs_relevance",
        is_internship=False,
        is_new_grad=False,
        required_years_min=None,
        years_requirement_type="unclear",
        title_description_conflict=False,
        senior_title_signal=True,
    )

    assert result.score < 60
    assert "Senior-title signal without junior evidence (-18)" in result.reasons


from src.ranking.profile_fit import profile_fit_ranking_adjustment


def test_live_ranking_adjustment_bands():
    assert profile_fit_ranking_adjustment(72) == (
        25.0,
        "Strong AI profile fit (+25)",
    )
    assert profile_fit_ranking_adjustment(64) == (
        12.0,
        "Moderate AI profile fit (+12)",
    )
    assert profile_fit_ranking_adjustment(55) == (
        0.0,
        "Lower-priority AI profile fit (no adjustment)",
    )
    assert profile_fit_ranking_adjustment(42) == (
        -12.0,
        "Lower-confidence AI profile fit (-12)",
    )
