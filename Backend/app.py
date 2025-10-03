# app.py
from flask import Flask, request, jsonify, render_template_string
from functools import wraps
import os
from rapidfuzz import process
from dotenv import load_dotenv
from datetime import datetime, time
import pytz
# Load environment variables
load_dotenv()

import firebase_admin
from firebase_admin import credentials, auth

from Media_Recommendation.mood_recommend import get_movies_by_genre, MOOD_GENRE_MAP
from Media_Recommendation.movie_search import search_movie_robust
from Media_Recommendation.song_recommend import get_mood_songs
from Media_Recommendation.search_song import search_songs_or_artist
from Media_Recommendation.books_recommendation import recommend_books_by_emotion
from Media_Recommendation.search_books import search_books_robust
from Mood_Detection.database.db_manager import DBManager
from Mood_Detection.mood_detection_sentence.predictor_sentence_level import SentencePredictor
from Mood_Detection.summarization.summarizer import Summarizer
from Mood_Detection.mood_detection_sentence.config_sentence import Config
from Mood_Detection.analysis.insight_analyzer import InsightsGenerator

app = Flask(__name__)
out_dir = os.path.join(os.path.dirname(__file__), "Mood_Detection", Config.OUTPUT_DIR)
print("Model output dir:", out_dir)
# -------------------- Firebase Initialization --------------------
FIREBASE_JSON = os.getenv("FIREBASE_CREDENTIALS_PATH")
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_JSON)
    firebase_admin.initialize_app(cred)

# -------------------- Auth Decorator --------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        id_token = header.split(" ")[1]
        try:
            decoded_token = auth.verify_id_token(id_token)
            request.user = decoded_token
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
        return f(*args, **kwargs)
    return decorated

# -------------------- Initialize DB and models --------------------
db = DBManager(firebase_json_path=FIREBASE_JSON)
predictor = SentencePredictor(out_dir)

try:
    summarizer = Summarizer()
except Exception as e:
    print("⚠️ Summarizer not available, skipping. Error:", e)
    summarizer = None

# -------------------- Routes --------------------
@app.route("/process_entry", methods=["POST"])
@login_required
def process_entry():
    data = request.get_json()
    if not data or "entry_text" not in data:
        return jsonify({"error": "Missing entry_text"}), 400

    uid = request.user["uid"]
    text = data["entry_text"]

    entry_id = db.insert_entry(uid, text)
    summary = summarizer.summarize(text) if summarizer else text[:200] + "..."
    mood_probs = predictor.predict(summary)
    db.insert_analysis(entry_id, summary, mood_probs)

    return jsonify({
        "entry_id": entry_id,
        "summary": summary,
        "mood_probs": mood_probs
    }), 200

@app.route("/generate_insights", methods=["POST"])
@login_required
def generate_insights():
    data = request.get_json() or {}
    uid = request.user["uid"]
    start_date = data.get("start_date")
    print(start_date)
    end_date = data.get("end_date")
    print(end_date)

    # Set Gemini credentials before initializing InsightsGenerator
    GEMINI_JSON = os.getenv("GEMINI_CREDENTIALS_PATH")
    if GEMINI_JSON:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_JSON
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    generator = InsightsGenerator(db)
    insights= generator.generate_insights(uid, start_date, end_date)
    print(insights)
    return jsonify(insights), 200


@app.route("/entries", methods=["GET"])
@login_required  # your authentication decorator
def get_entries():
    """
    Query journal entries with analysis.
    Accepts query params:
      - start_date: ISO string in IST, e.g., 2025-10-01
      - end_date: ISO string in IST, e.g., 2025-10-02
    """
    IST = pytz.timezone("Asia/Kolkata")
    uid = request.user["uid"]  # assuming your login_required sets request.user
    start_date = request.args.get("start_date") 
    end_date = request.args.get("end_date")      
    if start_date:
        try:
            start_date = IST.localize(datetime.strptime(start_date, "%Y-%m-%d"))
        except ValueError:
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD."}), 400

    if end_date:
        try:
            end_date = IST.localize(datetime.strptime(end_date, "%Y-%m-%d"))
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD."}), 400

    try:
        entries = db.fetch_entries_with_analysis(uid, start_date=start_date, end_date=end_date)
        return jsonify({"entries": entries, "count": len(entries)}), 200
    except Exception as e:
        return jsonify({"error": "Failed to fetch entries", "details": str(e)}), 500

