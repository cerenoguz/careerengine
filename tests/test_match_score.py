import pytest

from src.ranking.match_score import (
    BANDS,
    WEIGHTS,
    band_for,
    compute_match,
    normalise_semantic,
)
from src.ranking.role_fit import RoleFit
from src.ranking.skills import SkillMatch


def match(role=1.0, skills=1.0, cosine=0.58):
    return compute_match(
        role=RoleFit(role, "software engineer"),
        skills=SkillMatch(score=skills),
        semantic_cosine=cosine,
    )


def test_weights_sum_to_one():
    assert sum(WEIGHTS.values()) == pytest.approx(1.0)


def test_score_measures_experience_fit_only():
    """Level and work authorization are gates and dashboard indicators, never
    components of the number."""
    assert set(WEIGHTS) == {"skills", "semantic", "role"}


def test_perfect_components_score_one_hundred():
    assert match().score == pytest.approx(100.0)


def test_all_zero_components_score_zero():
    assert match(role=0, skills=0, cosine=0.0).score == pytest.approx(0.0)


def test_score_is_always_between_zero_and_one_hundred():
    assert 0.0 <= match(cosine=5.0).score <= 100.0
    assert 0.0 <= match(cosine=-5.0).score <= 100.0


def test_each_component_moves_the_score_in_the_right_direction():
    base = match(role=0.5, skills=0.5, cosine=0.4).score

    assert match(role=0.9, skills=0.5, cosine=0.4).score > base
    assert match(role=0.5, skills=0.9, cosine=0.4).score > base
    assert match(role=0.5, skills=0.5, cosine=0.5).score > base


def test_skills_and_semantic_outweigh_the_job_title():
    assert WEIGHTS["role"] < WEIGHTS["skills"]
    assert WEIGHTS["role"] < WEIGHTS["semantic"]


def test_semantic_is_neutral_when_unavailable():
    unavailable = compute_match(
        role=RoleFit(0.5, "x"), skills=SkillMatch(score=0.5), semantic_cosine=None,
    )

    assert unavailable.components["semantic"] == 0.5
    assert not any(reason.startswith("Similarity") for reason in unavailable.reasons)


def test_semantic_anchors_stretch_the_observed_cosine_range():
    assert normalise_semantic(0.0) == 0.0
    assert normalise_semantic(1.0) == 1.0
    assert 0.0 < normalise_semantic(0.40) < 1.0
    assert normalise_semantic(0.30) < normalise_semantic(0.40) < normalise_semantic(0.50)


def test_bands_are_ordered_and_cover_the_range():
    minimums = [minimum for minimum, _ in BANDS]

    assert minimums == sorted(minimums, reverse=True)
    assert minimums[-1] == 0.0
    assert band_for(100) == "excellent"
    assert band_for(0) == BANDS[-1][1]


def test_reasons_describe_the_experience_match_and_nothing_about_level_or_visa():
    result = compute_match(
        role=RoleFit(1.0, "backend"),
        skills=SkillMatch(score=0.8, matched=["python", "sql"]),
        semantic_cosine=0.55,
    )

    assert "Matching skills: Python, SQL" in result.reasons
    assert "Similarity to your experience: High" in result.reasons
    assert not any("ntry" in reason or "ponsor" in reason for reason in result.reasons)
