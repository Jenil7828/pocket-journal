# 🗺️ API Route → Service → Database Mapping

## Journal Entries Domain

### POST /api/v1/journal - Create Entry

```
HTTP Request:
  Method: POST
  Path: /api/v1/journal
  Headers: Authorization: Bearer {JWT_TOKEN}
  Body: {
    "entry_text": "string (required, ≤5000 chars)",
    "title": "string (optional, ≤200 chars)"
  }

Route Handler: routes/journal_domain.py:create_journal_entry()
  ├─ Extract: user = request.user (from @login_required decorator)
  ├─ Extract: data = request.get_json()
  └─ Call Service:

Service: services/journal_entries/entry_create.py:process_entry()
  Input: (user, data, db, predictor, summarizer)
  
  Processing Steps:
  ├─ Validate: "entry_text" present and non-empty
  ├─ DB: db.insert_entry(uid, text, title)
  │   └─ Firestore: INSERT into journal_entries
  │       ├─ entry_id (auto-generated)
  │       ├─ uid
  │       ├─ entry_text
  │       ├─ title (if provided)
  │       ├─ created_at
  │       └─ updated_at
  │
  ├─ ML: summarizer.summarize(text) → summary_string
  │   └─ BART model inference
  │
  ├─ ML: predictor.predict(text, threshold=0.25) → mood_dict
  │   └─ RoBERTa model inference
  │
  ├─ ML: embedder.embed_text(summary) → embedding_vector (384D)
  │   └─ All-MpNet-Base-V2 inference
  │
  ├─ DB: db.insert_analysis(entry_id, summary, mood=mood_probs)
  │   └─ Firestore: INSERT into entry_analysis
  │       ├─ entry_id
  │       ├─ summary
  │       ├─ mood (all 7 emotions)
  │       └─ created_at
  │
  ├─ DB: firebase.collection("journal_embeddings").add(...)
  │   └─ Firestore: INSERT into journal_embeddings
  │       ├─ uid
  │       ├─ entry_id
  │       ├─ embedding (384D array)
  │       └─ created_at
  │
  ├─ DB: Blend user_vectors with journal_embedding
  │   └─ Firestore: UPDATE user_vectors
  │       ├─ movies_vector = 0.95 * old + 0.05 * journal_embedding
  │       ├─ songs_vector = blend
  │       ├─ books_vector = blend
  │       ├─ podcasts_vector = blend
  │       └─ updated_at
  │
  └─ Return: {entry_id, mood, summary, analysis_id, created_at}

Response:
  Status: 200 OK
  Body: {
    "entry_id": "string",
    "created_at": "2025-01-18T10:30:00Z",
    "mood": {
      "anger": 0.05,
      "disgust": 0.02,
      "fear": 0.01,
      "happy": 0.85,
      "neutral": 0.10,
      " sad": 0.01,
      "surprise": 0.01
    },
    "summary": "string",
    "analysis_id": "string"
  }

Error Cases:
  400 → Missing entry_text
  401 → Invalid/missing JWT token
  500 → Model inference failure or DB error
```

---

### GET /api/v1/journal - List Entries

```
HTTP Request:
  Method: GET
  Path: /api/v1/journal
  QueryString: ?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&mood=happy&search=vacation&limit=10&offset=0
  Headers: Authorization: Bearer {JWT_TOKEN}

Route Handler: routes/journal_domain.py:list_journal_entries()
  ├─ Extract: uid = request.user["uid"]
  ├─ Extract: params = {
  │   "start_date": request.args.get("start_date"),
  │   "end_date": request.args.get("end_date"),
  │   "mood": request.args.get("mood"),
  │   "search": request.args.get("search"),
  │   "limit": request.args.get("limit", 50),
  │   "offset": request.args.get("offset", 0)
  │ }
  └─ Call Service:

Service: services/journal_entries/entry_read.py:get_entries_filtered()
  Input: (uid, params, db)
  
  Processing:
  ├─ DB: db.db.collection("journal_entries")
  │       .where("uid", "==", uid)
  │
  ├─ IF start_date:
  │   └─ .where("created_at", ">=", parse_date(start_date))
  │
  ├─ IF end_date:
  │   └─ .where("created_at", "<=", parse_date(end_date))
  │
  ├─ .order_by("created_at", DESCENDING)
  │
  ├─ .offset(offset).limit(limit)
  │
  ├─ FOR each entry_doc:
  │   ├─ entry = entry_doc.to_dict()
  │   ├─ IF mood filter:
  │   │   └─ db.db.collection("entry_analysis")
  │   │       .where("entry_id", "==", entry_doc.id)
  │   │       .limit(1)
  │   │       .stream()
  │   │       ├─ analysis = analysis_doc.to_dict()
  │   │       └─ IF analysis.mood[mood_name] is not defined: skip entry
  │   └─ entry["mood"] = analysis_doc.mood
  │
  └─ Return: [entries_with_analysis], total_count

Database Queries:
  Query 1: SELECT * FROM journal_entries WHERE uid=? ORDER BY created_at DESC
  Query 2 (per entry if mood filter): SELECT mood FROM entry_analysis WHERE entry_id=?

Response:
  Status: 200 OK
  Body: {
    "entries": [
      {
        "entry_id": "string",
        "entry_text": "string",
        "title": "string",
        "created_at": "2025-01-18T10:30:00Z",
        "mood": {emotion_dict},
        "summary": "string"
      }
    ],
    "total_count": 15,
    "returned_count": 10,
    "limit": 10,
    "offset": 0
  }
```

