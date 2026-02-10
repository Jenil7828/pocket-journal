from firebase_admin import firestore


def generate_insights(user, data, db, enable_llm=False, enable_insights=True):
    uid = user["uid"]
    start_date = data.get("start_date") if data else None
    end_date = data.get("end_date") if data else None

    # Simple DB-backed cache: look for an existing insights doc with same uid & date range
    try:
        insights_query = db.db.collection("insights").where(filter=firestore.FieldFilter("uid", "==", uid))
        if start_date is not None:
            insights_query = insights_query.where(filter=firestore.FieldFilter("start_date", "==", start_date))
        if end_date is not None:
            insights_query = insights_query.where(filter=firestore.FieldFilter("end_date", "==", end_date))
        docs = list(insights_query.limit(1).stream())
        if docs:
            doc = docs[0]
            data_out = doc.to_dict()
            data_out["insight_id"] = doc.id
            return data_out, 200
    except Exception:
        # If cache lookup fails, fallthrough to generator depending on flags
        pass

    if not enable_llm or not enable_insights:
        return {"insights": [], "note": "LLM/insights disabled; enable to generate insights"}, 200

    try:
        from ai_insights.insight_analyzer import InsightsGenerator
        generator = InsightsGenerator(db)
        insights = generator.generate_insights(uid, start_date, end_date)
        return insights, 200
    except Exception as e:
        return {"error": "Failed to generate insights", "details": str(e)}, 500


def get_insights(uid, limit, offset, db):
    insights_query = db.db.collection("insights").where(filter=firestore.FieldFilter("uid", "==", uid)).order_by("created_at", direction="DESCENDING").limit(limit).offset(offset)
    insights = []
    for insight_doc in insights_query.stream():
        insight_data = insight_doc.to_dict()
        insight_data["insight_id"] = insight_doc.id
        insights.append(insight_data)
    return {"insights": insights, "count": len(insights), "limit": limit, "offset": offset}, 200


def get_single_insight(insight_id, uid, db):
    insight_doc = db.db.collection("insights").document(insight_id).get()
    if not insight_doc.exists:
        return {"error": "Insight not found"}, 404
    insight_data = insight_doc.to_dict()
    if insight_data.get("uid") != uid:
        return {"error": "Unauthorized: Insight does not belong to user"}, 403
    insight_data["insight_id"] = insight_id
    return insight_data, 200


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

