# Data Flow: Pocket Journal Backend

## 1. Entry Creation & Analysis Pipeline

```
User writes entry
     │
     ▼
POST /api/v1/entries
     │
     ├─ Validate: entry_text not empty
     │
     ├─ Insert into journal_entries
     │   └─ entry_id generated, created_at = NOW()
     │
     ├─ Parallel ML Analysis
     │   ├─ RoBERTa (Mood Detection)
     │   │   └─ Output: mood + probabilities
     │   │
     │   ├─ BART (Summarization)
     │   │   └─ Output: summary (20-128 tokens)
     │   │
     │   └─ sentence-transformers (Embeddings)
     │       └─ Output: 768-dim vector
     │
     ├─ Store analysis in entry_analysis
     │   └─ emotional_state + summary + raw_analysis
     │
     ├─ Store embedding in journal_embeddings
     │   └─ 768-dim vector + model_version
     │
     └─ Return to client
        {
          "entry_id": "...",
          "analysis": {
            "mood": "happy",
            "summary": "..."
          }
        }

Response Time: ~2-2.5 seconds (ML bottleneck)
```

---

## 2. Recommendation Pipeline (Mood-Based)

```
User requests: GET /api/v1/movies/recommend?limit=10
     │
     ├─ Authenticate (Firebase JWT)
     │
     ├─ Fetch today's mood summary for user
     │   └─ Query: entry_analysis where uid=user_id, created_at >= TODAY
     │   └─ Dominant mood determined (or neutral as fallback)
     │
     ├─ Build Intent Vector
     │   ├─ Get user's latest journal embedding
     │   │   └─ journal_embeddings where uid=user_id, limit 1
     │   │
     │   ├─ Get user's taste vector
     │   │   └─ user_vectors where uid=user_id
     │   │
     │   └─ Blend: intent = (journal × 5%) + (taste × 95%)
     │
     ├─ Query Media Cache (Phase 1: Cache-First)
     │   ├─ Firestore: media_cache where media_type="movies", expires_at > NOW()
     │   │
     │   ├─ Rank cached results
     │   │   ├─ similarity_score = cosine(intent_vector, media_embedding)
     │   │   ├─ popularity_score = normalize(media.popularity)
     │   │   └─ final_score = (similarity × 0.9) + (popularity × 0.1)
     │   │
     │   └─ Return top 10 if sufficient cache hits
     │
     ├─ Fallback to Live Provider (Phase 2: if cache miss)
     │   ├─ Call TMDb API (popular, top-rated, trending)
     │   │   └─ Retry: 1 attempt on 5xx
     │   │
     │   ├─ Rank and format results
     │   │
     │   ├─ Cache results in media_cache
     │   │   └─ expires_at = NOW() + 24 hours
     │   │
     │   └─ Return top 10
     │
     └─ Return to client
        {
          "mood": "happy",
          "recommendations": [{title, release_date, poster, ...}],
          "source": "cache" | "live"
        }

Response Time:
  - Cache hit: ~800ms (Firestore query + ranking)
  - Provider fallback: ~2.5s (API latency + ranking)
```

---

## 3. Search Pipeline (Hybrid Cache-First)

```
User searches: GET /api/v1/movies/search?query=Inception&limit=20
     │
     ├─ Authenticate (Firebase JWT)
     │
     ├─ Validate: query not empty
     │
     ├─ Query Cache (Phase 1)
     │   ├─ Firestore: media_cache where media_type="movies", expires_at > NOW()
     │   │   └─ Returns cached movies array
     │   │
     │   ├─ Fuzzy match title/overview against query (RapidFuzz)
     │   │   └─ Threshold: 70% similarity
     │   │   └─ Return matching items
     │   │
     │   └─ metrics.cache_hit_count = count(matched from cache)
     │
     ├─ Fallback Decision
     │   └─ If cache_results < limit:
     │       └─ Trigger provider fetch
     │
     ├─ Provider Fetch (Phase 2: Fallback)
     │   ├─ Call provider search (TMDb, Spotify, etc.)
     │   │   └─ Retry: 1 attempt on 5xx
     │   │
     │   ├─ Fuzzy match results to query
     │   │
     │   └─ metrics.fallback_triggered = true
     │
     ├─ Merge & Deduplicate
     │   ├─ Combine cache + provider results
     │   ├─ Dedupe by title + release_date
     │   │   └─ metrics.deduplication_count = count(removed dupes)
     │   │
     │   └─ Sort by match_score (highest first)
     │
     └─ Return to client
        {
          "searched": "Inception",
          "results": [{title, poster, match_score, ...}],
          "metrics": {
            "cache_hit_count": 5,
            "fallback_triggered": false,
            "cache_latency_ms": 45.2,
            "provider_latency_ms": 0,
            "final_result_count": 10,
            "deduplication_count": 2
          }
        }

Response Time:
  - Cache only: ~300ms (Firestore + fuzzy match)
  - With provider: ~2.5s (provider API + merge)
```

