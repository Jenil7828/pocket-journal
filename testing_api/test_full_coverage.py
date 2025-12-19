import pytest


def test_health(api_client):
    r = api_client("GET", "/health", expected_status=200, expected_desc="200 OK")
    assert r.status_code == 200


def test_process_entry_endpoints(api_client):
    payload = {"entry_text": "Automated test entry.", "timestamp": "2025-01-01T00:00:00Z"}
    r = api_client("POST", "/process_entry", json=payload, expected_status=200, expected_desc="Create entry and analysis")
    assert 200 <= r.status_code < 300

    # try GET entries (filtered)
    r2 = api_client("GET", "/entries", expected_status=200, expected_desc="List entries or empty list")
    assert r2.status_code >= 200


def test_entry_crud(api_client):
    # Create
    payload = {"entry_text": "CRUD test entry.", "timestamp": "2025-01-01T00:00:00Z"}
    r = api_client("POST", "/process_entry", json=payload, expected_status=200, expected_desc="Create entry")
    assert 200 <= r.status_code < 300
    try:
        data = r.json()
        entry_id = data.get("id") or data.get("entry_id") or data.get("document_id")
    except Exception:
        entry_id = None

    if entry_id:
        # Get single
        api_client("GET", f"/entries/{entry_id}", expected_status=200, expected_desc="Get created entry")
        # Update
        api_client("PUT", f"/entries/{entry_id}", json={"entry_text": "Updated by test"}, expected_status=200, expected_desc="Update entry")
        # Reanalyze
        api_client("POST", f"/entries/{entry_id}/reanalyze", expected_status=200, expected_desc="Reanalyze entry")
        # Delete
        api_client("DELETE", f"/entries/{entry_id}", expected_status=200, expected_desc="Delete entry")


def test_insights_endpoints(api_client):
    # generate_insights
    api_client("POST", "/generate_insights", json={}, expected_status=200, expected_desc="Generate insights (may be cached)")
    # list insights
    api_client("GET", "/insights", expected_status=200, expected_desc="List insights")


def test_media_and_search(api_client):
    api_client("GET", "/movie/recommend", expected_status=200, expected_desc="Recommend movies for user")
    api_client("GET", "/api/recommend?mood=happy", expected_status=200, expected_desc="Recommend movies for mood")
    api_client("GET", "/api/search?movie=Inception", expected_status=200, expected_desc="Search movies")
    api_client("GET", "/song/recommend", expected_status=200, expected_desc="Recommend songs for user")
    api_client("GET", "/api/songs?mood=happy&limit=5", expected_status=200, expected_desc="Get songs by mood")
    api_client("GET", "/api/search_song?q=Arijit&type=artist", expected_status=200, expected_desc="Search songs")
    api_client("GET", "/book/recommend", expected_status=200, expected_desc="Recommend books for user")
    api_client("GET", "/api/books?emotion=happy&limit=3", expected_status=200, expected_desc="Books by emotion")
    api_client("GET", "/api/search_books?query=harry&type=both", expected_status=200, expected_desc="Search books")


def test_stats_and_export(api_client):
    api_client("GET", "/stats", expected_status=200, expected_desc="User stats")
    api_client("GET", "/mood-trends?days=7", expected_status=200, expected_desc="Mood trends")
    api_client("GET", "/export?format=json", expected_status=200, expected_desc="Export data JSON")


def test_auth_failures(api_client):
    # These calls use use_auth=False to validate 401 behavior
    api_client("GET", "/stats", use_auth=False, expected_status=401, expected_desc="Requires auth")
    api_client("POST", "/process_entry", json={"entry_text": "x"}, use_auth=False, expected_status=401, expected_desc="Requires auth")
