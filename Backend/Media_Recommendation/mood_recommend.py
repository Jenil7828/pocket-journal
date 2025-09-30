import requests, time
import os

API_KEY = os.getenv("TMDB_API_KEY")
BASE_IMG_URL = "https://image.tmdb.org/t/p/w500"

MOOD_GENRE_MAP = {
    "happy": ["35", "12", "10751"],
    "sad": ["18", "10749", "36"],
    "angry": ["28", "53", "80"],
    "scared": ["27", "53", "9648"],
    "relaxed": ["99", "16", "14"],
    "excited": ["28", "12", "878"],
    "romantic": ["10749", "35"],
    "thoughtful": ["878", "99"]
}

def tmdb_get(path, params=None):
    if params is None:
        params = {}
    params["api_key"] = API_KEY
    url = f"https://api.themoviedb.org/3/{path}"
    try:
        r = requests.get(url, params=params, timeout=6)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("TMDb request failed:", e)
        return {}

def get_movies_by_genre(genre_ids, max_results=10):
    results = []
    for page in range(1, 6):
        data = tmdb_get("discover/movie", {
            "with_genres": ",".join(genre_ids),
            "sort_by": "popularity.desc",
            "page": page
        })
        results.extend(data.get("results", []))
        if len(results) >= max_results:
            break
        time.sleep(0.2)
    if not results:
        data = tmdb_get("movie/popular", {"page": 1})
        results = data.get("results", [])
    return [
        {
            "title": m.get("title") or m.get("original_title"),
            "release_date": m.get("release_date", "N/A"),
            "overview": m.get("overview", ""),
            "poster": (BASE_IMG_URL + m["poster_path"]) if m.get("poster_path") else None
        } for m in results[:max_results]
    ]
