import pytest

from src.ranking.level import LevelAssessment
from src.ranking.match_score import (
    BANDS,
    WEIGHTS,
    authorization_component,
    band_for,
    compute_match,
    normalise_semantic,
)
from src.ranking.role_fit import RoleFit
from src.ranking.skills import SkillMatch


def match(level=1.0, role=1.0, skills=1.0, cosine=0.52, status="likely_compatible", sponsorship="available"):
    return compute_match(
        level=LevelAssessment(level_score=level),
        role=RoleFit(role, "software engineer"),
        skills=SkillMatch(score=skills),
        semantic_cosine=cosine,
        eligibility_status=status,
        sponsorship_language=sponsorship,
    )


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_perfect_components_score_one_hundred():
    assert match().score == pytest.approx(100.0)


def test_all_zero_components_score_zero():
    result = match(level=0, role=0, skills=0, cosine=0.0, status="likely_incompatible", sponsorship="unclear")

    assert result.score == pytest.approx(0.0)


def test_score_is_always_between_zero_and_one_hundred():
    assert 0.0 <= match(cosine=5.0).score <= 100.0
    assert 0.0 <= match(cosine=-5.0).score <= 100.0


def test_each_component_moves_the_score_in_the_right_direction():
    base = match(level=0.5, role=0.5, skills=0.5, cosine=0.3, status="unclear", sponsorship="unclear").score

    assert match(level=0.9, role=0.5, skills=0.5, cosine=0.3, status="unclear", sponsorship="unclear").score > base
    assert match(level=0.5, role=0.9, skills=0.5, cosine=0.3, status="unclear", sponsorship="unclear").score > base
    assert match(level=0.5, role=0.5, skills=0.9, cosine=0.3, status="unclear", sponsorship="unclear").score > base
    assert match(level=0.5, role=0.5, skills=0.5, cosine=0.5, status="unclear", sponsorship="unclear").score > base
    assert match(level=0.5, role=0.5, skills=0.5, cosine=0.3, status="likely_compatible", sponsorship="available").score > base


def test_level_is_the_heaviest_component():
    assert WEIGHTS["level"] == max(WEIGHTS.values())


def test_semantic_is_neutral_when_unavailable():
    unavailable = compute_match(
        level=LevelAssessment(level_score=0.5), role=RoleFit(0.5, "x"), skills=SkillMatch(score=0.5),
        semantic_cosine=None, eligibility_status="unclear", sponsorship_language="unclear",
    )

    assert unavailable.components["semantic"] == 0.5
    assert not any(reason.startswith("Profile similarity") for reason in unavailable.reasons)


def test_semantic_anchors_stretch_the_narrow_cosine_range():
    assert normalise_semantic(0.0) == 0.0
    assert normalise_semantic(1.0) == 1.0
    assert 0.0 < normalise_semantic(0.3) < 1.0


def test_authorization_component_ordering():
    assert (
        authorization_component("unclear", "available")
        > authorization_component("likely_compatible", "unclear")
        > authorization_component("unclear", "unclear")
        > authorization_component("unclear", "unavailable")
        >= authorization_component("likely_incompatible", "unclear")
    )


def test_bands_are_ordered_and_cover_the_range():
    minimums = [minimum for minimum, _ in BANDS]

    assert minimums == sorted(minimums, reverse=True)
    assert minimums[-1] == 0.0
    assert band_for(100) == "excellent"
    assert band_for(0) == BANDS[-1][1]


def test_reasons_explain_the_score():
    result = match()

    assert any(reason.startswith("Role:") for reason in result.reasons)
    assert "Sponsorship available" in result.reasons
