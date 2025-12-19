# app.py
import os
import warnings
# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')

from flask import Flask, request, jsonify, render_template
from functools import wraps
from dotenv import load_dotenv
from datetime import datetime, time
import pytz
# Logging
import logging
# Load environment variables
load_dotenv()

# Configure logging for the application. Use APP_LOG_LEVEL to control verbosity.
LOG_LEVEL = os.getenv("APP_LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pocket_journal")

# Reduce noise from verbose libraries in development
logging.getLogger("werkzeug").setLevel(os.getenv("WERKZEUG_LOG_LEVEL", "WARNING"))
logging.getLogger("firebase_admin").setLevel(os.getenv("FIREBASE_LOG_LEVEL", "WARNING"))

import firebase_admin
from firebase_admin import credentials, auth, firestore
from Mood_Detection.mood_detection_roberta.config import Config
import journal_entries
import insights_service
import media_recommendations
import stats_service
import export_service
import health_service

# Lazy singletons (initialized on first use)
_db = None
_predictor = None
_summarizer = None


def get_db():
    """Lazily initialize DBManager to avoid heavy work at import time."""
    global _db
    if _db is None:
        # Import here to avoid firebase side-effects during module import
        from Mood_Detection.database.db_manager import DBManager
        FIREBASE_JSON = os.getenv("FIREBASE_CREDENTIALS_PATH")
        _db = DBManager(firebase_json_path=FIREBASE_JSON)
    return _db


def get_predictor():
    """Lazily create SentencePredictor (model loaded once)."""
    global _predictor
    if _predictor is None:
        from Mood_Detection.mood_detection_roberta.predictor import SentencePredictor
        out_dir = os.path.join(os.path.dirname(__file__), "Mood_Detection", Config.OUTPUT_DIR)
        _predictor = SentencePredictor(out_dir)
    return _predictor


def get_summarizer():
    """Lazily create SummarizationPredictor if available."""
    global _summarizer
    if _summarizer is None:
        try:
            from Mood_Detection.summarization.predictor import SummarizationPredictor
            summarizer_model_path = os.path.join(os.path.dirname(__file__), "Mood_Detection", "outputs", "models", "summarizer")
            _summarizer = SummarizationPredictor(model_path=summarizer_model_path)
        except Exception:
            _summarizer = None
    return _summarizer

app = Flask(__name__)
# Print model output dir only when initializing predictor to avoid spamming during reloads
_ = None
# -------------------- Firebase Initialization --------------------
# Do NOT initialize firebase or models at import time. Use get_db()/get_predictor() instead.

# Feature flags (runtime-configurable via env vars)
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() in ("1", "true", "yes")
ENABLE_INSIGHTS = os.getenv("ENABLE_INSIGHTS", str(ENABLE_LLM)).lower() in ("1", "true", "yes")


# -------------------- Auth Decorator --------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Ensure Firebase SDK is initialized before attempting token verification.
        try:
            firebase_admin.get_app()
        except ValueError:
            FIREBASE_JSON = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if FIREBASE_JSON and os.path.exists(FIREBASE_JSON):
                try:
                    cred = credentials.Certificate(FIREBASE_JSON)
                    firebase_admin.initialize_app(cred)
                except Exception:
                    # Fallback: try initializing with default credentials
                    firebase_admin.initialize_app()
            else:
                # Initialize with default credentials (if available in environment)
                firebase_admin.initialize_app()

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
# DB and models are lazily initialized via `get_db()`, `get_predictor()` and `get_summarizer()`.

# -------------------- Routes --------------------
@app.route("/process_entry", methods=["POST"])
@login_required
def process_entry():
    data = request.get_json()
    # lazily obtain DB and models when needed; avoids reload side-effects
    _db = get_db()
    predictor = get_predictor()
    summarizer = get_summarizer()
    body, status = journal_entries.process_entry(request.user, data, _db, predictor, summarizer)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/generate_insights", methods=["POST"])
@login_required
def generate_insights():
    data = request.get_json() or {}
    # Set Gemini credentials before initializing InsightsGenerator
    GEMINI_JSON = os.getenv("GEMINI_CREDENTIALS_PATH")
    if GEMINI_JSON:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_JSON
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    # Use the DB instance lazily and pass flags so external LLM calls can be disabled
    _db = get_db()
    body, status = insights_service.generate_insights(request.user, data, _db, enable_llm=ENABLE_LLM, enable_insights=ENABLE_INSIGHTS)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)



