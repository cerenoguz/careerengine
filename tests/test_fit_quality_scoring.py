from src.ranking.rule_score import has_mid_level_title, has_unrealistic_seniority, is_new_grad, score_job


DESCRIPTION = """
Build backend services using Python, Java, SQL, APIs, databases, cloud systems,
and distributed systems.
"""


def test_mid_level_title_detection_for_level_two_roles():
    assert has_mid_level_title("Software Engineer II (Backend, Platform)") is True
    assert has_mid_level_title("Software Engineer (L2)") is True
    assert has_mid_level_title("Software Engineer I (Backend)") is False
    assert has_mid_level_title("New Grad Software Engineer") is False


def test_level_two_roles_receive_small_fit_penalty():
    score, reasons = score_job(
        "Software Engineer II (Backend, Platform)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert score > 0
    assert "Mid-level title signal (-12)" in reasons


def test_l2_roles_receive_small_fit_penalty():
    score, reasons = score_job(
        "Software Engineer (L2)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert score > 0
    assert "Mid-level title signal (-12)" in reasons


def test_new_grad_role_does_not_receive_mid_level_penalty():
    _, reasons = score_job(
        "New Grad Software Engineer",
        DESCRIPTION,
        "likely_compatible",
    )

    assert "Mid-level title signal (-12)" not in reasons


def test_software_engineering_intern_gets_explicit_role_boost():
    score, reasons = score_job(
        "Software Engineering Intern (Summer 2026)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert score > 0
    assert "Role match: software engineering intern (+12)" in reasons
    assert "Internship opportunity (+10)" in reasons


def test_new_grad_software_engineer_gets_explicit_role_boost():
    score, reasons = score_job(
        "New Grad Software Engineer",
        DESCRIPTION,
        "unclear",
    )

    assert score > 0
    assert "Role match: new grad software engineer (+14)" in reasons
    assert "New grad / early-career opportunity (+12)" in reasons


def test_principal_software_engineer_i_is_not_new_grad():
    title = "Principal Software Engineer I - Snowhouse Foundation"

    assert is_new_grad(title, DESCRIPTION) is False
    assert has_unrealistic_seniority(title, DESCRIPTION) is True


def test_principal_software_engineer_i_does_not_get_software_engineer_i_boost():
    _, reasons = score_job(
        "Principal Software Engineer I - Snowhouse Foundation",
        DESCRIPTION,
        "unclear",
    )

    assert "Role match: software engineer i (+12)" not in reasons
    assert "New grad / early-career opportunity (+12)" not in reasons


def test_explicit_early_career_role_receives_ranking_priority():
    _, reasons = score_job(
        "Software Engineer I (Quality)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert "Early-career ranking priority (+10)" in reasons


def test_software_engineer_i_outranks_close_level_two_role():
    software_engineer_i_score, _ = score_job(
        "Software Engineer I (Quality)",
        DESCRIPTION,
        "likely_compatible",
    )

    software_engineer_ii_score, _ = score_job(
        "Software Engineer II (Backend, Platform)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert software_engineer_i_score > software_engineer_ii_score


def test_principal_software_engineer_i_does_not_receive_early_career_priority():
    _, reasons = score_job(
        "Principal Software Engineer I - Snowhouse Foundation",
        DESCRIPTION,
        "unclear",
    )

    assert "Early-career ranking priority (+10)" not in reasons

def test_internship_outranks_skill_richer_level_two_role():
    internship_score, _ = score_job(
        "Software Engineering Intern (Summer 2026)",
        "Build services using Python, APIs, and cloud systems.",
        "likely_compatible",
    )

    level_two_score, _ = score_job(
        "Software Engineer (L2)",
        (
            "Build backend services using Python, Java, SQL, APIs, databases, "
            "cloud systems, and distributed systems."
        ),
        "likely_compatible",
    )

    assert internship_score > level_two_score


def test_new_grad_outranks_skill_richer_level_two_role():
    new_grad_score, _ = score_job(
        "New Grad Software Engineer",
        "Build services using Python, APIs, and cloud systems.",
        "likely_compatible",
    )

    level_two_score, _ = score_job(
        "Software Engineer (L2)",
        (
            "Build backend services using Python, Java, SQL, APIs, databases, "
            "cloud systems, and distributed systems."
        ),
        "likely_compatible",
    )

    assert new_grad_score > level_two_score

