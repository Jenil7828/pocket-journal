import pytest


def sample_entry_payload():
    return {
        "entry_text":"I felt genuinely happy and excited today. Everything went well and I was in a great mood.",
        "timestamp": "2025-01-01T12:00:00Z"
    }


def test_process_entry_success(api_client):
    r = api_client("POST", "/process_entry", json=sample_entry_payload())
    assert 200 <= r.status_code < 300, f"Expected success, got {r.status_code}: {r.text}"


def test_process_entry_missing_auth(api_client):
    r = api_client("POST", "/process_entry", json=sample_entry_payload(), use_auth=False)
    assert r.status_code == 401


def test_process_entry_invalid_input(api_client):
    # Send malformed payload
    r = api_client("POST", "/process_entry", json={})
    # Expect client error or handled gracefully
    assert r.status_code >= 400
