from database.db_manager import DBManager
from mood_detection_sentence.predictor_sentence_level import SentencePredictor
from summarization.summarizer import Summarizer
from embeddings.embedder import Embedder
from mood_detection_sentence.config_sentence import Config
import json


def process_entries(user_id, start_date=None, end_date=None):
    db = DBManager()

    # Load trained mood model
    predictor = SentencePredictor(Config.OUTPUT_DIR)

    # Summarizer & embedder with safe fallback
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

    # Fetch user journal entries
    entries = db.fetch_entries(user_id, start_date, end_date)
    for entry in entries:
        entry_id, text = entry["id"], entry["entry_text"]

        # Summarize entry
        summary = summarizer.summarize(text) if summarizer else "[Summary not available]"

        # Predict mood (JSON with probabilities)
        mood_probs = predictor.predict(text)

        # Generate embedding
        embedding = embedder.get_embedding(text).tolist() if embedder else None

        # Save results in DB
        db.insert_analysis(entry_id, summary, mood_probs, embedding)

        print(f"✅ Processed entry {entry_id}: Top mood = {max(mood_probs, key=mood_probs.get)}")

if __name__ == "__main__":
    process_entries(user_id=1)

# from database.db_manager import DBManager
# from mood_detection.predictor import MoodPredictor
# from summarization.summarizer import Summarizer
# from embeddings.embedder import Embedder
# from mood_detection.config import Config
#
# def process_entries(user_id, start_date=None, end_date=None):
#     db = DBManager()
#
#     # Mood predictor (your trained model)
#     predictor = MoodPredictor("./outputs/models/mood_model")
#
#     # Summarizer & embedder with safe fallback
#     try:
#         summarizer = Summarizer()
#     except Exception as e:
#         print("⚠️ Summarizer model not available, skipping summarization.")
#         summarizer = None
#
#     try:
#         embedder = Embedder()
#     except Exception as e:
#         print("⚠️ Embedder model not available, skipping embeddings.")
#         embedder = None
#
#     entries = db.fetch_entries(user_id, start_date, end_date)
#     for entry in entries:
#         entry_id, text = entry["id"], entry["entry_text"]
#
#         # Summarize (or fallback)
#         if summarizer:
#             summary = summarizer.summarize(text)
#         else:
#             summary = "[Summary not available: model not trained]"
#
#         # Mood Detection
#         mood = predictor.predict(text)
#
#         # Embedding (or fallback)
#         if embedder:
#             embedding = embedder.get_embedding(text)
#             embedding = embedding.tolist()
#         else:
#             embedding = None
#
#         # Store results with timestamp
#         db.insert_analysis(entry_id, summary, mood, embedding)
#
#         print(f"✅ Processed entry {entry_id}: Mood={mood}, Summary={summary[:50]}...")
#
# if __name__ == "__main__":
#     process_entries(user_id=1)



# from database.db_manager import DBManager
# from mood_detection.predictor import MoodPredictor
# from summarization.summarizer import Summarizer
# from embeddings.embedder import Embedder
# from mood_detection.config import Config
#
# def process_entries(user_id, start_date=None, end_date=None):
#     db = DBManager()
#     predictor = MoodPredictor( "./outputs/models/mood_model")#f"{Config.OUTPUT_DIR}/roberta_mood.pt")
#     summarizer = Summarizer()
#     embedder = Embedder()
#
#     entries = db.fetch_entries(user_id, start_date, end_date)
#     for entry in entries:
#         entry_id, text = entry["id"], entry["entry_text"]
#
#         # Summarize
#         summary = summarizer.summarize(text)
#
#         # Mood Detection
#         mood = predictor.predict(text)
#
#         # Embedding
#         embedding = embedder.get_embedding(text)
#
#         # Store results with timestamp
#         db.insert_analysis(entry_id, summary, mood, embedding)
#
#         print(f"✅ Processed entry {entry_id}: Mood={mood}, Summary={summary[:50]}...")
#
# if __name__ == "__main__":
#     process_entries(user_id=1)
