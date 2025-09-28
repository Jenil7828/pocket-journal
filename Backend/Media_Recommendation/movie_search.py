import time, requests
from rapidfuzz import process, fuzz
import os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("TMDB_APIKEY")
BASE_IMG_URL = "https://image.tmdb.org/t/p/w500"

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

def search_movie_robust(query, max_candidates=300, top_k=6):
    query = (query or "").strip()
    if not query:
        return {"error": "Empty query", "results": []}

    seen_ids = set()
    candidates = []

    # 1) Search TMDb directly (3 pages)
    for page in range(1, 4):
        data = tmdb_get("search/movie", {"query": query, "page": page, "include_adult": "false"})
        for m in data.get("results", []):
            if m.get("id") and m["id"] not in seen_ids:
                seen_ids.add(m["id"])
                candidates.append(m)
        if len(candidates) >= 60:
            break
        time.sleep(0.2)

    # 2) Fallback: substring / token search if few candidates
    if len(candidates) < 10:
        qlen = len(query)
        tries = []
        if qlen > 4:
            tries += [query[:qlen//2], query[:qlen-1], query[:qlen-2], query[:qlen-3]]
        tries += [tok for tok in query.split() if len(tok) >= 3]
        for t in tries:
            if len(candidates) >= max_candidates:
                break
            for page in range(1, 3):
                data = tmdb_get("search/movie", {"query": t, "page": page, "include_adult": "false"})
                for m in data.get("results", []):
                    if m.get("id") and m["id"] not in seen_ids:
                        seen_ids.add(m["id"])
                        candidates.append(m)
                time.sleep(0.2)

    # 3) Add popular movies pages 1..5
    if len(candidates) < 80:
        for page in range(1, 6):
            data = tmdb_get("movie/popular", {"page": page})
            for m in data.get("results", []):
                if m.get("id") and m["id"] not in seen_ids:
                    seen_ids.add(m["id"])
                    candidates.append(m)
            if len(candidates) >= max_candidates:
                break
            time.sleep(0.2)

    if not candidates:
        return {"error": "No candidates found on TMDb", "results": []}

    titles = []
    for m in candidates:
        title = m.get("title") or m.get("original_title") or ""
        year = (m.get("release_date") or "")[:4]
        title_with_year = f"{title} ({year})" if year else title
        titles.append(title_with_year)

    matches = process.extract(query, titles, scorer=fuzz.token_sort_ratio, limit=top_k)

    results = []
    for match in matches:
        matched_title, score, idx = match
        movie_obj = candidates[idx]
        results.append({
            "title": movie_obj.get("title") or movie_obj.get("original_title"),
            "matched_title": matched_title,
            "score": int(score),
            "release_date": movie_obj.get("release_date", "N/A"),
            "overview": movie_obj.get("overview", ""),
            "poster": (BASE_IMG_URL + movie_obj["poster_path"]) if movie_obj.get("poster_path") else None,
            "tmdb_id": movie_obj.get("id")
        })

    return {"error": None, "results": results}
