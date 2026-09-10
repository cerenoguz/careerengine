from src.collectors import netflix
from src.collectors.netflix import (
    _extract_location,
    _fetch_description,
    _format_timestamp,
)


def test_extract_location_uses_location_string():
    assert _extract_location({"location": "USA - Remote"}) == "USA - Remote"


def test_extract_location_joins_locations_list():
    raw_job = {"locations": ["New York, NY", "Los Gatos, CA"]}

    assert _extract_location(raw_job) == "New York, NY, Los Gatos, CA"


def test_extract_location_defaults_to_unknown():
    assert _extract_location({}) == "Unknown"


def test_format_timestamp_converts_unix_seconds_to_iso_date():
    assert _format_timestamp(1721692800) == "2024-07-23"


def test_format_timestamp_handles_missing_value():
    assert _format_timestamp(None) is None


def test_format_timestamp_handles_invalid_value():
    assert _format_timestamp("not-a-timestamp") is None


def test_fetch_description_prefers_list_description():
    raw_job = {"job_description": "Already present in list response."}

    assert _fetch_description(raw_job, headers={}) == "Already present in list response."


def test_fetch_description_falls_back_to_detail_call(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {"job_description": "Full description from detail call."}

    def fake_get(url, headers=None, timeout=None):
        assert "12345" in url
        return FakeResponse()

    monkeypatch.setattr(netflix.requests, "get", fake_get)

    raw_job = {"id": 12345, "job_description": ""}

    assert (
        _fetch_description(raw_job, headers={})
        == "Full description from detail call."
    )


def test_fetch_description_returns_empty_when_no_id():
    assert _fetch_description({"job_description": ""}, headers={}) == ""
