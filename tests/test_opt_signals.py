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


from src.ranking.opt_signals import sponsorship_stance


@pytest.mark.parametrize(
    "text",
    [
        "Visa sponsorship is not available for this role.",
        "Visa sponsorship is not available.",
        "Sponsorship isn't available at this time.",
        "Sponsorship is not provided.",
        "We are unable to sponsor visas.",
        "We do not offer visa sponsorship.",
        "We cannot sponsor work visas at this time.",
        "No visa sponsorship.",
        "Applicants must be authorized to work in the U.S. without sponsorship.",
        "Will you now or in the future require sponsorship for employment visa status?",
        "We will not sponsor work visas. No sponsorship available.",
    ],
)
def test_negated_sponsorship_sentences_read_as_unavailable(text):
    assert sponsorship_stance(text) == "unavailable"
    status, positive_signals, negative_signals = classify_eligibility(text)

    assert status == "likely_incompatible"
    assert "visa sponsorship" not in positive_signals
    assert "sponsorship not available" in negative_signals


@pytest.mark.parametrize(
    "text",
    [
        "Visa sponsorship is available for qualified candidates.",
        "We offer H-1B visa sponsorship.",
        "Open to sponsorship.",
        "We provide visa sponsorship and relocation assistance.",
        "No matter your background, we offer visa sponsorship.",
        "We are not only open to sponsoring visas but actively support it.",
    ],
)
def test_affirmative_sponsorship_sentences_read_as_available(text):
    assert sponsorship_stance(text) == "available"
    assert classify_eligibility(text)[0] == "likely_compatible"


def test_a_negated_sentence_outweighs_a_positive_one_elsewhere():
    text = "We welcome international students. Visa sponsorship is not available."

    assert sponsorship_stance(text) == "unavailable"
    assert classify_eligibility(text)[0] == "likely_incompatible"


@pytest.mark.parametrize(
    "text",
    [
        "We sponsor several open-source conferences.",
        "Our executive sponsor is the CTO.",
        "Great benefits and career growth.",
    ],
)
def test_sponsorship_unrelated_to_work_authorization_is_ignored(text):
    assert sponsorship_stance(text) == "unclear"


def test_everify_alone_is_not_a_work_authorization_signal():
    assert classify_eligibility("The company participates in E-Verify.")[0] == "unclear"


def test_opt_in_and_opt_out_are_not_opt_work_authorization():
    assert classify_eligibility("Please opt-in to our newsletter or opt out at any time.")[0] == "unclear"
    assert classify_eligibility("Candidates on OPT are welcome to apply.")[0] == "likely_compatible"


def test_a_period_inside_us_does_not_split_a_sentence():
    text = (
        "For US based roles only, please note the Company may not be able to employ candidates "
        "who have United States work authorization related to certain U.S. visa categories, "
        "or support future H-1B sponsorship at this time."
    )

    assert sponsorship_stance(text) == "unavailable"


def test_a_hedged_refusal_after_an_offer_of_sponsorship_reads_as_available():
    text = (
        "Visa sponsorship: We do sponsor visas! However, we aren't able to successfully sponsor "
        "visas for every role and every candidate."
    )

    assert sponsorship_stance(text) == "available"


def test_a_hedged_refusal_alone_is_not_a_flat_no():
    assert sponsorship_stance("We aren't able to sponsor visas for every role.") == "unclear"


@pytest.mark.parametrize(
    "text",
    [
        "Clearance sponsorship will be available.",
        "Review, advise on, and support sponsorship and marketing efforts.",
        "Applicants must be able to work under U.S. export laws without sponsorship for an export license.",
    ],
)
def test_other_kinds_of_sponsorship_are_ignored(text):
    assert sponsorship_stance(text) == "unclear"


def test_requiring_an_existing_right_to_work_means_no_sponsorship():
    assert sponsorship_stance("You must hold an existing right to work in the US. Visa sponsorship is not offered.") == "unavailable"
    assert sponsorship_stance("Applicants must already have a valid authorization to work in the United States; no visa sponsorship.") == "unavailable"
