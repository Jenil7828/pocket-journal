# 🔄 Data Processing Pipelines

## Entry Processing Pipeline

### Overview
Triggered when user creates or updates a journal entry. Runs in-request synchronously.

### Pipeline Steps

```
1. VALIDATION
   Input: user dict with uid, entry_text (string), title (optional)
   Checks:
   - Missing entry_text? → Return 400
   - uid is None? → Return 401
   └─ Continue if valid
   
2. ENTRY CREATION
   Operation: db.insert_entry(uid, entry_text, title)
   Database:
   - Collection: journal_entries
   - Document: Auto-generated ID
   - Fields: uid, entry_text, title (if provided), created_at, updated_at
   Output: entry_id
   
3. MOOD DETECTION
   Condition: IF mood_tracking_enabled for user (check user.settings)
   Input: entry_text (max 512 tokens)
   Process:
   - RoBERTa tokenizer: text → token IDs
   - RoBERTa model forward pass
   - Sigmoid activation: logits → probabilities [0,1]
   - Apply threshold (0.25): probabilities → binary predictions
   Output: {"probabilities": {7 emotions}, "predictions": {7 emotions}}
   Fallback: If model fails, mood_probs = {}
   
4. SUMMARIZATION  
   Input: entry_text (max 1024 tokens)
   Process:
   - BART tokenizer: Pad to max_length
   - BART encoder-decoder: Generate with beam search (num_beams=4)
   - Length constraints: min=20, max=128 tokens
   - No-repeat n-gram: 3-gram blocking
   - Decode: Token IDs → summary string
   Output: Summary string (1-2 sentences)
   Fallback: If BART fails, return entry_text[:200] + "..."
   
5. EMBEDDING GENERATION
   Input: summary (from step 4)
   Process:
   - Sentence-Transformers tokenizer: text → tokens
   - All-MpNet-Base-V2 model: Generate embeddings
   - Single-text normalization
   - Float32 array: 384 dimensions
   Output: embedding array (list of 384 floats)
   Storage: journal_embeddings collection with uid, entry_id
   
6. ANALYSIS STORAGE
   Operation: db.insert_analysis(entry_id, summary, mood=mood_probs)
   Database:
   - Collection: entry_analysis
   - Fields: entry_id, summary, mood, created_at
   - Optional: emotional_state, semantic_context, temporal_context
   
7. USER VECTOR BLENDING
   Fetch: user_vectors document for uid
   IF user_vectors.{media_type}_vector exists:
     FOR each media_type in [movies, songs, books, podcasts]:
       - existing_vec = user_vectors[{media_type}_vector]
       - blended = 0.95 * existing_vec + 0.05 * journal_embedding
       - normalized = blended / ||blended||
       - Update user_vectors[{media_type}_vector] = normalized
   
8. RESPONSE
   Status: 200 OK
   Body:
   {
     "entry_id": "doc_id",
     "created_at": "2025-01-18T10:30:00Z",
     "mood": { emotion_probs },
     "summary": "Generated summary",
     "analysis_id": "analysis_doc_id"
   }

Total Latency: 1-3 seconds
Critical Path: RoBERTa (500ms) > Embedding (100ms) > DB writes (200ms)

Error Handling:
- Model unavailable: Use fallback (truncated summary)
- DB write failure: Return 500 with retry suggestion
- User settings unavailable: Default to config.mood_tracking_enabled_default
```

## Recommendation Pipeline

### Overview
Triggered for any media type recommendation request. Runs synchronously, targets <500ms response.

### Pipeline Input
```
GET /api/v1/movies/recommend?genre=drama&mood=happy&limit=10&offset=0

Parameters:
- uid: From request.user (via auth)
- media_type: "movies" | "songs" | "books" | "podcasts"
- genre: Optional filter
- mood: Optional filter (emotion name)
- search: Optional filter
- sort: "default" | "rating" | "trending" | "recent"
- limit: 1-100, default 10
- offset: ≥0, default 0
```

