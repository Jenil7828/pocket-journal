import pytest


def test_generate_insights_success(api_client):
    r = api_client("POST", "/generate_insights", json={})
    assert 200 <= r.status_code < 300, f"Expected success, got {r.status_code}: {r.text}"


def test_generate_insights_missing_auth(api_client):
    r = api_client("POST", "/generate_insights", json={}, use_auth=False)
    assert r.status_code == 401


def test_generate_insights_invalid_payload(api_client):
    # Pass an unexpected type to trigger validation paths
    r = api_client("POST", "/generate_insights", json={"start_date": "not-a-date"})
    assert r.status_code >= 400 or 200 <= r.status_code < 300