---

## 4. Insight Generation Pipeline

```
User requests: POST /api/v1/generate_insights
  {
    "start_date": "2026-03-01",
    "end_date": "2026-03-29",
    "use_gemini": false
  }
     │
     ├─ Authenticate (Firebase JWT)
     │
     ├─ Validate date range
     │
     ├─ Fetch entries for period
     │   └─ Query: journal_entries where uid=user_id, 
     │            created_at >= start_date AND created_at <= end_date
     │   └─ Limit: 1000 entries
     │
     ├─ Aggregate mood data
     │   ├─ For each entry, fetch analysis
     │   │   └─ Get mood_probs from entry_analysis
     │   │
     │   ├─ Compute mood distribution
     │   │   └─ avg(mood_probs) across all entries
     │   │
     │   └─ Identify patterns
     │       ├─ Dominant moods
     │       ├─ Trend (improving/declining)
     │       └─ Anomalies
     │
     ├─ Prepare LLM Prompt
     │   └─ Template: "User's mood distribution: {agg}. Generate reflection..."
     │
     ├─ Invoke LLM (Phase 1: Local Qwen2)
     │   ├─ Backend: huggingface or ollama
     │   ├─ Model: Qwen2-1.5B-Instruct
     │   ├─ Temperature: 0.7
     │   ├─ Max tokens: 4096
     │   │
     │   └─ Parse JSON response
     │       {
     │         "emotional_state": "...",
     │         "goals": [...],
     │         "progress": "...",
     │         ...
     │       }
     │
     ├─ Fallback: Gemini (Phase 2: if Qwen2 unavailable)
     │   ├─ Invoke gemini-2.0-flash via LangChain
     │   └─ Retry: 2 attempts
     │
     ├─ Store insight in insights collection
     │   └─ Document: {uid, start_date, end_date, emotional_state, ...}
     │
     ├─ Create insight_entry_mapping
     │   └─ Document: {insight_id, entry_ids: [list of entry IDs]}
     │
     └─ Return to client
        {
          "insight_id": "...",
          "emotional_state": "...",
          "goals": [...],
          "progress": "...",
          ...
        }

Response Time: ~4-6 seconds (LLM latency bottleneck)
```

---

## 5. Cache Refresh Pipeline (Background Job)

```
Scheduled Job: Every 6 hours (or on-demand)
     │
     ├─ For each media_type in [movies, songs, books, podcasts]:
     │   │
     │   ├─ For each language in [neutral, hindi, english]:
     │   │   │
     │   │   ├─ Query media_cache
     │   │   │   └─ media_type={type}, language={lang}
     │   │   │
     │   │   ├─ Check freshness
     │   │   │   └─ If expires_at > NOW(): SKIP (still fresh)
     │   │   │   └─ Else: REFRESH
     │   │   │
     │   │   ├─ Fetch fresh media from provider
     │   │   │   ├─ TMDb: trending + popular + top-rated
     │   │   │   ├─ Spotify: language-specific playlists
     │   │   │   └─ Google Books: genre queries
     │   │   │
     │   │   ├─ Compute embeddings for new items
     │   │   │   └─ sentence-transformers(title + description)
     │   │   │
     │   │   ├─ Update media_cache
     │   │   │   └─ media_items = [new items]
     │   │   │   └─ expires_at = NOW() + 24 hours
     │   │   │
     │   │   └─ Log: "Updated cache: {type}/{lang} ({count} items)"
     │   │
     │   └─ End for each language
     │
     ├─ Cleanup expired cache
     │   └─ Delete: media_cache where expires_at < NOW()
     │
     └─ Log job completion

Job Frequency: Every 6 hours (configurable)
Job Duration: ~2-5 minutes (depends on provider availability)
```

---

## 6. Entry Update & Reanalysis Pipeline

```
User updates entry: PUT /api/v1/entries/<entry_id>
  {
    "entry_text": "Updated text..."
  }
     │
     ├─ Authenticate & authorize (verify uid matches)
     │
     ├─ Update journal_entries
     │   └─ entry_text = new_text, updated_at = NOW()
     │
     ├─ Delete old analysis (optional cascade)
     │   └─ Delete entry_analysis for this entry
     │
     ├─ Re-run ML Analysis
     │   ├─ RoBERTa (Mood Detection)
     │   ├─ BART (Summarization)
     │   └─ sentence-transformers (Embeddings)
     │
     ├─ Store new analysis + embeddings
     │
     └─ Return updated entry with new analysis

Alternative: POST /api/v1/entries/<entry_id>/reanalyze
     └─ Re-run ML analysis only (keep entry_text unchanged)

Response Time: ~2-2.5 seconds
```