---

### GET /api/v1/journal/search - Search Entries

```
HTTP Request:
  Method: GET
  Path: /api/v1/journal/search
  QueryString: ?query=vacation&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=20
  Headers: Authorization: Bearer {JWT_TOKEN}

Route Handler: routes/journal_domain.py:search_journal_entries()
  ├─ Extract: uid, query, start_date, end_date, limit
  └─ Call Service:

Service: Inline in route (simplified, future: move to service)
  
  Processing:
  ├─ DB: db.db.collection("journal_entries")
  │       .where("uid", "==", uid)
  │
  ├─ IF start_date: .where("created_at", ">=", date)
  ├─ IF end_date: .where("created_at", "<=", date)
  │
  ├─ .order_by("created_at", DESCENDING)
  │ .stream()
  │
  ├─ Post-Filter in Memory:
  │   FOR each doc:
  │     entry = doc.to_dict()
  │     IF query.lower() in entry_text.lower() OR 
  │        query.lower() in summary.lower() OR
  │        query.lower() in title.lower():
  │       ├─ Add to results
  │       └─ Break when limit reached
  │
  └─ Return: matching_entries, total_count

Database Query:
  SELECT * FROM journal_entries WHERE uid=? ORDER BY created_at DESC
  (Text filtering done in-app, not in Firestore for simplicity)

Response:
  Status: 200 OK
  Body: {
    "results": [
      {
        "entry_id": "string",
        "entry_text": "string",
        "summary": "string",
        "created_at": "2025-01-18T10:30:00Z"
      }
    ],
    "total_count": 3,
    "query": "vacation"
  }
```

---

### GET /api/v1/journal/{entry_id} - Get Single Entry

```
HTTP Request:
  Method: GET
  Path: /api/v1/journal/doc123
  Headers: Authorization: Bearer {JWT_TOKEN}

Route Handler: routes/journal_domain.py:get_journal_entry()
  ├─ Extract: entry_id (from URL)
  ├─ Extract: uid (from request.user)
  └─ Call Service:

Service: services/journal_entries/entry_read.py:get_single_entry()
  Input: (entry_id, uid, db)
  
  Processing:
  ├─ DB: db.db.collection("journal_entries")
  │       .document(entry_id)
  │       .get()
  │
  ├─ Check: entry_data.uid == uid (authorization)
  │   └─ If not: return {error: "Unauthorized"}, 403
  │
  ├─ DB: db.db.collection("entry_analysis")
  │       .where("entry_id", "==", entry_id)
  │       .limit(1)
  │       .stream()
  │
  ├─ Combine: entry + analysis
  └─ Return: complete_entry_with_analysis

Database Queries:
  Query 1: SELECT * FROM journal_entries WHERE document_id = entry_id
  Query 2: SELECT * FROM entry_analysis WHERE entry_id = entry_id

Response:
  Status: 200 OK
  Body: {
    "entry_id": "string",
    "entry_text": "string",
    "title": "string",
    "created_at": "2025-01-18T10:30:00Z",
    "updated_at": "2025-01-18T10:35:00Z",
    "mood": {emotion_dict},
    "summary": "string"
  }

Error Cases:
  404 → Entry not found
  403 → Unauthorized (not owner)
```

