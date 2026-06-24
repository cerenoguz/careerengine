from src.ranking.structured_evaluator import evaluate_job_description


def test_new_grad_l2_role_remains_non_hard_no():
    result = evaluate_job_description(
        "Software Engineer (L2)",
        (
            "Recent graduates are encouraged to apply. "
            "Candidates with 0-2 years of experience are welcome."
        ),
    )

    assert result.hard_no is False
    assert result.new_grad_signal == "yes"
    assert result.required_years_min == 0
    assert result.title_description_conflict is True
    assert result.experience_fit == "strong"


def test_required_five_years_is_hard_no():
    result = evaluate_job_description(
        "Backend Engineer",
        "Must have 5+ years of relevant software engineering experience.",
    )

    assert result.hard_no is True
    assert result.required_years_min == 5
    assert result.years_requirement_type == "required"


def test_preferred_five_years_is_not_hard_no():
    result = evaluate_job_description(
        "Backend Engineer",
        "5+ years of backend experience preferred. Python and SQL required.",
    )

    assert result.hard_no is False
    assert result.required_years_min == 5
    assert result.years_requirement_type == "preferred"


def test_three_year_requirement_is_demoted_not_excluded():
    result = evaluate_job_description(
        "Software Engineer II",
        "Minimum of 3 years of software engineering experience required.",
    )

    assert result.hard_no is False
    assert result.required_years_min == 3
    assert result.experience_fit == "possible"


def test_citizenship_requirement_is_hard_no():
    result = evaluate_job_description(
        "Software Engineer",
        "U.S. citizenship required. Active security clearance required.",
    )

    assert result.hard_no is True
    assert result.citizenship_required == "yes"
    assert result.clearance_required == "yes"


def test_no_sponsorship_alone_is_not_hard_no():
    result = evaluate_job_description(
        "Software Engineer",
        "We are unable to provide visa sponsorship for this role.",
    )

    assert result.hard_no is False
    assert result.sponsorship_language == "unavailable"


def test_generic_internship_reference_does_not_reclassify_full_time_role():
    result = evaluate_job_description(
        "Software Engineer I",
        (
            "This is a full-time engineering position. "
            "Our company also offers internship programs each summer."
        ),
    )

    assert result.internship_signal == "no"


def test_two_to_four_year_range_is_possible_not_strong_entry_level_fit():
    result = evaluate_job_description(
        "Software Engineer II",
        "2-4 years of backend software development experience preferred.",
    )

    assert result.required_years_min == 2
    assert result.required_years_max == 4
    assert result.experience_fit == "possible"
