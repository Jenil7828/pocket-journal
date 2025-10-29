# app.py
import os
import warnings
# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')

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
from firebase_admin import credentials, auth, firestore

from Media_Recommendation.mood_recommend import get_movies_by_genre, MOOD_GENRE_MAP
from Media_Recommendation.movie_search import search_movie_robust
from Media_Recommendation.song_recommend import get_mood_songs
from Media_Recommendation.search_song import search_songs_or_artist
from Media_Recommendation.books_recommendation import recommend_books_by_emotion
from Media_Recommendation.search_books import search_books_robust
from Mood_Detection.database.db_manager import DBManager
from Mood_Detection.mood_detection_roberta.predictor import SentencePredictor
from Mood_Detection.summarization.predictor import SummarizationPredictor
from Mood_Detection.mood_detection_roberta.config import Config
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
    summarizer_model_path = os.path.join(os.path.dirname(__file__), "Mood_Detection", "outputs", "models", "summarizer")
    summarizer = SummarizationPredictor(model_path=summarizer_model_path)
except Exception as e:
    print("WARNING: SummarizationPredictor not available, skipping. Error:", e)
    summarizer = None

# -------------------- Routes --------------------
@app.route("/process_entry", methods=["POST"])
@login_required
def process_entry():
    try:
        data = request.get_json()
        if not data or "entry_text" not in data:
            return jsonify({"error": "Missing entry_text"}), 400

        uid = request.user["uid"]
        text = data["entry_text"]

        entry_id = db.insert_entry(uid, text)
        summary = summarizer.summarize(text) if summarizer else text[:200] + "..."
        # Use lower threshold for better mixed emotion detection
        mood_result = predictor.predict(summary, threshold=0.25)
        mood_probs = mood_result["probabilities"]  # Extract just the probabilities
        db.insert_analysis(entry_id, summary, mood_probs)

        return jsonify({
            "entry_id": entry_id,
            "summary": summary,
            "mood_probs": mood_probs
        }), 200
    except Exception as e:
        print(f"Error in process_entry: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

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
    
    try:
        result = db.delete_entry(entry_id, uid)
        
        if result["success"]:
            return jsonify({
                "message": "Entry deleted successfully",
                "deleted": result["deleted"]
            }), 200
        else:
            return jsonify({"error": result["error"]}), 400
            
    except Exception as e:
        return jsonify({"error": "Failed to delete entry", "details": str(e)}), 500

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
    
    try:
        result = db.delete_entries_batch(entry_ids, uid)
        
        if result["success"]:
            return jsonify({
                "message": "All entries deleted successfully",
                "deleted_count": result["deleted_count"],
                "deleted_entries": result["deleted_entries"]
            }), 200
        else:
            return jsonify({
                "message": "Some entries could not be deleted",
                "deleted_count": result["deleted_count"],
                "failed_count": result["failed_count"],
                "deleted_entries": result["deleted_entries"],
                "failed_entries": result["failed_entries"]
            }), 207  # 207 Multi-Status for partial success
            
    except Exception as e:
        return jsonify({"error": "Failed to delete entries", "details": str(e)}), 500

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
    
    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400
    
    if not data or "entry_text" not in data:
        return jsonify({"error": "Missing entry_text in request body"}), 400
    
    new_entry_text = data["entry_text"]
    regenerate_analysis = data.get("regenerate_analysis", True)
    
    if not new_entry_text.strip():
        return jsonify({"error": "Entry text cannot be empty"}), 400
    
    try:
        if regenerate_analysis:
            # Update entry and immediately regenerate analysis
            result = db.update_entry_with_analysis(entry_id, uid, new_entry_text, predictor, summarizer)
        else:
            # Update entry only (analysis will need to be regenerated separately)
            result = db.update_entry(entry_id, uid, new_entry_text)
        
        if result["success"]:
            return jsonify({
                "message": "Entry updated successfully",
                "updated": result["updated"]
            }), 200
        else:
            return jsonify({"error": result["error"]}), 400
            
    except Exception as e:
        return jsonify({"error": "Failed to update entry", "details": str(e)}), 500

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
    
    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400
    
    try:
        # First, verify the entry belongs to the user and get the text
        entry_doc = db.db.collection("journal_entries").document(entry_id).get()
        if not entry_doc.exists:
            return jsonify({"error": "Entry not found"}), 404
        
        entry_data = entry_doc.to_dict()
        if entry_data.get("uid") != uid:
            return jsonify({"error": "Unauthorized: Entry does not belong to user"}), 403
        
        entry_text = entry_data["entry_text"]
        
        # Delete existing analysis
        analysis_query = db.db.collection("entry_analysis").where("entry_id", "==", entry_id).get()
        old_analysis_ids = []
        
        for analysis_doc in analysis_query:
            analysis_doc.reference.delete()
            old_analysis_ids.append(analysis_doc.id)
        
        # Generate new analysis
        summary = summarizer.summarize(entry_text) if summarizer else entry_text[:200] + "..."
        mood_probs = predictor.predict(summary)
        
        # Insert new analysis
        db.insert_analysis(entry_id, summary, mood_probs)
        
        return jsonify({
            "message": "Entry reanalyzed successfully",
            "entry_id": entry_id,
            "old_analysis_deleted": len(old_analysis_ids),
            "old_analysis_ids": old_analysis_ids,
            "new_analysis": {
                "summary": summary,
                "mood_probs": mood_probs
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to reanalyze entry", "details": str(e)}), 500

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
    
    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400
    
    try:
        # Get the entry
        entry_doc = db.db.collection("journal_entries").document(entry_id).get()
        if not entry_doc.exists:
            return jsonify({"error": "Entry not found"}), 404
        
        entry_data = entry_doc.to_dict()
        if entry_data.get("uid") != uid:
            return jsonify({"error": "Unauthorized: Entry does not belong to user"}), 403
        
        # Get analysis for this entry
        analysis_query = db.db.collection("entry_analysis").where("entry_id", "==", entry_id).get()
        analysis_data = None
        
        for analysis_doc in analysis_query:
            analysis_data = analysis_doc.to_dict()
            analysis_data["analysis_id"] = analysis_doc.id
            break
        
        # Format response
        response_data = {
            "entry_id": entry_id,
            "entry_text": entry_data["entry_text"],
            "created_at": entry_data["created_at"],
            "updated_at": entry_data.get("updated_at"),
            "analysis": analysis_data
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve entry", "details": str(e)}), 500

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
    
    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400
    
    try:
        # Verify entry exists and belongs to user
        entry_doc = db.db.collection("journal_entries").document(entry_id).get()
        if not entry_doc.exists:
            return jsonify({"error": "Entry not found"}), 404
        
        entry_data = entry_doc.to_dict()
        if entry_data.get("uid") != uid:
            return jsonify({"error": "Unauthorized: Entry does not belong to user"}), 403
        
        # Get analysis
        analysis_query = db.db.collection("entry_analysis").where("entry_id", "==", entry_id).get()
        
        if not analysis_query:
            return jsonify({"error": "No analysis found for this entry"}), 404
        
        analysis_data = None
        for analysis_doc in analysis_query:
            analysis_data = analysis_doc.to_dict()
            analysis_data["analysis_id"] = analysis_doc.id
            break
        
        return jsonify({
            "entry_id": entry_id,
            "analysis": analysis_data
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve analysis", "details": str(e)}), 500

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
        # Get query parameters
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
        
        # Get insights for user
        insights_query = db.db.collection("insights").where("uid", "==", uid).order_by("created_at", direction="DESCENDING").limit(limit).offset(offset)
        insights = []
        
        for insight_doc in insights_query.stream():
            insight_data = insight_doc.to_dict()
            insight_data["insight_id"] = insight_doc.id
            insights.append(insight_data)
        
        return jsonify({
            "insights": insights,
            "count": len(insights),
            "limit": limit,
            "offset": offset
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve insights", "details": str(e)}), 500

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
    
    try:
        # Get the insight
        insight_doc = db.db.collection("insights").document(insight_id).get()
        if not insight_doc.exists:
            return jsonify({"error": "Insight not found"}), 404
        
        insight_data = insight_doc.to_dict()
        if insight_data.get("uid") != uid:
            return jsonify({"error": "Unauthorized: Insight does not belong to user"}), 403
        
        insight_data["insight_id"] = insight_id
        
        return jsonify(insight_data), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve insight", "details": str(e)}), 500

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
    
    try:
        # Verify insight exists and belongs to user
        insight_doc = db.db.collection("insights").document(insight_id).get()
        if not insight_doc.exists:
            return jsonify({"error": "Insight not found"}), 404
        
        insight_data = insight_doc.to_dict()
        if insight_data.get("uid") != uid:
            return jsonify({"error": "Unauthorized: Insight does not belong to user"}), 403
        
        # Delete insight-entry mappings
        mappings_query = db.db.collection("insight_entry_mapping").where("insight_id", "==", insight_id).get()
        mappings_deleted = 0
        
        for mapping_doc in mappings_query:
            mapping_doc.reference.delete()
            mappings_deleted += 1
        
        # Delete the insight
        insight_doc.reference.delete()
        
        return jsonify({
            "message": "Insight deleted successfully",
            "insight_id": insight_id,
            "mappings_deleted": mappings_deleted
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to delete insight", "details": str(e)}), 500

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
    <h2>✏️ Update Entries</h2>
    <ul>
      <li>
        Update single entry: <code>PUT /entries/{entry_id}</code>
        <br><small>Request body: <code>{"entry_text": "new text", "regenerate_analysis": true}</code></small>
        <br><small>Updates the journal entry and regenerates its analysis</small>
      </li>
      <li>
        Reanalyze entry: <code>POST /entries/{entry_id}/reanalyze</code>
        <br><small>Regenerates analysis for an existing entry without changing the text</small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>📖 Get Entries</h2>
    <ul>
      <li>
        Get all entries: <code>GET /entries</code>
        <br><small>Query params: <code>?start_date=2025-01-01&end_date=2025-01-31&mood=happy&search=keyword&limit=50&offset=0</code></small>
      </li>
      <li>
        Get single entry: <code>GET /entries/{entry_id}</code>
        <br><small>Returns entry with analysis</small>
      </li>
      <li>
        Get entry analysis: <code>GET /entries/{entry_id}/analysis</code>
        <br><small>Returns only mood analysis for the entry</small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>🗑️ Delete Entries</h2>
    <ul>
      <li>
        Delete single entry: <code>DELETE /entries/{entry_id}</code>
        <br><small>Deletes the journal entry and its associated analysis</small>
      </li>
      <li>
        Delete multiple entries: <code>DELETE /entries/batch</code>
        <br><small>Request body: <code>{"entry_ids": ["id1", "id2", ...]}</code></small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>💡 Insights Management</h2>
    <ul>
      <li>
        Get all insights: <code>GET /insights</code>
        <br><small>Query params: <code>?limit=50&offset=0</code></small>
      </li>
      <li>
        Get specific insight: <code>GET /insights/{insight_id}</code>
        <br><small>Returns detailed insight information</small>
      </li>
      <li>
        Delete insight: <code>DELETE /insights/{insight_id}</code>
        <br><small>Deletes insight and its mappings</small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>📊 Analytics & Statistics</h2>
    <ul>
      <li>
        User statistics: <code>GET /stats</code>
        <br><small>Returns total entries, insights, mood distribution, recent activity</small>
      </li>
      <li>
        Mood trends: <code>GET /mood-trends</code>
        <br><small>Query params: <code>?days=30</code> - Returns mood trends over time</small>
      </li>
    </ul>
  </div>

  <div class="section">
    <h2>🔧 Utility & Export</h2>
    <ul>
      <li>
        Health check: <code>GET /health</code>
        <br><small>Returns API health status and service connectivity</small>
      </li>
      <li>
        Export data: <code>GET /export</code>
        <br><small>Query params: <code>?start_date=2025-01-01&end_date=2025-01-31&format=json</code></small>
        <br><small>Supports JSON and CSV formats</small>
      </li>
    </ul>
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
    
    try:
        # Get query parameters with validation
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        mood_filter = request.args.get("mood")
        search_term = request.args.get("search")
        
        # Validate limit and offset
        try:
            limit = int(request.args.get("limit", 50))
            offset = int(request.args.get("offset", 0))
        except ValueError:
            return jsonify({"error": "Invalid limit or offset parameter"}), 400
        
        # Validate limit range
        if limit < 1 or limit > 100:
            return jsonify({"error": "Limit must be between 1 and 100"}), 400
        
        if offset < 0:
            return jsonify({"error": "Offset must be non-negative"}), 400
        
        # Build query
        query = db.db.collection("journal_entries").where(filter=firestore.FieldFilter("uid", "==", uid))
        
        # Apply date filters
        if start_date and start_date.strip():
            try:
                # Convert to string and parse using strptime
                start_date_str = str(start_date).strip()
                start_datetime_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
                # Make it timezone-aware (IST)
                IST = pytz.timezone("Asia/Kolkata")
                start_datetime = IST.localize(start_datetime_naive)
                query = query.where(filter=firestore.FieldFilter("created_at", ">=", start_datetime))
            except ValueError as e:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
        
        if end_date and end_date.strip():
            try:
                # Convert to string and parse using strptime
                end_date_str = str(end_date).strip()
                end_datetime_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
                # Make it timezone-aware (IST) and set to end of day
                IST = pytz.timezone("Asia/Kolkata")
                end_datetime = IST.localize(end_datetime_naive.replace(hour=23, minute=59, second=59))
                query = query.where(filter=firestore.FieldFilter("created_at", "<=", end_datetime))
            except ValueError as e:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
        
        # Order by created_at descending
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        entries = []
        all_entries = []
        
        # Get all entries first
        try:
            for entry_doc in query.stream():
                entry_data = entry_doc.to_dict()
                entry_data["entry_id"] = entry_doc.id
                all_entries.append(entry_data)
        except Exception as e:
            raise e
        
        # Apply filters
        for i, entry_data in enumerate(all_entries):
            try:
                # Apply search filter
                if search_term and search_term.lower() not in entry_data["entry_text"].lower():
                    continue
                
                # Get analysis for mood filtering
                if mood_filter:
                    try:
                        analysis_query = db.db.collection("entry_analysis").where(filter=firestore.FieldFilter("entry_id", "==", entry_data["entry_id"])).get()
                        has_matching_mood = False
                        
                        for analysis_doc in analysis_query:
                            analysis_data = analysis_doc.to_dict()
                            mood_probs = analysis_data.get("mood", {})
                            if mood_probs:
                                dominant_mood = max(mood_probs, key=mood_probs.get)
                                if dominant_mood == mood_filter.lower():
                                    has_matching_mood = True
                                    break
                        
                        if not has_matching_mood:
                            continue
                    except Exception as e:
                        # If analysis query fails, skip mood filtering
                        pass
                
                entries.append(entry_data)
            except Exception as e:
                # Skip this entry and continue
                continue
        
        # Apply pagination manually
        total_count = len(entries)
        entries = entries[offset:offset + limit]
        
        return jsonify({
            "entries": entries,
            "count": len(entries),
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "filters": {
                "start_date": start_date,
                "end_date": end_date,
                "mood": mood_filter,
                "search": search_term
            }
        }), 200
        
    except Exception as e:
        import traceback
        error_details = {
            "error": "Failed to retrieve entries",
            "details": str(e),
            "type": type(e).__name__,
            "traceback": traceback.format_exc()
        }
        print(f"Error in get_entries_filtered: {error_details}")  # Debug print
        print(f"Full traceback: {traceback.format_exc()}")  # Additional debug
        return jsonify(error_details), 500

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
    
    try:
        # Get total entries count
        entries_query = db.db.collection("journal_entries").where("uid", "==", uid)
        total_entries = len(list(entries_query.stream()))
        
        # Get total insights count
        insights_query = db.db.collection("insights").where("uid", "==", uid)
        total_insights = len(list(insights_query.stream()))
        
        # Get mood distribution
        mood_distribution = {}
        analysis_query = db.db.collection("entry_analysis").stream()
        
        for analysis_doc in analysis_query:
            # Check if this analysis belongs to user's entries
            analysis_data = analysis_doc.to_dict()
            entry_id = analysis_data.get("entry_id")
            
            # Verify entry belongs to user
            entry_doc = db.db.collection("journal_entries").document(entry_id).get()
            if entry_doc.exists and entry_doc.to_dict().get("uid") == uid:
                mood_probs = analysis_data.get("mood", {})
                if mood_probs:
                    dominant_mood = max(mood_probs, key=mood_probs.get)
                    mood_distribution[dominant_mood] = mood_distribution.get(dominant_mood, 0) + 1
        
        # Get recent activity (last 7 days)
        from datetime import timedelta
        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_entries_query = db.db.collection("journal_entries").where("uid", "==", uid).where("created_at", ">=", seven_days_ago)
        recent_entries_count = len(list(recent_entries_query.stream()))
        
        return jsonify({
            "total_entries": total_entries,
            "total_insights": total_insights,
            "recent_entries_7_days": recent_entries_count,
            "mood_distribution": mood_distribution,
            "most_common_mood": max(mood_distribution, key=mood_distribution.get) if mood_distribution else None
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve statistics", "details": str(e)}), 500

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
        from datetime import timedelta
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get entries in date range
        entries_query = db.db.collection("journal_entries").where("uid", "==", uid).where("created_at", ">=", start_date).where("created_at", "<=", end_date)
        entries = list(entries_query.stream())
        
        # Get mood data for each entry
        mood_trends = []
        for entry_doc in entries:
            entry_data = entry_doc.to_dict()
            entry_id = entry_doc.id
            
            # Get analysis
            analysis_query = db.db.collection("entry_analysis").where("entry_id", "==", entry_id).get()
            for analysis_doc in analysis_query:
                analysis_data = analysis_doc.to_dict()
                mood_probs = analysis_data.get("mood", {})
                
                if mood_probs:
                    dominant_mood = max(mood_probs, key=mood_probs.get)
                    mood_trends.append({
                        "date": entry_data["created_at"].strftime("%Y-%m-%d"),
                        "mood": dominant_mood,
                        "confidence": mood_probs[dominant_mood]
                    })
        
        # Sort by date
        mood_trends.sort(key=lambda x: x["date"])
        
        return jsonify({
            "period_days": days,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "trends": mood_trends,
            "total_data_points": len(mood_trends)
        }), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to retrieve mood trends", "details": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """
    Health check endpoint for API status.
    
    Returns:
      - Success: API health status
    """
    try:
        # Test database connection
        db_status = "connected"
        try:
            # Simple database test
            db.db.collection("journal_entries").limit(1).stream()
        except Exception:
            db_status = "disconnected"
        
        # Test Firebase auth
        auth_status = "connected"
        try:
            # Simple auth test
            auth.list_users(max_results=1)
        except Exception:
            auth_status = "disconnected"
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": db_status,
                "authentication": auth_status
            },
            "version": "1.0.0"
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

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
    
    try:
        # Get query parameters
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        export_format = request.args.get("format", "json").lower()
        
        # Build query
        query = db.db.collection("journal_entries").where("uid", "==", uid)
        
        if start_date and start_date.strip():
            try:
                start_date_str = str(start_date).strip()
                start_datetime_naive = datetime.strptime(start_date_str, "%Y-%m-%d")
                # Make it timezone-aware (IST)
                IST = pytz.timezone("Asia/Kolkata")
                start_datetime = IST.localize(start_datetime_naive)
                query = query.where("created_at", ">=", start_datetime)
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
        
        if end_date and end_date.strip():
            try:
                end_date_str = str(end_date).strip()
                end_datetime_naive = datetime.strptime(end_date_str, "%Y-%m-%d")
                # Make it timezone-aware (IST) and set to end of day
                IST = pytz.timezone("Asia/Kolkata")
                end_datetime = IST.localize(end_datetime_naive.replace(hour=23, minute=59, second=59))
                query = query.where("created_at", "<=", end_datetime)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
        
        # Get entries
        entries = []
        for entry_doc in query.stream():
            entry_data = entry_doc.to_dict()
            entry_data["entry_id"] = entry_doc.id
            
            # Get analysis for this entry
            analysis_query = db.db.collection("entry_analysis").where("entry_id", "==", entry_doc.id).get()
            analysis_data = None
            
            for analysis_doc in analysis_query:
                analysis_data = analysis_doc.to_dict()
                analysis_data["analysis_id"] = analysis_doc.id
                break
            
            entry_data["analysis"] = analysis_data
            entries.append(entry_data)
        
        # Get insights
        insights = []
        insights_query = db.db.collection("insights").where("uid", "==", uid)
        for insight_doc in insights_query.stream():
            insight_data = insight_doc.to_dict()
            insight_data["insight_id"] = insight_doc.id
            insights.append(insight_data)
        
        export_data = {
            "user_id": uid,
            "export_timestamp": datetime.now().isoformat(),
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "entries": entries,
            "insights": insights,
            "total_entries": len(entries),
            "total_insights": len(insights)
        }
        
        if export_format == "csv":
            # Convert to CSV format (simplified)
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            writer.writerow(["entry_id", "entry_text", "created_at", "updated_at", "dominant_mood", "mood_confidence"])
            
            # Write data
            for entry in entries:
                dominant_mood = None
                confidence = None
                if entry.get("analysis") and entry["analysis"].get("mood"):
                    mood_probs = entry["analysis"]["mood"]
                    dominant_mood = max(mood_probs, key=mood_probs.get)
                    confidence = mood_probs[dominant_mood]
                
                writer.writerow([
                    entry["entry_id"],
                    entry["entry_text"],
                    entry["created_at"].isoformat() if entry.get("created_at") else "",
                    entry.get("updated_at").isoformat() if entry.get("updated_at") else "",
                    dominant_mood,
                    confidence
                ])
            
            return output.getvalue(), 200, {"Content-Type": "text/csv"}
        
        return jsonify(export_data), 200
        
    except Exception as e:
        return jsonify({"error": "Failed to export data", "details": str(e)}), 500

# -------------------- Home Page --------------------
@app.route("/", methods=["GET"])
def home():
    return render_template_string(MAIN_PAGE_HTML)

# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)