@app.route("/entries/<entry_id>", methods=["DELETE"])
@login_required
def delete_entry(entry_id):
    """
    Delete a specific journal entry and its associated analysis.
    
    Path Parameters:
      - entry_id: The ID of the journal entry to delete
    
    Returns:
      - Success: Details of what was deleted
      - Error: Error message with details
    """
    uid = request.user["uid"]
    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400
    _db = get_db()
    body, status = journal_entries.delete_entry(entry_id, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/entries/batch", methods=["DELETE"])
@login_required
def delete_entries_batch():
    """
    Delete multiple journal entries and their associated analysis.
    
    Request Body:
      {
        "entry_ids": ["entry_id_1", "entry_id_2", ...]
      }
    
    Returns:
      - Success: Summary of deleted entries
      - Error: Error message with details
    """
    uid = request.user["uid"]
    data = request.get_json()
    if not data or "entry_ids" not in data:
        return jsonify({"error": "Missing entry_ids in request body"}), 400
    entry_ids = data["entry_ids"]
    if not isinstance(entry_ids, list) or len(entry_ids) == 0:
        return jsonify({"error": "entry_ids must be a non-empty array"}), 400

    _db = get_db()
    body, status = journal_entries.delete_entries_batch(entry_ids, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/entries/<entry_id>", methods=["PUT"])
@login_required
def update_entry(entry_id):
    """
    Update a journal entry and regenerate its analysis.
    
    Path Parameters:
      - entry_id: The ID of the journal entry to update
    
    Request Body:
      {
        "entry_text": "Updated journal text here...",
        "regenerate_analysis": true  // optional, defaults to true
      }
    
    Returns:
      - Success: Updated entry details and new analysis
      - Error: Error message with details
    """
    uid = request.user["uid"]
    data = request.get_json()
    _db = get_db()
    predictor = get_predictor()
    summarizer = get_summarizer()
    body, status = journal_entries.update_entry(entry_id, uid, data, _db, predictor, summarizer)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/entries/<entry_id>/reanalyze", methods=["POST"])
@login_required
def reanalyze_entry(entry_id):
    """
    Regenerate analysis for an existing journal entry.
    Useful when analysis was not generated during update.
    
    Path Parameters:
      - entry_id: The ID of the journal entry to reanalyze
    
    Returns:
      - Success: New analysis data
      - Error: Error message with details
    """
    uid = request.user["uid"]
    _db = get_db()
    predictor = get_predictor()
    summarizer = get_summarizer()
    body, status = journal_entries.reanalyze_entry(entry_id, uid, _db, predictor, summarizer)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

# ==================== NEW API ENDPOINTS ====================

@app.route("/entries/<entry_id>", methods=["GET"])
@login_required
def get_single_entry(entry_id):
    """
    Get a specific journal entry with its analysis.
    
    Path Parameters:
      - entry_id: The ID of the journal entry to retrieve
    
    Returns:
      - Success: Entry details with analysis
      - Error: Error message with details
    """
    uid = request.user["uid"]
    _db = get_db()
    body, status = journal_entries.get_single_entry(entry_id, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/entries/<entry_id>/analysis", methods=["GET"])
@login_required
def get_entry_analysis(entry_id):
    """
    Get mood analysis for a specific journal entry.
    
    Path Parameters:
      - entry_id: The ID of the journal entry
    
    Returns:
      - Success: Analysis details
      - Error: Error message with details
    """
    uid = request.user["uid"]
    _db = get_db()
    body, status = journal_entries.get_entry_analysis(entry_id, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/insights", methods=["GET"])
@login_required
def get_insights():
    """
    Get all insights for the authenticated user.
    
    Query Parameters:
      - limit: Maximum number of insights to return (default: 50)
      - offset: Number of insights to skip (default: 0)
    
    Returns:
      - Success: List of insights
      - Error: Error message with details
    """
    uid = request.user["uid"]
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "Invalid limit or offset parameter"}), 400
    _db = get_db()
    body, status = insights_service.get_insights(uid, limit, offset, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/insights/<insight_id>", methods=["GET"])
@login_required
def get_single_insight(insight_id):
    """
    Get a specific insight by ID.
    
    Path Parameters:
      - insight_id: The ID of the insight to retrieve
    
    Returns:
      - Success: Insight details
      - Error: Error message with details
    """
    uid = request.user["uid"]
    if not insight_id:
        return jsonify({"error": "Insight ID is required"}), 400
    _db = get_db()
    body, status = insights_service.get_single_insight(insight_id, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/insights/<insight_id>", methods=["DELETE"])
@login_required
def delete_insight(insight_id):
    """
    Delete a specific insight and its associated mappings.
    
    Path Parameters:
      - insight_id: The ID of the insight to delete
    
    Returns:
      - Success: Deletion confirmation
      - Error: Error message with details
    """
    uid = request.user["uid"]
    if not insight_id:
        return jsonify({"error": "Insight ID is required"}), 400
    _db = get_db()
    body, status = insights_service.delete_insight(insight_id, uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

# -------------------- Movies, Songs, Books APIs --------------------
@app.route("/api/recommend", methods=["GET"])
@login_required
def api_recommend():
    mood = request.args.get("mood")
    _db = get_db()
    # recommend_movies_for_mood expects only the mood string
    body, status = media_recommendations.recommend_movies_for_mood(mood)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/movie/recommend", methods=["GET"])
@login_required
def movie_recommend():
    uid = request.user["uid"]
    _db = get_db()
    body, status = media_recommendations.recommend_movies_for_user(uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/song/recommend", methods=["GET"])
@login_required
def song_recommend():
    uid = request.user["uid"]
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400
    language = request.args.get("language", "both")
    _db = get_db()
    body, status = media_recommendations.recommend_songs_for_user(uid, limit, language, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/book/recommend", methods=["GET"])
@login_required
def book_recommend():
    uid = request.user["uid"]
    _db = get_db()
    body, status = media_recommendations.recommend_books_for_user(uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)



@app.route("/api/search", methods=["GET"])
@login_required
def api_search():
    q = request.args.get("movie")
    _db = get_db()
    # search_movies expects only the query string
    body, status = media_recommendations.search_movies(q)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/api/songs", methods=["GET"])
@login_required
def get_songs():
    mood = request.args.get("mood", "happy").lower()
    language = request.args.get("language", "both").lower()
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400
    body, status = media_recommendations.get_songs(mood, language, limit)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/api/search_song", methods=["GET"])
@login_required
def api_search_song():
    query = request.args.get("q")
    search_type = (request.args.get("type") or "track").lower()
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400
    body, status = media_recommendations.search_songs(query, search_type, limit)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/api/books", methods=["GET"])
@login_required
def get_books_by_emotion():
    emotion = request.args.get("emotion", "happy").lower()
    try:
        limit = int(request.args.get("limit", 5))
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400
    body, status = media_recommendations.books_by_emotion(emotion, limit)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/api/search_books", methods=["GET"])
@login_required
def api_search_books():
    query = request.args.get("query")
    search_type = (request.args.get("type") or "both").lower()
    try:
        max_results = int(request.args.get("limit", 10))
    except ValueError:
        return jsonify({"error": "Invalid limit"}), 400
    body, status = media_recommendations.search_books(query, search_type, max_results)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)



# ==================== ADDITIONAL API ENDPOINTS ====================

@app.route("/entries", methods=["GET"])
@login_required
def get_entries_filtered():
    """
    Get journal entries with filtering options.
    
    Query Parameters:
      - start_date: Start date filter (YYYY-MM-DD)
      - end_date: End date filter (YYYY-MM-DD)
      - mood: Filter by dominant mood (happy, sad, angry, etc.)
      - search: Search in entry text
      - limit: Maximum number of entries (default: 50)
      - offset: Number of entries to skip (default: 0)
    
    Returns:
      - Success: Filtered list of entries
      - Error: Error message with details
    """
    uid = request.user["uid"]
    params = {
        "start_date": request.args.get("start_date"),
        "end_date": request.args.get("end_date"),
        "mood": request.args.get("mood"),
        "search": request.args.get("search"),
        "limit": request.args.get("limit", 50),
        "offset": request.args.get("offset", 0),
    }
    _db = get_db()
    body, status = journal_entries.get_entries_filtered(uid, params, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/stats", methods=["GET"])
@login_required
def get_user_stats():
    """
    Get user statistics and dashboard data.
    
    Returns:
      - Success: User statistics
      - Error: Error message with details
    """
    uid = request.user["uid"]
    _db = get_db()
    body, status = stats_service.get_user_stats(uid, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/mood-trends", methods=["GET"])
@login_required
def get_mood_trends():
    """
    Get mood trends over time.
    
    Query Parameters:
      - days: Number of days to analyze (default: 30)
    
    Returns:
      - Success: Mood trends data
      - Error: Error message with details
    """
    uid = request.user["uid"]
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        return jsonify({"error": "Invalid days parameter"}), 400
    _db = get_db()
    body, status = stats_service.get_mood_trends(uid, days, _db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for API status.
    
    Returns:
      - Success: API health status
    """
    _db = get_db()
    body, status = health_service.health_check(_db)
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

@app.route("/export", methods=["GET"])
@login_required
def export_data():
    """
    Export user data in JSON format.
    
    Query Parameters:
      - start_date: Start date for export (YYYY-MM-DD)
      - end_date: End date for export (YYYY-MM-DD)
      - format: Export format (json, csv) - default: json
    
    Returns:
      - Success: Exported data
      - Error: Error message with details
    """
    uid = request.user["uid"]
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    export_format = request.args.get("format", "json").lower()

    _db = get_db()
    result = export_service.export_data(uid, start_date, end_date, export_format, _db)
    if isinstance(result, tuple) and len(result) == 3:
        return result
    body, status = result
    return (jsonify(body), status) if isinstance(body, dict) else (body, status)

# -------------------- Home Page --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")

# -------------------- Run App --------------------
if __name__ == "__main__":
    # Respect environment debug/reloader flags to avoid multiple model loads
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "true").lower() in ("1", "true", "yes")
    DISABLE_RELOADER = os.getenv("DISABLE_RELOADER", "false").lower() in ("1", "true", "yes")
    use_reloader = FLASK_DEBUG and not DISABLE_RELOADER
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=FLASK_DEBUG, use_reloader=use_reloader)