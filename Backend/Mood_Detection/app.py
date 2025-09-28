from flask import Flask, request, jsonify
from database.db_manager import DBManager
from mood_detection_sentence.predictor_sentence_level import SentencePredictor
from summarization.summarizer import Summarizer
from embeddings.embedder import Embedder
from mood_detection_sentence.config_sentence import Config

app = Flask(__name__)

# Initialize DB and models
db = DBManager()
predictor = SentencePredictor(Config.OUTPUT_DIR)

try:
    summarizer = Summarizer()
except Exception as e:
    print("⚠️ Summarizer not available, skipping. Error:", e)
    summarizer = None

try:
    embedder = Embedder()
except Exception as e:
    print("⚠️ Embedder not available, skipping. Error:", e)
    embedder = None


@app.route("/process_entry", methods=["POST"])
def process_entry():
    """
    Expects JSON payload:
    {
        "user_id": 1,
        "entry_text": "Your journal text here..."
    }
    """
    data = request.get_json()
    if not data or "user_id" not in data or "entry_text" not in data:
        return jsonify({"error": "Missing user_id or entry_text"}), 400

    user_id = data["user_id"]
    text = data["entry_text"]

    # Insert journal entry into DB
    entry_id = db.insert_entry(user_id, text)

    # Summarize
    summary = summarizer.summarize(text) if summarizer else "[Summary not available]"

    # Predict mood
    mood_probs = predictor.predict(text)

    # Generate embedding
    embedding = embedder.get_embedding(text).tolist() if embedder else None

    # Save analysis
    db.insert_analysis(entry_id, summary, mood_probs, embedding)

    # Return result
    response = {
        "entry_id": entry_id,
        "summary": summary,
        "mood_probs": mood_probs
    }

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