### Step 1: Intent Vector Construction
```
Purpose: Build a 384D vector representing current user mood + taste

Process:
a) Fetch Recent Entries
   - Query: journal_entries WHERE uid = {uid}
   - Sort: created_at DESC
   - Limit: 1 (configurable via intent_journal_embedding_fetch_limit)
   - Select: Most recent entry

b) Generate Entry Embeddings
   - IF entry.summary exists:
     - embedding = All-MpNet.embed(entry.summary)
     - Result: 384D vector
   - IF embedding missing:
     - Use zero vector (384 dimensions)

c) Fetch User Taste Vector
   - Query: user_vectors collection, document = uid
   - Field: {media_type}_vector
   - IF not exists: Initialize to zeros

d) Blend Vectors
   - intent_vector = β_taste * taste_vector + β_journal * journal_embedding
   - β_taste = 0.95 (taste_blend_weight)
   - β_journal = 0.05 (journal_blend_weight)
   - Normalize: intent_vector = intent_vector / ||intent_vector||
   
   Result: 384D intent vector representing:
   - 95% historical taste preferences
   - 5% current mood from latest entry

Output: intent_vector (normalized, 384D)
Fallback: If all zeros, use uniform taste vector
```

### Step 2: Candidate Fetching
```
Purpose: Get ~300-500 candidate items to rank

Process:
- Query: media_cache_{media_type} collection
- Fetch: All documents (or limit 500)
- Fields needed:
  - id: Media ID
  - title: Media title
  - genre: Array of genres
  - mood_tags: Array of mood tags (if available)
  - embedding: 384D embedding vector
  - popularity: Numeric score
  - rating: Numeric score
  - {type}_metadata: Additional fields

Filter by Language (songs/podcasts only):
- IF language parameter provided:
  - Keep items WHERE language = {provided}
- IF language not provided:
  - Return mix of languages

Output: List of 300-500 candidate items with embeddings
Fallback: If <50 candidates, log warning but continue
```

### Step 3: Hard Filtering
```
Purpose: Remove items that don't match explicit user criteria

Process:
a) Genre Filter
   IF genre parameter provided:
   - Keep items WHERE genre CONTAINS {genre_param}
   - Return filtered list
   ELSE:
   - Keep all candidates

b) Mood Filter  
   IF mood parameter provided:
   - Keep items WHERE mood_tags CONTAINS {mood_param}
   ELSE:
   - Keep all candidates

c) Search Filter
   IF search parameter provided:
   - Fuzzy match on title, artist, author
   - Similarity threshold: 75%
   - Keep items WHERE fuzzy_score >= threshold
   ELSE:
   - Keep all candidates

d) Duplicate Removal
   - Remove any duplicate media_ids
   - Keep first occurrence

Combined Filter Result:
- filtered_items = candidates
  .filter(genre if provided)
  .filter(mood if provided)
  .filter(search if provided)
  .deduplicate()

Fallback: If NO items remain after all filters:
- Log warning: "all_items_filtered"
- Return full candidates (unfilt ered)

Output: Filtered list (or full list if empty after filtering)
```

### Step 4: Personalization Ranking (Phase 5)
```
Purpose: Rank filtered items by relevance + diversity + temporal decay

For each candidate_item:

a) Cosine Similarity Score
   - similarity = cosine_distance(intent_vector, item_embedding)
   - Range: [−1, 1], goal: maximize to 1
   - Weight: 0.9

b) Apply MMR (Maximal Marginal Relevance)
   - Purpose: Diversify results (avoid redundancy)
   - Formula: MMR_score = λ * similarity − (1−λ) * max_similarity_to_already_selected
   - λ = 0.7 (relevance vs diversity trade-off)
   - Higher λ → more relevant, less diverse
   - Lower λ → more diverse, less relevant
   
c) Temporal Decay
   - Purpose: Reduce score for old user interactions
   - Formula: decayed_score = score * exp(−decay_rate * days_since_interaction)
   - decay_rate = 0.15 per day
   - Example: 7 days old → score * 0.32 (68% reduction)
   - Fetch: last interaction from user_interactions

d) Hybrid Scoring
   - interaction_frequency = count interactions for this media / total interactions
   - popularity_score = item.popularity (0-100)
   - recency_score = 1 / (1 + days_since_last_user_interaction)
   
   Combined:
   final_score = 0.5 * similarity
               + 0.2 * interaction_frequency
               + 0.2 * popularity_score
               + 0.1 * recency_score
               - temporal_decay_penalty

Ranking Iteration:
FOR each candidate (up to max_candidates_for_ranking=500):
  - Calculate similarity
  - Apply MMR if rank > 1
  - Apply temporal decay
  - Calculate hybrid score
  - Store (candidate, score) tuple

Sort by final_score descending
Return top desired_k = limit + offset items

Output: Ranked list with scores
```