---

### PUT /api/v1/journal/{entry_id} - Update Entry

```
HTTP Request:
  Method: PUT
  Path: /api/v1/journal/doc123
  Headers: Authorization: Bearer {JWT_TOKEN}
  Body: {
    "entry_text": "string (required)",
    "title": "string (optional)"
  }

Route Handler: routes/journal_domain.py:update_entry()
  └─ Call Service:

Service: services/journal_entries/entry_update.py:update_entry()
  Input: (entry_id, uid, new_entry_text, title, db, predictor, summarizer)
  
  Processing:
  ├─ DB: Verify ownership (entry.uid == uid)
  │
  ├─ DB: db.db.collection("journal_entries")
  │       .document(entry_id)
  │       .update({
  │         "entry_text": new_entry_text,
  │         "title": title,
  │         "updated_at": now
  │       })
  │
  ├─ ML: Re-analyze with new text
  │   ├─ summarizer.summarize(new_text) → new_summary
  │   ├─ predictor.predict(new_text) → new_mood
  │   └─ embedder.embed_text(new_summary) → new_embedding
  │
  ├─ DB: db.db.collection("entry_analysis")
  │       .where("entry_id", "==", entry_id)
  │       .limit(1)
  │       .stream()
  │       └─ UPDATE with: {mood, summary, created_at}
  │
  ├─ DB: Update embeddings:
  │   db.db.collection("journal_embeddings")
  │   .where("entry_id", "==", entry_id)
  │   .limit(1)
  │   .update({embedding, created_at})
  │
  └─ Return: updated_entry_with_new_analysis

Response:
  Status: 200 OK
  Body: {entry with new mood, summary}
```

---

### DELETE /api/v1/journal/{entry_id} - Delete Entry

```
HTTP Request:
  Method: DELETE
  Path: /api/v1/journal/doc123
  Headers: Authorization: Bearer {JWT_TOKEN}

Route Handler: routes/journal_domain.py:delete_entry()
  └─ Call Service:

Service: services/journal_entries/entry_delete.py:delete_entry()
  Input: (entry_id, uid, db)
  
  Processing:
  ├─ DB: Verify ownership
  │
  ├─ DB: db.db.collection("journal_entries")
  │       .document(entry_id)
  │       .delete()
  │
  ├─ DB: db.db.collection("entry_analysis")
  │       .where("entry_id", "==", entry_id)
  │       .stream() → DELETE each doc
  │
  ├─ DB: db.db.collection("journal_embeddings")
  │       .where("entry_id", "==", entry_id)
  │       .stream() → DELETE each doc
  │
  ├─ DB: db.db.collection("insight_entry_mapping")
  │       .where("entry_id", "==", entry_id)
  │       .stream() → DELETE each doc
  │       (Note: insight itself is NOT deleted, only mapping)
  │
  └─ Return: {message: "deleted", entry_id}

Cascade Deletions:
  - entry_analysis documents
  - journal_embeddings documents
  - insight_entry_mapping documents
  (Insights themselves remain, just lose the entry reference)

Response:
  Status: 200 OK
  Body: {
    "message": "Entry deleted successfully",
    "entry_id": "string"
  }
```

---

## Media Recommendations Domain

### GET /api/v1/movies/recommend - Get Recommendations

