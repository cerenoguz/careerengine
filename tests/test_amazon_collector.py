from src.collectors.amazon import (
    _extract_description,
    _extract_location,
    _extract_url,
)


def test_extract_url_builds_absolute_amazon_jobs_url():
    raw_job = {"job_path": "/en/jobs/10502744/software-development-manager"}

    assert (
        _extract_url(raw_job)
        == "https://www.amazon.jobs/en/jobs/10502744/software-development-manager"
    )


def test_extract_url_handles_missing_job_path():
    assert _extract_url({}) == ""


def test_extract_location_prefers_normalized_location():
    raw_job = {
        "normalized_location": "Bellevue, Washington, USA",
        "location": "US, WA, Bellevue",
    }

    assert _extract_location(raw_job) == "Bellevue, Washington, USA"


def test_extract_location_falls_back_to_raw_location():
    raw_job = {"location": "US, WA, Bellevue"}

    assert _extract_location(raw_job) == "US, WA, Bellevue"


def test_extract_location_defaults_to_unknown():
    assert _extract_location({}) == "Unknown"


def test_extract_description_combines_amazon_fields():
    raw_job = {
        "description": "Build satellite network software.",
        "basic_qualifications": "3+ years of experience.",
        "preferred_qualifications": "Experience with distributed systems.",
    }

    description = _extract_description(raw_job)

    assert "Build satellite network software." in description
    assert "3+ years of experience." in description
    assert "Experience with distributed systems." in description


def test_extract_description_labels_basic_and_preferred_qualifications():
    raw_job = {
        "description": "Build things.",
        "basic_qualifications": "- 3+ years of experience",
        "preferred_qualifications": "- 5+ years of server-side experience",
    }

    lines = _extract_description(raw_job).splitlines()

    assert "Basic Qualifications" in lines
    assert "Preferred Qualifications" in lines
    assert lines.index("Basic Qualifications") < lines.index("Preferred Qualifications")


def test_amazon_preferred_years_do_not_count_as_required():
    from src.ranking.level import assess_level
    from src.ranking.text_clean import clean_description

    description = clean_description(_extract_description({
        "description": "Build things.",
        "basic_qualifications": "- 3+ years of non-internship professional software development experience",
        "preferred_qualifications": "- 5+ years of server-side development experience",
    }))

    result = assess_level("SDE II", description)

    assert result.gate is False
    assert result.years_required == 3
    assert result.years_preferred == 5