### Step 5: Apply Sorting
```
Purpose: Re-sort by user preference after ranking

IF sort = "default":
- Keep ranked order (Phase 5 output)

ELSE IF sort = "rating":
- Sort by item.rating descending
- OR item.popularity descending (fallback)

ELSE IF sort = "trending":
- Sort by item.popularity descending

ELSE IF sort = "recent":
- Sort by item.last_updated or item.release_date descending

Output: Sorted list
```

### Step 6: Pagination
```
Purpose: Return subset of results

Parameters:
- offset: Start position (default 0)
- limit: Count to return (default 10, max 100)

Operation:
- paginated_items = sorted_items[offset : offset+limit]
- total_count = len(sorted_items)
- returned_count = len(paginated_items)

Output:
- Items to return: paginated_items
- Metadata: total_count, offset, limit, returned_count
```

### Step 7: Clean Response (Strip Internal Fields)
```
Purpose: Remove ML-specific fields before returning to client

Remove from each item:
- embedding (384D vector)
- similarity_score
- raw_analysis
- _internal_id

Keep for client:
- id, title, artist/author/director
- genre, rating, popularity
- description, image_url
- External URLs (iTunes, Spotify, Amazon, etc.)

Output: Normalized media items ready for response
```

### Complete Response
```
{
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
    },
    ...
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

Time Complexity:
- Fetch candidates: O(C) where C ≈ 300-500
- Filter: O(C * F) where F ≈ 3 filters, ~0.1ms each
- Rank: O(C * 384) for embedding similarity
- Sort: O(C log C) for Phase 5 sorting
- Total: ~200-400ms for typical requests

## Insights Generation Pipeline

### Input
```
POST /api/v1/insights/generate
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-07"
}
```

### Step 1: Date Validation and Entry Fetching
```
Parse dates: YYYY-MM-DD format
Query: journal_entries WHERE:
  - uid = request.user.uid
  - created_at >= start_date 00:00:00
  - created_at <= end_date 23:59:59
Sort: created_at ascending
Fetch: All entries in range + associated analysis (mood, summary)

Output: List of (entry_id, entry_text, summary, mood_probs) tuples
```

### Step 2: Prompt Construction
```
System Prompt:
"You are an empathetic AI assistant analyzing a user's journal. 
Identify patterns, progress, challenges, and provide constructive insights."

Context Assembly:
- Entry count: N entries
- Date range: start_date to end_date (N days)
- Mood distribution: Aggregate mood probabilities across entries
- Key themes: Extract topics from summaries (TF-IDF or simple)

For each entry (up to 50):
- Entry text or summary
- Associated mood probabilities
- Timestamp

Final Prompt:
```
Analyze the following journal entries from [start_date] to [end_date]:

[ENTRIES with summaries and moods]

Please provide a structured analysis including:
1. Goals: What goals did the user mention or imply?
2. Progress: What progress was made toward goals?
3. Negative Behaviors: What patterns or behaviors should the user work on?
4. Remedies: What specific changes would help?
5. Appreciation: What positive aspects should be celebrated?
6. Conflicts: What internal or external conflicts were identified?

Respond in JSON format.
```

Output: Formatted prompt text
```

### Step 3: LLM Selection and Inference
```
Config Check: use_gemini = config["ml"]["insight_generation"]["use_gemini"]

IF use_gemini = true:
  Backend: Google Gemini 2.0 Flash API
  Model: gemini-2.0-flash
  Request:
    - system_prompt: (from step 2)
    - user_message: entries_context
    - temperature: 0.7
    - max_tokens: 4096
  Response Latency: <2 seconds
  Parsing: Extract JSON from response
  
