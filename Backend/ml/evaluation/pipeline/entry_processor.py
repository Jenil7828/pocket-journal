import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from ml.evaluation.orchestrator.api_client import APIClient
from ml.evaluation.orchestrator.ground_truth_loader import GroundTruthLoader
from ml.evaluation.ground_truth.gemini_generator import GeminiGTGenerator
from utils import extract_dominant_mood

logger = logging.getLogger()

class EntryProcessor:
    """Processes a single journal entry through the entire system via the API.
    
    Orchestrates the workflow: Create Entry -> Get Recommendations -> Get Insights -> Match GT.
    """
    
    def __init__(self, api_client: APIClient, ground_truth_loader: GroundTruthLoader, 
                 gemini_generator: GeminiGTGenerator = None,
                 rec_limit: int = 5, cleanup_after: bool = False):
        self.api_client = api_client
        self.gt_loader = ground_truth_loader
        self.gemini_generator = gemini_generator
        self.rec_limit = rec_limit
        self.cleanup_after = cleanup_after

    def process_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Process one entry end-to-end and collect results and metrics."""
        entry_id = entry["entry_id"]
        text = entry["entry_text"]
        created_at = entry["created_at"]
        
        errors = []
        latencies = {
            "journal_create": 0,
            "movies_recommend": 0,
            "songs_recommend": 0,
            "books_recommend": 0,
            "insights_generate": 0
        }
        
        # Output structure
        result = {
            "entry_id": entry_id,
            "created_entry_id": None,
            "text": text,
            "created_at": created_at,
            "ground_truth": {
                "dominant_emotion": None,
                "emotion_labels": None,
                "reference_summary": None
            },
            "prediction": {
                "dominant_emotion": None,
                "emotion_probabilities": {},
                "summary": None,
                "summary_length_tokens": 0,
                "original_length_tokens": 0,
                "compression_ratio": 0.0
            },
            "recommendations": {
                "movies": [],
                "songs": [],
                "books": []
            },
            "insights": {
                "goals": [],
                "appreciation": None,
                "conflicts": None,
                "negative_behaviors": None
            },
            "metadata": {
                "processing_timestamp": datetime.utcnow().isoformat() + "Z",
                "api_latency_ms": latencies,
                "errors": errors
            }
        }

        # Step 1: Create Journal Entry via API
        start = time.time()
        try:
            api_res = self.api_client.create_journal_entry(text, title=entry.get("title"))
            latencies["journal_create"] = int((time.time() - start) * 1000)
            
            created_id = api_res.get("entry_id")
            result["created_entry_id"] = created_id
            
            # Analysis extraction
            analysis = api_res.get("analysis", {})
            mood_probs = analysis.get("mood", {})
            summary = analysis.get("summary", "")
            
            result["prediction"].update({
                "dominant_emotion": extract_dominant_mood(mood_probs),
                "emotion_probabilities": mood_probs,
                "summary": summary,
                "summary_length_tokens": len(summary.split()) if summary else 0,
                "original_length_tokens": len(text.split()),
                "compression_ratio": (len(summary.split()) / len(text.split())) if text.split() else 0.0
            })
        except Exception as e:
            errors.append(f"Journal creation failed: {str(e)}")
            logger.error("[PIPELINE] Entry %s creation failed: %s", entry_id, str(e))
            return result # Critical failure, return partial record

        # Step 2: Recommendations
        # Movies
        start = time.time()
        try:
            movies = self.api_client.get_movie_recommendations(limit=self.rec_limit)
            latencies["movies_recommend"] = int((time.time() - start) * 1000)
            result["recommendations"]["movies"] = [
                {"id": str(m.get("id")), "title": m.get("title"), "score": m.get("score"), "genres": m.get("genres", [])}
                for m in movies
            ]
        except Exception as e:
            errors.append(f"Movie recommendation failed: {str(e)}")

        # Songs
        start = time.time()
        try:
            songs = self.api_client.get_song_recommendations(limit=self.rec_limit)
            latencies["songs_recommend"] = int((time.time() - start) * 1000)
            result["recommendations"]["songs"] = [
                {"id": str(s.get("id")), "title": s.get("title"), "score": s.get("score")}
                for s in songs
            ]
        except Exception as e:
            errors.append(f"Song recommendation failed: {str(e)}")

        # Books
        start = time.time()
        try:
            books = self.api_client.get_book_recommendations(limit=self.rec_limit)
            latencies["books_recommend"] = int((time.time() - start) * 1000)
            result["recommendations"]["books"] = [
                {"id": str(b.get("id")), "title": b.get("title"), "score": b.get("score")}
                for b in books
            ]
        except Exception as e:
            errors.append(f"Book recommendation failed: {str(e)}")

        # Step 3: Insights
        if created_at:
            start_date = created_at[:10] # YYYY-MM-DD
            end_date = datetime.now().strftime("%Y-%m-%d")
            start = time.time()
            try:
                insights = self.api_client.generate_insights(start_date, end_date)
                latencies["insights_generate"] = int((time.time() - start) * 1000)
                if insights:
                    result["insights"].update({
                        "goals": insights.get("goals", []),
                        "appreciation": insights.get("appreciation"),
                        "conflicts": insights.get("conflicts"),
                        "negative_behaviors": insights.get("negative_behaviors")
                    })
            except Exception as e:
                errors.append(f"Insights generation failed: {str(e)}")

        # Step 4: Match Ground Truth
        gt = self.gt_loader.get_ground_truth(entry_id)
        if gt:
            result["ground_truth"].update({
                "dominant_emotion": gt.get("dominant_emotion"),
                "emotion_labels": gt.get("emotion_labels"),
                "reference_summary": gt.get("reference_summary")
            })
        elif self.gemini_generator:
            # Fallback to Gemini for automated GT
            try:
                gemini_gt = self.gemini_generator.generate_ground_truth(text)
                if gemini_gt:
                    result["ground_truth"].update({
                        "dominant_emotion": gemini_gt.get("primary_emotion"),
                        "emotion_labels": gemini_gt.get("emotions"),
                        "reference_summary": gemini_gt.get("summary"),
                        "insight": gemini_gt.get("insight")
                    })
            except Exception as e:
                logger.warning("[PIPELINE] Gemini GT generation failed for entry %s: %s", entry_id, str(e))

        # Step 5: Cleanup
        if self.cleanup_after and result["created_entry_id"]:
            try:
                self.api_client.delete_journal_entry(result["created_entry_id"])
            except Exception as e:
                logger.warning("[PIPELINE] Cleanup failed for entry %s: %s", result["created_entry_id"], str(e))

        return result
