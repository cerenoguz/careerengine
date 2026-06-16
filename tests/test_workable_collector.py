from src.collectors.workable import (
    _extract_description,
    _extract_location,
    _extract_raw_jobs,
    _extract_url,
    _normalize_workable_source_url,
)


def test_normalize_workable_careers_page_to_public_api_url():
    assert (
        _normalize_workable_source_url("https://apply.workable.com/huggingface/")
        == "https://www.workable.com/api/accounts/huggingface?details=true"
    )


def test_normalize_workable_public_api_url_is_preserved():
    url = "https://www.workable.com/api/accounts/huggingface?details=true"
    assert _normalize_workable_source_url(url) == url


def test_extract_raw_jobs_from_workable_response():
    data = {
        "jobs": [
            {"title": "Software Engineer"},
            {"title": "Data Engineer"},
        ]
    }

    assert len(_extract_raw_jobs(data)) == 2


def test_extract_location_from_workable_location_dict():
    raw_job = {
        "location": {
            "location_str": "Remote - US",
            "city": "New York",
            "country": "United States",
        }
    }

    assert _extract_location(raw_job) == "Remote - US"


def test_extract_description_combines_workable_fields():
    raw_job = {
        "description": "Build ML tools.",
        "requirements": "Python experience.",
        "benefits": "Remote team.",
    }

    description = _extract_description(raw_job)

    assert "Build ML tools." in description
    assert "Python experience." in description
    assert "Remote team." in description


def test_extract_url_uses_workable_url_when_available():
    raw_job = {
        "url": "https://apply.workable.com/huggingface/j/ABC123/",
        "shortcode": "ABC123",
    }

    assert (
        _extract_url(raw_job, "https://apply.workable.com/huggingface/")
        == "https://apply.workable.com/huggingface/j/ABC123/"
    )
