from src.ranking.rule_score import is_internship, is_new_grad


DESCRIPTION_WITH_PROGRAM_REFERENCES = """
This posting is for an immediate full-time hire. For internship opportunities
or new grad opportunities, please check our university recruiting page.
"""


def test_internship_detection_is_title_based():
    assert (
        is_internship(
            "Software Engineer I (Backend)",
            DESCRIPTION_WITH_PROGRAM_REFERENCES,
        )
        is False
    )

    assert (
        is_internship(
            "Software Engineering Intern (Summer 2026)",
            "",
        )
        is True
    )


def test_new_grad_detection_does_not_bleed_from_description():
    assert (
        is_new_grad(
            "Software Engineer II (Backend, Platform)",
            DESCRIPTION_WITH_PROGRAM_REFERENCES,
        )
        is False
    )

    assert (
        is_new_grad(
            "New Grad Software Engineer",
            "",
        )
        is True
    )


def test_software_engineer_i_counts_as_entry_level_signal():
    assert (
        is_new_grad(
            "Software Engineer I (Backend)",
            DESCRIPTION_WITH_PROGRAM_REFERENCES,
        )
        is True
    )
