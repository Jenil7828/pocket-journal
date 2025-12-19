from rapidfuzz import process

from Media_Recommendation.mood_recommend import get_movies_by_genre, MOOD_GENRE_MAP
from Media_Recommendation.song_recommend import get_mood_songs
from Media_Recommendation.books_recommendation import recommend_books_by_emotion
from Media_Recommendation.movie_search import search_movie_robust
from Media_Recommendation.search_song import search_songs_or_artist
from Media_Recommendation.search_books import search_books_robust


def recommend_movies_for_mood(mood):
    mood = (mood or "").strip().lower()
    if not mood:
        return {"error": "Provide mood parameter like ?mood=happy"}, 400
    if mood not in MOOD_GENRE_MAP:
        closest_mood, score, _ = process.extractOne(mood, MOOD_GENRE_MAP.keys())
        genre_ids = MOOD_GENRE_MAP[closest_mood]
    else:
        genre_ids = MOOD_GENRE_MAP[mood]
    movies = get_movies_by_genre(genre_ids, max_results=12)
    return {"mood": mood, "recommendations": movies}, 200


def recommend_movies_for_user(uid, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404

    dominant = mood["dominant_mood"]
    genre_ids = MOOD_GENRE_MAP.get(dominant, [])

    # If there's no direct mapping (e.g., 'neutral'), try to pick the next most likely
    # non-neutral mood from the mood probabilities, or fall back to a sensible default.
    if not genre_ids:
        probs = mood.get("mood") or mood.get("mood_probs") or {}
        fallback_mood = None
        if isinstance(probs, dict):
            # exclude 'neutral' and pick the highest-scoring remaining mood
            candidates = sorted(((k, v) for k, v in probs.items() if k != "neutral"), key=lambda x: x[1], reverse=True)
            if candidates:
                fallback_mood = candidates[0][0]

        if fallback_mood:
            genre_ids = MOOD_GENRE_MAP.get(fallback_mood, [])

    # Final fallback: use 'happy' mapping or any first available mapping
    if not genre_ids:
        if "happy" in MOOD_GENRE_MAP:
            genre_ids = MOOD_GENRE_MAP["happy"]
        else:
            first = next(iter(MOOD_GENRE_MAP.values()), [])
            genre_ids = first

    if not genre_ids:
        return {"error": f"No genre mapping available"}, 404

    movies = get_movies_by_genre(genre_ids, max_results=12)
    return {"mood": dominant, "recommendations": movies}, 200


def recommend_songs_for_user(uid, limit, language, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404
    songs = get_mood_songs(user_mood=mood["dominant_mood"], limit=limit, language=language)
    return {"mood": mood["dominant_mood"], "recommendations": songs}, 200


def recommend_books_for_user(uid, db):
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return {"error": "No mood data available for today"}, 404
    books = recommend_books_by_emotion(mood["dominant_mood"], limit=5)
    return {"mood": mood["dominant_mood"], "recommendations": books}, 200


def search_movies(query):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide movie parameter like ?movie=Inception", "results": []}, 200
    res = search_movie_robust(q, max_candidates=300, top_k=6)
    # Normalize search to always return 200 with results array (may be empty)
    if res.get("error"):
        return {"searched": q, "results": []}, 200
    return {"searched": q, "results": res.get("results", [])}, 200


def get_songs(mood, language, limit):
    songs = get_mood_songs(user_mood=mood, limit=limit, language=language)
    return songs, 200


def search_songs(query, search_type, limit):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide query parameter like ?q=Arjit Sngh&type=artist"}, 400
    res = search_songs_or_artist(q, search_type=search_type, limit=limit)
    return res, 200


def books_by_emotion(emotion, limit):
    books = recommend_books_by_emotion(emotion, limit)
    return {"emotion": emotion, "results": books}, 200


def search_books(query, search_type, max_results):
    q = (query or "").strip()
    if not q:
        return {"error": "Provide query parameter like ?query=Harry Potter"}, 400
    results = search_books_robust(query=q, max_results=max_results, search_type=search_type)
    return results, 200