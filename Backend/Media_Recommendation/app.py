from flask import Flask, request, jsonify, render_template_string
from rapidfuzz import process
from mood_recommend import get_movies_by_genre, MOOD_GENRE_MAP
from movie_search import search_movie_robust
from song_recommend import get_mood_songs
from search_song import search_songs_or_artist
from books_recommendation import recommend_books_by_emotion
from search_books import search_books_robust

app = Flask(__name__)

# -------------------- API Routes --------------------

# Mood-based movie recommendation
@app.route("/api/recommend", methods=["GET"])
def api_recommend():
    mood = (request.args.get("mood") or "").strip().lower()
    if not mood:
        return jsonify({"error": "Provide mood parameter like ?mood=excited"}), 400
    # fuzzy match mood
    if mood not in MOOD_GENRE_MAP:
        closest_mood, score, _ = process.extractOne(mood, MOOD_GENRE_MAP.keys())
        genre_ids = MOOD_GENRE_MAP[closest_mood]
    else:
        genre_ids = MOOD_GENRE_MAP[mood]
    movies = get_movies_by_genre(genre_ids, max_results=12)
    return jsonify({"mood": mood, "recommendations": movies})

# Movie search (typos OK)
@app.route("/api/search", methods=["GET"])
def api_search():
    q = (request.args.get("movie") or "").strip()
    if not q:
        return jsonify({"error": "Provide movie parameter like ?movie=Incepton"}), 400
    res = search_movie_robust(q, max_candidates=300, top_k=6)
    if res.get("error"):
        return jsonify({"error": res["error"], "results": []}), 404
    return jsonify({"searched": q, "results": res["results"]})



@app.route("/api/songs", methods=["GET"])
def get_songs():
    # Get query parameters
    mood = request.args.get("mood", "happy").lower()
    language = request.args.get("language", "both").lower()  # english, hindi, both
    limit = int(request.args.get("limit", 10))
    
    # Call the updated function
    songs = get_mood_songs(user_mood=mood, limit=limit, language=language)
    
    return jsonify(songs)



@app.route("/api/search_song", methods=["GET"])
def api_search_song():
    query = (request.args.get("q") or "").strip()
    search_type = (request.args.get("type") or "track").lower()  # track / artist
    limit = int(request.args.get("limit", 10))

    if not query:
        return jsonify({"error": "Provide query parameter like ?q=Arjit Sngh&type=artist"}), 400

    res = search_songs_or_artist(query, search_type=search_type, limit=limit)

    return jsonify(res)


@app.route("/api/books", methods=["GET"])
def get_books_by_emotion():
    emotion = request.args.get("emotion", "happy").lower()
    limit = int(request.args.get("limit", 5))
    books = recommend_books_by_emotion(emotion, limit)
    return jsonify({
        "emotion": emotion,
        "results": books
    })

@app.route("/api/search_books", methods=["GET"])
def api_search_books():
    query = (request.args.get("query") or "").strip()
    search_type = (request.args.get("type") or "both").lower()  # title, author, both
    max_results = int(request.args.get("limit", 10))
    
    if not query:
        return jsonify({"error": "Provide query parameter like ?query=Harry Potter"}), 400

    results = search_books_robust(query=query, max_results=max_results, search_type=search_type)
    return jsonify(results)

MAIN_TEMPLATE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Pocket Journal — Mood Movie Recommender</title>
</head>
<body>
  <h1>🎬 Pocket Journal — Mood Movie Recommender</h1>
  <p>Use the API endpoints:</p>
  <ul>
    <li>Get movies by mood: <code>/api/recommend?mood=happy</code></li>
    <li>Search movies: <code>/api/search?movie=Incepton</code></li>
  </ul>
  <p>Use the API endpoints:</p>
  <li><h1>Get songs by mood: </h1>
    <code>/api/songs?mood=happy&language=both&limit=5</code>
    <br>
    <small>Parameters:</small>
    <ul>
        <li><strong>mood</strong>: Mood of the songs (happy, sad, chill, energetic, romantic)</li>
        <li><strong>language</strong>: Song language (english, hindi, both). Default is both.</li>
        <li><strong>limit</strong>: Number of songs to return. Default is 10.</li>
    </ul>
</li>
<li><h1>Search songs or artists:</h1> 
  <code>/api/search_song?q=arjit sngh&type=artist&limit=10</code><br>
  <small>Parameters:</small>
  <ul>
    <li><strong>q</strong>: Song or artist name (supports typos)</li>
    <li><strong>type</strong>: "track" or "artist". Default is "artist".</li>
    <li><strong>limit</strong>: Number of results (default 10)</li>
  </ul>
</li>
 <h1>📚 Emotion-Based Book Recommendation API</h1>
            <p>Use the following endpoints to get book recommendations:</p>
            <ul>
                <li>Get books by emotion: <code>/api/books?emotion=happy&limit=5</code></li>
                <li>Example emotions: <b>happy, sad, angry, romantic, stressed, bored</b></li>
                 <li>Search books (typo-tolerant): <code>/api/search_books?query=harry poter&type=both&limit=5</code></li>
            </ul>
            <p>🔗 Try it now: <a href="/api/books?emotion=happy&limit=5" target="_blank">Books for Happy Mood</a></p>
        </div>
    </body>

</body>
</html>
"""

@app.route("/", methods=["GET"])
def home():
    return render_template_string(MAIN_TEMPLATE)

# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(debug=True)
