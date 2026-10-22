import pytest

from src.ranking.opt_signals import classify_eligibility


@pytest.mark.parametrize(
    "text",
    [
        "We optimize data pipelines and adopt new tooling.",
        "Evaluate the options and optional features.",
        "Drive adoption of the new platform.",
        "Experience supporting military programs.",
    ],
)
def test_signals_do_not_match_inside_other_words(text):
    status, positive_signals, negative_signals = classify_eligibility(text)

    assert status == "unclear"
    assert positive_signals == []
    assert negative_signals == []


@pytest.mark.parametrize(
    "text",
    [
        "Candidates on OPT are welcome to apply.",
        "We support STEM OPT and CPT.",
        "F-1 students are encouraged to apply.",
        "We offer H-1B visa sponsorship.",
        "International students are welcome.",
    ],
)
def test_real_positive_signals_are_still_detected(text):
    status, positive_signals, _ = classify_eligibility(text)

    assert status == "likely_compatible"
    assert positive_signals


@pytest.mark.parametrize(
    "text",
    [
        "This role is subject to ITAR.",
        "We will not sponsor work visas. No sponsorship available.",
        "U.S. citizen required.",
    ],
)
def test_real_negative_signals_are_still_detected(text):
    status, _, negative_signals = classify_eligibility(text)

    assert status == "likely_incompatible"
    assert negative_signals
