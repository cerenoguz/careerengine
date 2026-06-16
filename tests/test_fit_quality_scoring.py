from src.ranking.rule_score import has_mid_level_title, score_job


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
    assert "Mid-level title signal (-8)" in reasons


def test_l2_roles_receive_small_fit_penalty():
    score, reasons = score_job(
        "Software Engineer (L2)",
        DESCRIPTION,
        "likely_compatible",
    )

    assert score > 0
    assert "Mid-level title signal (-8)" in reasons


def test_new_grad_role_does_not_receive_mid_level_penalty():
    _, reasons = score_job(
        "New Grad Software Engineer",
        DESCRIPTION,
        "likely_compatible",
    )

    assert "Mid-level title signal (-8)" not in reasons
