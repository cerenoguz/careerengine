import pytest

from src.ranking.level import assess_level, extract_years_requirement


def years(text: str):
    return extract_years_requirement(text)


def test_largest_required_mention_wins_over_a_small_tooling_mention():
    result = years("Requirements\n- 5+ years of backend engineering experience\n- 1+ year of experience with Kubernetes")

    assert result.required == 5


def test_ranges_use_their_lower_bound():
    assert years("Requirements\n- 2-5 years of software engineering experience").required == 2


def test_decimal_years_round_up():
    assert years("What we look for\n- You have a total of 1.5+ years of experience as a software engineer.").required == 2


def test_preferred_years_do_not_count_as_required():
    result = years("Requirements\n- Python\nPreferred Qualifications\n- 6+ years of experience with distributed systems")

    assert result.required is None
    assert result.preferred == 6


def test_a_preference_about_another_skill_does_not_demote_the_years():
    line = "- 4+ years building production frontend; experience with a design system is a plus"

    assert years("What we're looking for\n" + line).required == 4


def test_ideally_clause_after_the_years_does_not_make_them_optional():
    line = "- Have 6+ years of experience building production software, ideally full-stack"

    assert years("You may be a good fit if you:\n" + line).required == 6


def test_company_history_is_not_a_years_requirement():
    assert years("Requirements\n- Python\nFounded over 20 years ago, we have been building software for 15 years.").required is None


def test_doctoral_alternative_is_ignored_for_a_bachelors_candidate():
    line = "- A minimum of 8 years of related experience with a Bachelor's degree; or 6 years and a Master's degree; or a PhD with 3 years experience"

    assert years("Requirements\n" + line).required == 6


@pytest.mark.parametrize(
    "title",
    ["Senior Software Engineer", "Sr. Engineer", "Staff Engineer", "Software Engineer III", "Software Engineer 4", "Software Engineer (L5)", "Tech Lead", "Principal Engineer"],
)
def test_senior_titles_are_gated_even_with_junior_language(title):
    result = assess_level(title, "Recent graduates are encouraged to apply. 0-2 years of experience welcome.")

    assert result.gate is True
    assert result.level == "senior"
    assert result.level_score == 0.0


def test_more_than_three_required_years_is_gated():
    result = assess_level("Software Engineer", "Requirements\n- 4+ years of professional software experience")

    assert result.gate is True
    assert "4+" in result.gate_reason


def test_three_required_years_is_allowed_but_scores_low():
    result = assess_level("Software Engineer", "Requirements\n- 3+ years of professional software experience")

    assert result.gate is False
    assert result.level == "mid"
    assert result.level_score <= 0.3


@pytest.mark.parametrize(
    "title",
    ["New Grad Software Engineer", "Software Engineer I", "Associate Software Engineer", "Junior Backend Developer", "Software Engineer, Early Career"],
)
def test_entry_titles_score_full_marks(title):
    result = assess_level(title, "Build backend services.")

    assert result.gate is False
    assert result.level == "entry"
    assert result.level_score == 1.0


def test_level_ii_is_junior_mid_not_entry():
    result = assess_level("Software Engineer II", "Build backend services.")

    assert result.level == "junior_mid"
    assert 0.5 <= result.level_score < 1.0


def test_unlabelled_role_scores_neutral():
    result = assess_level("Software Engineer", "Build backend services.")

    assert result.level == "unknown"
    assert result.level_score == 0.5


def test_senior_scope_language_lowers_an_unlabelled_role():
    plain = assess_level("Software Engineer", "Build backend services.")
    scoped = assess_level("Software Engineer", "You will mentor junior engineers and set the technical direction.")

    assert scoped.level_score < plain.level_score


def test_prefers_many_years_without_a_minimum_lowers_the_score():
    result = assess_level("Software Engineer", "Requirements\n- Python\nPreferred Qualifications\n- 5+ years of experience")

    assert result.gate is False
    assert result.level_score <= 0.3


def test_member_of_technical_staff_is_not_senior():
    assert assess_level("Member of Technical Staff", "Build AI products.").gate is False


def test_phd_title_is_gated():
    assert assess_level("PhD University Grad Machine Learning Engineer", "").gate is True
