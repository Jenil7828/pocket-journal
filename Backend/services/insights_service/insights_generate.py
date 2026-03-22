from firebase_admin import firestore
import logging

logger = logging.getLogger("pocket_journal.insights.service")


def _clean_insight_response(data: dict) -> dict:
    """Return only the insight content fields. Internal fields stay in DB but are not sent to client."""
    return {
        "goals": data.get("goals") or [],
        "progress": data.get("progress") or "",
        "negative_behaviors": data.get("negative_behaviors") or "",
        "remedies": data.get("remedies") or "",
        "appreciation": data.get("appreciation") or "",
        "conflicts": data.get("conflicts") or "",
    }


def generate_insights(user, data, db, enable_llm=False, enable_insights=True, insights_predictor=None):
    uid = user["uid"]
    start_date = data.get("start_date") if data else None
    end_date = data.get("end_date") if data else None

    if not enable_llm or not enable_insights:
        return {"insights": [], "note": "LLM/insights disabled; enable to generate insights"}, 200

    try:
        from config_loader import get_config
        use_gemini = bool(get_config()["insights"].get("use_gemini", False))

        if use_gemini:
            logger.info("Insights backend: Gemini")
            from ml.insight_generation.inference.gemini.insight_analyzer import InsightsGenerator
            generator = InsightsGenerator(db)
        else:
            logger.info("Insights backend: Local model (Qwen2)")
            from ml.insight_generation.inference.qwen2.insight_analyzer import InsightsGenerator
            generator = InsightsGenerator(db, insights_predictor=insights_predictor)

        insights = generator.generate_insights(uid, start_date, end_date)
        return _clean_insight_response(insights), 200
    except Exception as e:
        logger.exception("Failed to generate insights for uid=%s", uid)
        return {"error": "Failed to generate insights", "details": str(e)}, 500


def get_insights(uid, limit, offset, db):
    insights_query = db.db.collection("insights").where(filter=firestore.FieldFilter("uid", "==", uid)).order_by("created_at", direction="DESCENDING").limit(limit).offset(offset)
    insights = []
    for insight_doc in insights_query.stream():
        insight_data = insight_doc.to_dict()
        cleaned = _clean_insight_response(insight_data)
        cleaned["insight_id"] = insight_doc.id
        insights.append(cleaned)
    return {"insights": insights, "count": len(insights), "limit": limit, "offset": offset}, 200


def get_single_insight(insight_id, uid, db):
    insight_doc = db.db.collection("insights").document(insight_id).get()
    if not insight_doc.exists:
        return {"error": "Insight not found"}, 404
    insight_data = insight_doc.to_dict()
    if insight_data.get("uid") != uid:
        return {"error": "Unauthorized: Insight does not belong to user"}, 403
    insight_data["insight_id"] = insight_id
    cleaned = _clean_insight_response(insight_data)
    cleaned["insight_id"] = insight_id
    return cleaned, 200


def delete_insight(insight_id, uid, db):
    insight_doc = db.db.collection("insights").document(insight_id).get()
    if not insight_doc.exists:
        return {"error": "Insight not found"}, 404
    insight_data = insight_doc.to_dict()
    if insight_data.get("uid") != uid:
        return {"error": "Unauthorized: Insight does not belong to user"}, 403

    mappings_query = db.db.collection("insight_entry_mapping").where(filter=("insight_id", "==", insight_id)).get()
    mappings_deleted = 0
    for mapping_doc in mappings_query:
        mapping_doc.reference.delete()
        mappings_deleted += 1

    insight_doc.reference.delete()
    return {"message": "Insight deleted successfully", "insight_id": insight_id, "mappings_deleted": mappings_deleted}, 200

