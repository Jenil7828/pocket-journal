import pytest


def test_movie_recommend_success(api_client):
    r = api_client("GET", "/movie/recommend")
    assert 200 <= r.status_code < 300, f"Expected success, got {r.status_code}: {r.text}"


def test_movie_recommend_missing_auth(api_client):
    r = api_client("GET", "/movie/recommend", use_auth=False)
    assert r.status_code == 401
