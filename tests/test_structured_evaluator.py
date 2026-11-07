from src.ranking.structured_evaluator import evaluate_job_description


def test_new_grad_language_in_description_sets_new_grad_signal():
    result = evaluate_job_description(
        "Software Engineer (L2)",
        "Recent graduates are encouraged to apply. Candidates with 0-2 years are welcome.",
    )

    assert result.hard_no is False
    assert result.new_grad_signal == "yes"


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


def test_sponsorship_available_is_detected():
    result = evaluate_job_description(
        "Software Engineer",
        "Visa sponsorship available for qualified candidates.",
    )

    assert result.sponsorship_language == "available"


def test_years_of_experience_no_longer_cause_a_hard_no_here():
    """Seniority is decided by src.ranking.level, not the evaluator."""
    result = evaluate_job_description(
        "Backend Engineer",
        "Must have 5+ years of relevant software engineering experience.",
    )

    assert result.hard_no is False


def test_generic_internship_reference_does_not_reclassify_full_time_role():
    result = evaluate_job_description(
        "Software Engineer I",
        (
            "This is a full-time engineering position. "
            "Our company also offers internship programs each summer."
        ),
    )

    assert result.internship_signal == "no"


def test_visa_sponsorship_not_available_is_detected_as_unavailable():
    result = evaluate_job_description(
        "Software Engineer",
        "Visa sponsorship is not available for this role.",
    )

    assert result.sponsorship_language == "unavailable"
    assert result.hard_no is False