# -------------------- Movies, Songs, Books APIs --------------------
@app.route("/api/recommend", methods=["GET"])
@login_required
def api_recommend():
    mood = (request.args.get("mood") or "").strip().lower()
    if not mood:
        return jsonify({"error": "Provide mood parameter like ?mood=happy"}), 400
    if mood not in MOOD_GENRE_MAP:
        closest_mood, score, _ = process.extractOne(mood, MOOD_GENRE_MAP.keys())
        genre_ids = MOOD_GENRE_MAP[closest_mood]
    else:
        genre_ids = MOOD_GENRE_MAP[mood]
    movies = get_movies_by_genre(genre_ids, max_results=12)
    return jsonify({"mood": mood, "recommendations": movies})

@app.route("/movie/recommend", methods=["GET"])
@login_required
def movie_recommend():
    uid = request.user["uid"]
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return jsonify({"error": "No mood data available for today"}), 404
    genre_ids = MOOD_GENRE_MAP.get(mood["dominant_mood"], [])
    if not genre_ids:
        return jsonify({"error": f"No genre mapping for mood {mood['dominant_mood']}"}), 404
    movies = get_movies_by_genre(genre_ids, max_results=12)
    return jsonify({"mood": mood["dominant_mood"], "recommendations": movies})

@app.route("/song/recommend", methods=["GET"])
@login_required
def song_recommend():
    uid = request.user["uid"]
    limit = int(request.args.get("limit", 10))
    language = request.args.get("language", "both")
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return jsonify({"error": "No mood data available for today"}), 404
    songs = get_mood_songs(user_mood=mood["dominant_mood"], limit=limit, language=language)
    return jsonify({"mood": mood["dominant_mood"], "recommendations": songs})

@app.route("/book/recommend", methods=["GET"])
@login_required
def book_recommend():
    uid = request.user["uid"]
    mood = db.fetch_today_entries_with_mood_summary(uid)
    if not mood.get("dominant_mood"):
        return jsonify({"error": "No mood data available for today"}), 404
    books = recommend_books_by_emotion(mood["dominant_mood"], limit=5)
    return jsonify({"mood": mood["dominant_mood"], "recommendations": books})



@app.route("/api/search", methods=["GET"])
@login_required
def api_search():
    q = (request.args.get("movie") or "").strip()
    if not q:
        return jsonify({"error": "Provide movie parameter like ?movie=Inception"}), 400
    res = search_movie_robust(q, max_candidates=300, top_k=6)
    if res.get("error"):
        return jsonify({"error": res["error"], "results": []}), 404
    return jsonify({"searched": q, "results": res["results"]})

@app.route("/api/songs", methods=["GET"])
@login_required
def get_songs():
    mood = request.args.get("mood", "happy").lower()
    language = request.args.get("language", "both").lower()
    limit = int(request.args.get("limit", 10))
    songs = get_mood_songs(user_mood=mood, limit=limit, language=language)
    return jsonify(songs)

@app.route("/api/search_song", methods=["GET"])
@login_required
def api_search_song():
    query = (request.args.get("q") or "").strip()
    search_type = (request.args.get("type") or "track").lower()
    limit = int(request.args.get("limit", 10))
    if not query:
        return jsonify({"error": "Provide query parameter like ?q=Arjit Sngh&type=artist"}), 400
    res = search_songs_or_artist(query, search_type=search_type, limit=limit)
    return jsonify(res)

@app.route("/api/books", methods=["GET"])
@login_required
def get_books_by_emotion():
    emotion = request.args.get("emotion", "happy").lower()
    limit = int(request.args.get("limit", 5))
    books = recommend_books_by_emotion(emotion, limit)
    return jsonify({"emotion": emotion, "results": books})

