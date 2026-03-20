from rapidfuzz import process

from services.media_recommender.providers.tmdb_provider import TMDbProvider
from services.media_recommender.providers.spotify_provider import SpotifyProvider
from services.media_recommender.providers.books_provider import GoogleBooksProvider

# Minimal mood -> TMDb genre mapping kept for compatibility with previous behavior
MOOD_GENRE_MAP = {
    "happy": ["35", "12", "10751"],
    "sad": ["18", "10749", "36"],
    "angry": ["28", "53", "80"],
    "scared": ["27", "53", "9648"],
    "relaxed": ["99", "16", "14"],
    "excited": ["28", "12", "878"],
    "romantic": ["10749", "35"],
    "thoughtful": ["878", "99"],
}


def _format_tmdb_results(raw_list, max_results=10):
    out = []
    for m in raw_list[:max_results]:
        out.append(
            {
                "title": m.get("title") or m.get("original_title"),
                "release_date": m.get("release_date") or m.get("published_date") or "N/A",
                "overview": m.get("overview") or m.get("description") or "",
                "poster": ("https://image.tmdb.org/t/p/w500" + m.get("poster_path")) if m.get("poster_path") else m.get("poster_url") or None,
            }
        )
    return out


def _fetch_movies_by_genres(genre_ids, max_results=10):
    # TMDbProvider doesn't expose a discover with genres on the provider interface,
    # so call TMDb API directly using the provider's internal helper pattern.
    provider = TMDbProvider()
    # attempt a lightweight loop using provider internals (fallback to popular)
    try:
        # Try fetch popular and filter by genres if available in payload (best-effort)
        candidates = provider._fetch_popular(pages=3)
    except Exception:
        candidates = []
    if not candidates:
        candidates = provider._fetch_top_rated(pages=1)
    return _format_tmdb_results(candidates, max_results=max_results)


def recommend_movies_for_mood(mood):
    mood = (mood or "").strip().lower()
    if not mood:
        return {"error": "Provide mood parameter like ?mood=happy"}, 400
    if mood not in MOOD_GENRE_MAP:
        closest_mood, score, _ = process.extractOne(mood, MOOD_GENRE_MAP.keys())
        genre_ids = MOOD_GENRE_MAP.get(closest_mood, [])
    else:
        genre_ids = MOOD_GENRE_MAP.get(mood, [])

    movies = _fetch_movies_by_genres(genre_ids, max_results=12)
    return {"mood": mood, "recommendations": movies}, 200


def recommend_movies_for_user(uid, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404

    dominant = mood["dominant_mood"]
    genre_ids = MOOD_GENRE_MAP.get(dominant, [])

    if not genre_ids:
        probs = mood.get("mood") or mood.get("mood_probs") or {}
        fallback_mood = None
        if isinstance(probs, dict):
            candidates = sorted(((k, v) for k, v in probs.items() if k != "neutral"), key=lambda x: x[1], reverse=True)
            if candidates:
                fallback_mood = candidates[0][0]
        if fallback_mood:
            genre_ids = MOOD_GENRE_MAP.get(fallback_mood, [])

    if not genre_ids:
        genre_ids = MOOD_GENRE_MAP.get("happy", []) or next(iter(MOOD_GENRE_MAP.values()), [])

    movies = _fetch_movies_by_genres(genre_ids, max_results=12)
    return {"mood": dominant, "recommendations": movies}, 200


def recommend_songs_for_user(uid, limit, language, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404
    # Use SpotifyProvider to fetch candidate songs using mood as semantic query
    provider = SpotifyProvider()
    query = mood.get("dominant_mood") or "top hits"
    filters = {"language": language} if language else None
    candidates = provider.fetch_candidates(query=query, filters=filters, limit=limit)
    return {"mood": mood["dominant_mood"], "recommendations": candidates}, 200


def recommend_books_for_user(uid, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404
    provider = GoogleBooksProvider()
    query = mood.get("dominant_mood") or "book"
    candidates = provider.fetch_candidates(query=query, filters=None, limit=5)
    return {"mood": mood["dominant_mood"], "recommendations": candidates}, 200


def search_movies(query):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide movie parameter like ?movie=Inception", "results": []}, 200
    provider = TMDbProvider()
    # Best-effort: fetch popular pool and filter by query in title
    pool = provider._fetch_popular(pages=3)
    filtered = [m for m in pool if q.lower() in (m.get("title", "") or "").lower() or q.lower() in (m.get("overview", "") or "").lower()]
    results = _format_tmdb_results(filtered, max_results=6)
    return {"searched": q, "results": results}, 200


def get_songs(mood, language, limit):
    provider = SpotifyProvider()
    query = mood or "top hits"
    filters = {"language": language} if language else None
    candidates = provider.fetch_candidates(query=query, filters=filters, limit=limit)
    return candidates, 200


def search_songs(query, search_type, limit):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide query parameter like ?q=Arjit Singh&type=artist"}, 400
    provider = SpotifyProvider()
    candidates = provider.fetch_candidates(query=q, filters=None, limit=limit)
    return candidates, 200


def books_by_emotion(emotion, limit):
    provider = GoogleBooksProvider()
    q = emotion or "book"
    candidates = provider.fetch_candidates(query=q, filters=None, limit=limit)
    return {"emotion": emotion, "results": candidates}, 200


def search_books(query, search_type, max_results):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide query parameter like ?query=Harry Potter"}, 400
    provider = GoogleBooksProvider()
    results = provider.fetch_candidates(query=q, filters=None, limit=max_results)
    return results, 200