---

## 7. User Profile & Taste Vector Update

```
Background Job: Daily (or on-entry-creation)
     │
     ├─ For each user (where entry_count > 0):
     │   │
     │   ├─ Fetch recent journal embeddings
     │   │   └─ Limit: 50 latest entries
     │   │
     │   ├─ Compute taste vector (aggregate)
     │   │   └─ taste_vector = mean(embeddings)
     │   │   └─ Normalize (L2)
     │   │
     │   ├─ Update user_vectors
     │   │   ├─ taste_vector = computed_aggregate
     │   │   ├─ entry_count = total_entries
     │   │   └─ last_updated_at = NOW()
     │   │
     │   └─ Log: "Updated taste vector for user {uid}"
     │
     └─ Job complete

Frequency: Daily at midnight or on-demand
Purpose: Enables personalized intent blending for recommendations
```

---

## 8. Export Pipeline (CSV/JSON)

```
User exports: GET /api/v1/export/csv?start_date=...&end_date=...
     │
     ├─ Authenticate
     │
     ├─ Query entries for date range
     │   └─ journal_entries where uid=user_id, 
     │        created_at >= start_date AND created_at <= end_date
     │
     ├─ Optional: Fetch analysis for each entry
     │   └─ entry_analysis for each entry_id
     │
     ├─ Format to CSV
     │   ├─ Columns: Date, EntryText, Mood, Summary
     │   └─ Escape special chars, handle line breaks
     │
     ├─ Stream to client
     │   └─ Content-Type: text/csv
     │   └─ Content-Disposition: attachment; filename="export.csv"
     │
     └─ Return file download

JSON Export: Similar, but outputs JSON array instead
Response Time: ~500ms-2s (depends on entry count)
```

---

## 9. Statistics Aggregation Pipeline

```
User requests: GET /api/v1/stats/mood_timeline?days=30
     │
     ├─ Authenticate
     │
     ├─ Query entries for period
     │   └─ journal_entries where uid=user_id, 
     │        created_at >= (NOW() - 30 days)
     │
     ├─ For each day:
     │   ├─ Fetch entries created on that day
     │   ├─ Aggregate mood distribution
     │   │   └─ avg(mood_probs) for entries on that day
     │   │
     │   ├─ Compute dominant_mood
     │   ├─ Count entries
     │   └─ Compute avg_entry_length
     │
     ├─ Build timeline array
     │   └─ [{date, dominant_mood, entry_count, mood_distribution}, ...]
     │
     └─ Return to client
        {
          "timeline": [...],
          "days": 30
        }

Response Time: ~500ms (Firestore aggregation)
```

---

## 10. Authentication Flow

```
Client Registration:
     │
     ├─ POST /api/v1/auth/create-user
     │   {
     │     "email": "user@example.com",
     │     "password": "...",
     │     "name": "John Doe"
     │   }
     │
     ├─ Backend creates Firebase Auth user
     │   └─ firebase_auth.create_user(email, password, display_name)
     │
     ├─ Store user profile in Firestore
     │   └─ users/{uid}: {email, name, created_at, ...}
     │
     ├─ Initialize user_vectors (empty)
     │   └─ user_vectors/{uid}: {taste_vector: [0,0,...], entry_count: 0}
     │
     └─ Return uid to client

Client Login (Offline):
     │
     ├─ Client uses Firebase SDK locally
     │   └─ firebase.auth().signInWithEmailAndPassword(email, password)
     │
     ├─ Firebase returns idToken (JWT)
     │
     └─ Client includes in all API requests:
        Authorization: Bearer <idToken>

Backend Validation:
     │
     ├─ On each request:
     │   ├─ Extract idToken from Authorization header
     │   ├─ Verify Firebase JWT (signature, expiry)
     │   │   └─ firebase_auth.verify_id_token(idToken)
     │   │
     │   ├─ Extract uid from token
     │   └─ Scope all data queries to uid
     │
     └─ Proceed with request (or return 401 if invalid)

Response Time: ~10ms (JWT verification)
```

---

## Data Flow Timing Summary

| Operation | Latency (p99) | Bottleneck |
|-----------|---------------|-----------|
| Create entry with analysis | 2.5s | ML inference |
| Get recommendations (cache) | 1.0s | Firestore query |
| Get recommendations (provider) | 3.0s | External API |
| Search media | 1.5s | Fuzzy matching |
| Generate insights | 5.0s | LLM inference |
| List entries | 300ms | Firestore query |
| Get stats | 500ms | Aggregation |
| Export (CSV) | 2.0s | Streaming |


