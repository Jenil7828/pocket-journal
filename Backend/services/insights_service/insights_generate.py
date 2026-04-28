from firebase_admin import firestore
import logging

logger = logging.getLogger()


def _fallback_clean_insights() -> dict:
    return {
        "goals": [],
        "progress": "",
        "negative_behaviors": [],
        "remedies": [],
        "appreciation": "You're beginning to reflect on your patterns more consistently.",
        "conflicts": [],
    }


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
    
    # Check user's weekly_insights_enabled setting
    try:
        user_doc = db.db.collection("users").document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict() or {}
            settings = user_data.get("settings", {}) or {}
            if not settings.get("weekly_insights_enabled", True):
                return {"insights": [], "note": "Weekly insights disabled in user settings"}, 200
    except Exception as e:
        logger.debug("Failed to check user settings for insights: %s", str(e))

    try:
        from config_loader import get_config
        use_gemini = bool(get_config()["ml"]["insight_generation"].get("use_gemini", False))

        if use_gemini:
            logger.info("Insights backend: Gemini")
            from ml.inference.insight_generation.gemini.insight_analyzer import InsightsGenerator, fallback_insight
            generator = InsightsGenerator(db)
        else:
            logger.info("Insights backend: Local model (Qwen2)")
            from ml.inference.insight_generation.qwen2.insight_analyzer import InsightsGenerator
            generator = InsightsGenerator(db, insights_predictor=insights_predictor)

        try:
            insights = generator.generate_insights(uid, start_date, end_date)
        except Exception:
            logger.warning("AI failed, fallback used")
            if use_gemini:
                fallback_body = fallback_insight(uid, start_date, end_date)
                insight_item = (fallback_body.get("insights") or [{}])[0] or {}
                return _clean_insight_response({
                    "goals": insight_item.get("goals", []),
                    "progress": "",
                    "negative_behaviors": insight_item.get("negative_behaviors", []),
                    "remedies": [],
                    "appreciation": insight_item.get("appreciation", ""),
                    "conflicts": insight_item.get("conflicts", []),
                }), 200
            insights = _fallback_clean_insights()

        if isinstance(insights, dict) and "insights" in insights:
            insight_item = (insights.get("insights") or [{}])[0] or {}
            insights = {
                "goals": insight_item.get("goals", []),
                "progress": insight_item.get("progress", ""),
                "negative_behaviors": insight_item.get("negative_behaviors", []),
                "remedies": insight_item.get("remedies", []),
                "appreciation": insight_item.get("appreciation", ""),
                "conflicts": insight_item.get("conflicts", []),
            }

        return _clean_insight_response(insights or _fallback_clean_insights()), 200
    except Exception:
        logger.warning("AI failed, fallback used")
        return _clean_insight_response(_fallback_clean_insights()), 200


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

    mappings_query = db.db.collection("insight_entry_mapping").where(
        filter=firestore.FieldFilter("insight_id", "==", insight_id)
    ).get()
    mappings_deleted = 0
    for mapping_doc in mappings_query:
        mapping_doc.reference.delete()
        mappings_deleted += 1

    insight_doc.reference.delete()
    return {"message": "Insight deleted successfully", "insight_id": insight_id, "mappings_deleted": mappings_deleted}, 200


def get_insight(insight_id, uid, db):
    """Get a single insight by ID with authorization check."""
    try:
        ref = db.db.collection("insights").document(insight_id)
        doc = ref.get()
        
        if not doc.exists:
            return {"error": "Insight not found"}, 404
        
        data = doc.to_dict()
        if data.get("uid") != uid:
            return {"error": "Unauthorized"}, 403
        
        data["id"] = insight_id
        return {"insight": data}, 200
    except Exception as e:
        return {"error": str(e)}, 500