```
HTTP Request:
  Method: GET
  Path: /api/v1/movies/recommend
  QueryString: ?genre=drama&mood=happy&limit=10&offset=0&sort=default
  Headers: Authorization: Bearer {JWT_TOKEN}

Route Handler: routes/media_domain.py:recommend_movies()
  ├─ Extract: uid, genre, mood, search, sort, limit, offset
  └─ Call Service:

Service: services/media_recommender/recommendation_pipeline.py:get_recommendations()
  Input: (uid, media_type="movies", genre, mood, search, sort, limit, offset)
  
  Processing Steps:
  ├─ Step 1: Build Intent Vector
  │   ├─ DB: db.db.collection("journal_embeddings")
  │   │       .where("uid", "==", uid)
  │   │       .order_by("created_at", DESCENDING)
  │   │       .limit(1)
  │   │       .stream()
  │   │
  │   ├─ ML: IF recent_entry exists:
  │   │       journal_embedding = recent_entry.embedding (384D)
  │   │   ELSE:
  │   │       journal_embedding = zeros(384)
  │   │
  │   ├─ DB: db.db.collection("user_vectors")
  │   │       .document(uid)
  │   │       .get()
  │   │       ├─ taste_vector = user_vectors.movies_vector
  │   │       └─ IF not exists: taste_vector = random_normalized(384)
  │   │
  │   ├─ Math: intent = 0.95 * taste_vector + 0.05 * journal_embedding
  │   │          intent = normalize(intent)
  │   │
  │   └─ Result: intent_vector (384D, unit norm)
  │
  ├─ Step 2: Fetch Candidates (~300-500 items)
  │   ├─ DB: db.db.collection("media_cache_movies")
  │   │       .stream()  # Fetch all
  │   │
  │   ├─ Parse: Extract {id, title, genre, mood_tags, embedding, rating, popularity}
  │   │
  │   └─ Candidates: list[300-500] items with embeddings
  │
  ├─ Step 3: Apply Hard Filters
  │   ├─ IF genre filter:
  │   │   candidates = [c for c in candidates if genre in c.genre]
  │   │
  │   ├─ IF mood filter:
  │   │   candidates = [c for c in candidates if mood in c.mood_tags]
  │   │
  │   ├─ IF search filter:
  │   │   candidates = [c for c in candidates if fuzzy_match(search, c.title) > 75%]
  │   │
  │   └─ IF empty result: use unfiltered candidates (fallback)
  │
  ├─ Step 4: Personalized Ranking (Phase 5)
  │   FOR each candidate:
  │
  │     a) Similarity Score:
  │        similarity = cosine(intent_vector, candidate.embedding)
  │
  │     b) Fetch User Interaction (for MMR + Temporal Decay):
  │        DB: db.db.collection("user_interactions")
  │            .where("uid", "==", uid)
  │            .where("media_id", "==", candidate.id)
  │            .order_by("timestamp", DESCENDING)
  │            .limit(1)
  │            .stream()
  │
  │     c) Temporal Decay:
  │        days_old = (now - interaction.timestamp).days
  │        decay = exp(-0.15 * days_old)
  │
  │     d) Interaction Frequency:
  │        DB: COUNT where uid=? AND media_id=candidate.id
  │        freq_score = count / total_interactions
  │
  │     e) Hybrid Score:
  │        final = 0.5*similarity + 0.2*freq + 0.2*popularity + 0.1*recency - decay
  │
  │   Sort by final_score DESC
  │   Take top (limit + offset) items
  │
  ├─ Step 5: Apply Sorting
  │   IF sort="rating": re-sort by rating DESC
  │   ELIF sort="trending": re-sort by popularity DESC
  │   ELIF sort="recent": re-sort by release_date DESC
  │   ELSE: keep Phase 5 ranking
  │
  ├─ Step 6: Paginate
  │   paginated = sorted_items[offset : offset+limit]
  │
  ├─ Step 7: Strip Internal Fields
  │   FOR each item:
  │     Remove: embedding, similarity_score, raw_analysis
  │
  └─ Return: paginated_items, total_count

Database Queries:
  Query 1: SELECT * FROM journal_embeddings WHERE uid ORDER BY created_at DESC
  Query 2: SELECT * FROM user_vectors WHERE uid
  Query 3: SELECT * FROM media_cache_movies (all)
  Query 4 (per item): SELECT * FROM user_interactions WHERE uid AND media_id
  Query 5 (per item): COUNT FROM user_interactions WHERE uid AND media_id

Response:
  Status: 200 OK
  Body: {
    "media_type": "movies",
    "recommendations": [
      {
        "id": "550",
        "title": "Fight Club",
        "description": "...",
        "genre": ["Drama", "Thriller"],
        "rating": 8.8,
        "popularity": 45.5,
        "image_url": "https://...",
        "year": 1999
      }
    ],
    "total_count": 42,
    "returned_count": 10,
    "offset": 0,
    "limit": 10,
    "filters": {
      "genre": "drama",
      "mood": "happy",
      "search": null,
      "sort": "default"
    }
  }
```

---

## Insights Domain

### POST /api/v1/insights/generate - Generate Insights