@app.route("/api/search_books", methods=["GET"])
@login_required
def api_search_books():
    query = (request.args.get("query") or "").strip()
    search_type = (request.args.get("type") or "both").lower()
    max_results = int(request.args.get("limit", 10))
    if not query:
        return jsonify({"error": "Provide query parameter like ?query=Harry Potter"}), 400
    results = search_books_robust(query=query, max_results=max_results, search_type=search_type)
    return jsonify(results)

MAIN_PAGE_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>📓 Pocket Journal — Mood-Based Recommendations API</title>
  <style>
    body { 
      font-family: Arial, sans-serif; 
      margin: 20px; 
      line-height: 1.6; 
      background: #fafafa;
      color: #2c3e50;
    }
    h1 { color: #34495e; }
    h2 { color: #16a085; margin-top: 30px; }
    code { 
      background: #f4f4f4; 
      padding: 3px 6px; 
      border-radius: 4px; 
      font-size: 0.95em; 
    }
    pre {
      background: #f8f8f8;
      padding: 10px;
      border-left: 4px solid #16a085;
      border-radius: 4px;
      overflow-x: auto;
    }
    ul { margin: 10px 0 20px 20px; }
    li { margin-bottom: 6px; }
    footer {
      margin-top: 40px;
      font-size: 0.9em;
      color: #7f8c8d;
      border-top: 1px solid #ddd;
      padding-top: 10px;
    }
    .section { margin-bottom: 30px; }
  </style>
</head>
<body>
  <h1>📓 Pocket Journal — Mood-Based Recommendations API</h1>
  <p>
    Welcome! Use the following endpoints to analyze journal entries 
    and get personalized recommendations for <b>movies</b>, <b>songs</b>, and <b>books</b>.
  </p>

  <div class="section">
    <h2>📝 Journal Entry Processing</h2>
    <p><code>POST /process_entry</code></p>
    <p><b>Request JSON:</b></p>
    <pre>{
  "entry_text": "Your journal text here..."
}</pre>
    <p><b>Response:</b> <i>entry_id</i>, <i>summary</i>, <i>mood probabilities</i></p>
  </div>

  <div class="section">
    <h2>🔍 Generate Insights</h2>
    <p><code>POST /generate_insights</code></p>
    <p><b>Request JSON:</b></p>
    <pre>{
  "start_date": "2025-09-01",  // optional 
  "end_date": "2025-09-30"     // optional
}</pre>
    <p><b>Response:</b> Extracted insights (goals, progress, challenges, etc.)</p>
  </div>

  <div class="section">
    <h2>🎬 Movies</h2>
    <ul>
      <li>Get movies by mood: <code>/api/recommend?mood=happy</code></li>
      <li>Search movies (typo-tolerant): <code>/api/search?movie=Incepton</code></li>
    </ul>
  </div>

  <div class="section">
    <h2>🎵 Songs</h2>
    <ul>
      <li>
        Get songs by mood:  
        <code>/api/songs?mood=happy&language=both&limit=5</code>
        <br><small>
          - mood: happy, sad, chill, energetic, romantic<br>
          - language: english, hindi, both (default = both)<br>
          - limit: number of songs (default = 10)
        </small>
      </li>
      <li>
        Search songs or artists:  
        <code>/api/search_song?q=arjit sngh&type=artist&limit=10</code>
        <br><small>
          - q: Song or artist name (typo-tolerant)<br>
          - type: track or artist (default = track)<br>
          - limit: number of results (default = 10)
        </small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>📚 Books</h2>
    <ul>
      <li>
        Get books by emotion:  
        <code>/api/books?emotion=happy&limit=5</code><br>
        <small>Emotions: happy, sad, angry, romantic, stressed, bored</small>
      </li>
      <li>
        Search books:  
        <code>/api/search_books?query=harry poter&type=both&limit=5</code>
        <br><small>
          - query: book title or author<br>
          - type: title, author, or both (default = both)<br>
          - limit: number of results (default = 10)
        </small>
      </li>
    </ul>
  </div>

  <footer>
    🚀 Pocket Journal API is running. Test with Postman, Curl, or your frontend app.
  </footer>
</body>
</html>
"""
# -------------------- Home Page --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template_string(MAIN_PAGE_HTML)

# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)