ELSE:
  Backend: Local Qwen2-1.5B Model
  Loading: Qwen/Qwen2-1.5B-Instruct from HuggingFace or Ollama
  Inference:
    - Input: Prompt text
    - Backend: HuggingFace + PyTorch OR Ollama API
    - Params:
      - max_new_tokens: 4096
      - temperature: 0.7
      - do_sample: true
  Response Latency: <5 seconds
  Parsing: Extract JSON from response

Error Handling:
- IF API fails: Attempt fallback (Gemini fail → Qwen2)
- IF parsing fails: Return error 500
- IF rate limited: Retry with backoff

Output: LLM response string or JSON
```

### Step 4: Response Parsing
```
Expected Format (JSON):
{
  "goals": [
    {"title": "Exercise", "description": "Daily morning runs"},
    {"title": "Reading", "description": "Finish 2 books per month"}
  ],
  "progress": "Good progress on exercise routine, consistent for 3 days",
  "negative_behaviors": "Late night scrolling affecting sleep quality",
  "remedies": "Set phone curfew at 10 PM, establish bedtime routine",
  "appreciation": "Celebrating small wins, improved morning mood",
  "conflicts": "Work deadlines conflicting with personal time"
}

Parsing Steps:
1. Try JSON.parse()
2. IF fails: Extract fields using regex patterns
3. Validate required fields: [goals, progress, negative_behaviors, remedies, appreciation, conflicts]
4. IF missing fields: Fill with defaults ("", [])

Output: Parsed dictionary with guaranteed structure
```

### Step 5: Storage
```
Database Operation:
  Collection: insights
  Fields:
    - uid: request.user.uid
    - start_date: (from request)
    - end_date: (from request)
    - goals: (from parsed response)
    - progress: (from parsed response)
    - negative_behaviors: (from parsed response)
    - remedies: (from parsed response)
    - appreciation: (from parsed response)
    - conflicts: (from parsed response)
    - raw_response: Full LLM response (for debugging)
    - created_at: Current timestamp
    
  Document ID: Auto-generated

  Mappings:
  FOR each entry_id in the date range:
    - Collection: insight_entry_mapping
    - Document fields:
      - insight_id: (ID of just-created insight)
      - entry_id: (ID of journal entry)
    - One mapping per entry

Output: insight_id (document ID)
```

### Step 6: Response to User
```
Status: 200 OK
Body (Clean Response, no raw_response):
{
  "goals": [...],
  "progress": "...",
  "negative_behaviors": "...",
  "remedies": "...",
  "appreciation": "...",
  "conflicts": "..."
}

Optional Additional Fields (if requested):
- insight_id: Created document ID
- created_at: Timestamp
- entry_count: Number of entries analyzed
- date_range: [start_date, end_date]
```

## List/Query Pipelines

### Journal List Pipeline
```
GET /api/v1/journal?start_date=2025-01-01&end_date=2025-01-31&mood=happy&limit=10

1. Parse parameters:
   - limit: clamp to [1, 100]
   - offset: clamp to ≥0
2. Build Firestore query:
   query = collection("journal_entries")
           .where("uid", "==", uid)
   
3. IF start_date: Add filter "created_at >= date"
4. IF end_date: Add filter "created_at <= date"
5. Order by: created_at DESC
6. Limit: limit + offset (for proper pagination)
7. Stream results: Fetch documents
8. IF mood filter: Post-filter by mood.{mood_name} > threshold
9. Paginate: Return [offset : offset+limit]

Output: Entries with mood, summary, created_at
```

## Performance Characteristics

| Pipeline | Latency | Dependencies |
|----------|---------|--------------|
| Entry Processing | 1-3s | DB (100ms) + RoBERTa (500ms) + BART (1s) |
| Recommendation | 200-500ms | Fetch (100ms) + Rank (300ms) + Filter (50ms) |
| Insights | 2-5s | LLM (Gemini 2s ou Qwen2 5s) + Fetch (100ms) |
| Journal List | 100-300ms | DB query + parsing |
| Search | 100-200ms | Firestore filter + text match |