```
HTTP Request:
  Method: POST
  Path: /api/v1/insights/generate
  Headers: Authorization: Bearer {JWT_TOKEN}
  Body: {
    "start_date": "2025-01-01",
    "end_date": "2025-01-07"
  }

Route Handler: routes/insights_domain.py:generate_insights()
  └─ Call Service:

Service: services/insights_service/insights_generate.py:generate_insights()
  Input: (user, data, db, enable_llm, enable_insights, insights_predictor)
  
  Processing:
  ├─ Validate: enable_llm=true AND enable_insights=true
  │   └─ IF not: return error 200 (feature disabled)
  │
  ├─ DB: db.db.collection("journal_entries")
  │       .where("uid", "==", uid)
  │       .where("created_at", ">=", start_date)
  │       .where("created_at", "<=", end_date)
  │       .stream()
  │       ├─ entries = list of entry documents
  │       └─ FOR each: fetch analysis (mood, summary)
  │
  ├─ Build LLM Prompt:
  │   ├─ System: "You are an empathetic AI analyst..."
  │   ├─ Context: Entry summaries, mood distribution
  │   ├─ Instruction: "Respond in JSON with goals, progress, ..."
  │   └─ full_prompt = system + context
  │
  ├─ Config: use_gemini = config.ml.insight_generation.use_gemini
  │
  ├─ IF use_gemini=true:
  │   └─ API: POST to Google Gemini API
  │       ├─ Headers: Authorization: Bearer {GOOGLE_API_KEY}
  │       ├─ Body: {contents: [{role: user, parts: [{text: full_prompt}]}]}
  │       ├─ Response: response_json
  │       └─ timeout: 2 seconds
  │
  ├─ ELIF use_gemini=false:
  │   └─ ML: InsightsPredictor.predict(full_prompt)
  │       ├─ Load Qwen2-1.5B model (if not already loaded)
  │       ├─ Tokenize prompt
  │       ├─ Generate with max_tokens=4096, temperature=0.7
  │       ├─ Decode response
  │       └─ timeout: 5 seconds
  │
  ├─ Parse Response:
  │   ├─ Try: json.loads(response)
  │   ├─ Extract: {goals, progress, negative_behaviors, remedies, appreciation, conflicts}
  │   └─ Validate: all required fields present
  │
  ├─ DB: db.db.collection("insights").add({
  │       "uid": uid,
  │       "start_date": start_date,
  │       "end_date": end_date,
  │       "goals": parsed_goals,
  │       "progress": parsed_progress,
  │       "negative_behaviors": parsed_behaviors,
  │       "remedies": parsed_remedies,
  │       "appreciation": parsed_appreciation,
  │       "conflicts": parsed_conflicts,
  │       "raw_response": full_response,
  │       "created_at": now
  │     })
  │   └─ insight_id = new document ID
  │
  ├─ DB: FOR each entry_id in date range:
  │   db.db.collection("insight_entry_mapping").add({
  │     "insight_id": insight_id,
  │     "entry_id": entry_id
  │   })
  │
  └─ Return: cleaned_insights (without raw_response)

Database Operations:
  Query 1: SELECT * FROM journal_entries WHERE uid AND created_at BETWEEN dates
  Query 2 (per entry): SELECT * FROM entry_analysis WHERE entry_id
  Write 1: INSERT into insights
  Write N: INSERT into insight_entry_mapping (one per entry)

Response:
  Status: 200 OK
  Body: {
    "goals": [
      {"title": "Exercise", "description": "Daily morning runs"}
    ],
    "progress": "Good progress on fitness routine",
    "negative_behaviors": "Late night scrolling",
    "remedies": "Set phone curfew at 10 PM",
    "appreciation": "Consistent waking times improving",
    "conflicts": "Work vs personal time"
  }
```

---

## Summary: Typical End-to-End Request Cost (DB calls)

```
Create Entry (POST /api/v1/journal):
  - 1 INSERT journal_entries
  - 1 INSERT entry_analysis
  - 1 INSERT journal_embeddings
  - 1 GET user_vectors
  - 1 UPDATE user_vectors
  = 5 Firestore operations

Get Recommendations (GET /api/v1/movies/recommend?limit=10):
  - 1 GET journal_embeddings (1 document)
  - 1 GET user_vectors (1 document)
  - 1 READ media_cache_movies (all documents, ~300-500)
  - 10 GET user_interactions (per recommended item)
  = ~13 Firestore operations

Generate Insights (POST /api/v1/insights/generate):
  - N GET journal_entries (for date range)
  - N GET entry_analysis (for each entry)
  - 1 INSERT insights
  - N INSERT insight_entry_mapping
  = 2N + 1 operations (typically N=5-20)
```

