# ⚙️ Functional Requirements

## Core Journal Management

### FR1: Create Journal Entry
- **Input**: User ID (from auth), entry_text (required), title (optional)
- **Processing**:
  1. Insert entry into `journal_entries` collection with uid, entry_text, created_at, updated_at
  2. Generate mood probabilities via RoBERTa predictor (if mood_tracking_enabled)
  3. Generate summary via BART summarizer
  4. Generate embeddings via All-MpNet-Base-V2
  5. Store analysis in `entry_analysis` collection
  6. Store embeddings in `journal_embeddings` collection
  7. Update user vectors with journal blending
- **Output**: Entry ID, analysis (mood, summary), created_at timestamp
- **Endpoint**: `POST /api/v1/journal`
- **Status Codes**: 200 (success), 400 (missing field), 401 (auth), 500 (processing error)
- **Fallback**: If mood_tracking disabled, skip mood detection; if models unavailable, use fallback summaries

### FR2: List Journal Entries
- **Input**: User ID (from auth), Optional: start_date, end_date, mood, search, limit (max 100), offset
- **Processing**:
  1. Query `journal_entries` where uid = request.user.uid
  2. Apply date range filter (created_at between dates)
  3. Apply mood filter if provided (via entry_analysis)
  4. Sort by created_at descending
  5. Apply limit/offset pagination
  6. Fetch associated analysis for each entry
- **Output**: List of entries with mood, summary, created_at
- **Endpoint**: `GET /api/v1/journal`
- **Parameters**:
  - start_date: YYYY-MM-DD (inclusive)
  - end_date: YYYY-MM-DD (inclusive)
  - mood: Single mood name (anger, happy, sad, etc.)
  - search: Text search in entry_text
  - limit: 1-100 (default 50)
  - offset: ≥0 (default 0)
- **Response**: JSON array of entries with pagination info (total_count, returned_count)

### FR3: Search Journal Entries
- **Input**: User ID, query (text), Optional: start_date, end_date, limit
- **Processing**:
  1. Query `journal_entries` where uid = request.user.uid
  2. Apply date range filter
  3. Filter by full-text match in entry_text, summary, or title (case-insensitive)
  4. Sort by created_at descending
  5. Paginate with limit (max 50)
- **Output**: List of matching entries
- **Endpoint**: `GET /api/v1/journal/search?query={text}`
- **Parameters**:
  - query: Search string (required)
  - start_date, end_date: Optional date filtering
  - limit: 1-50 (default 20)
- **Response**: Matching entries, exact match count

### FR4: Get Single Entry
- **Input**: User ID, entry_id
- **Processing**:
  1. Fetch entry from `journal_entries` where id=entry_id
  2. Verify uid matches request.user.uid (authorization)
  3. Fetch associated analysis from `entry_analysis`
  4. Include mood, summary, embeddings metadata
- **Output**: Single entry object with full metadata
- **Endpoint**: `GET /api/v1/journal/{entry_id}`
- **Status Codes**: 200 (success), 401 (auth), 403 (forbidden), 404 (not found)

### FR5: Update Entry Content
- **Input**: User ID, entry_id, new_entry_text, Optional: title
- **Processing**:
  1. Fetch existing entry and verify ownership
  2. Update entry_text, title, updated_at in `journal_entries`
  3. Re-run mood detection and summarization
  4. Update analysis in `entry_analysis`
  5. Update embeddings in `journal_embeddings`
- **Output**: Updated entry with new analysis
- **Endpoint**: `PUT /api/v1/journal/{entry_id}`
- **Status Codes**: Same as FR4

### FR6: Delete Entry
- **Input**: User ID, entry_id
- **Processing**:
  1. Verify ownership
  2. Delete from `journal_entries`
  3. Delete associated analysis from `entry_analysis`
  4. Delete embeddings from `journal_embeddings`
  5. Delete insight mappings from `insight_entry_mapping` (if any)
- **Output**: Confirmation message
- **Endpoint**: `DELETE /api/v1/journal/{entry_id}`
- **Cascade**: All related documents deleted automatically

## Mood Detection and Analysis

### FR7: Mood Detection
- **Input**: Journal entry text (up to 512 tokens)
- **Processing**:
  1. Tokenize text using RoBERTa tokenizer
  2. Run through RoBERTa model on CUDA/CPU
  3. Apply sigmoid activation to get probabilities [0, 1]
  4. Compare to threshold (default 0.25)
  5. Return probabilities for all 7 emotions
- **Output**: `{"probabilities": {"anger": 0.05, "disgust": 0.02, ..., "happy": 0.8}, "predictions": {"anger": false, ...}}`
- **Labels**: anger, disgust, fear, happy, neutral, sad, surprise
- **Threshold**: Configurable (default 0.25, min 0, max 1)
- **Latency**: <500ms GPU, <2s CPU

### FR8: Summary Generation
- **Input**: Journal entry text (up to 1024 tokens)
- **Processing**:
  1. Tokenize text using BART tokenizer
  2. Run through BART encoder-decoder with beam search
  3. Generate summary with num_beams=4
  4. Apply length constraints: min_length=20, max_length=128
  5. Decode to string, strip special tokens
- **Output**: Summary string (1-2 sentences)
- **Fallback**: If BART unavailable, truncate entry to 200 chars + "..."
- **Latency**: <1s GPU, <3s CPU

## Insights Generation

### FR9: Generate Insights
- **Input**: User ID, Optional: start_date, end_date
- **Processing**:
  1. Query entries for given date range (or last 7 days default)
  2. Fetch mood distributions and summaries
  3. Build LLM prompt with entry data
  4. Send to Gemini API if use_gemini=true, else use Qwen2
  5. Parse response into structured format
  6. Store in `insights` collection with insight_entry_mapping
- **Output**: Structured insights object with:
  - goals: List of identified goals
  - progress: Progress assessment
  - negative_behaviors: Identified patterns
  - remedies: Suggested improvements
  - appreciation: Positive aspects
  - conflicts: Identified conflicts
- **Endpoint**: `POST /api/v1/insights/generate`
- **Request Body**:
  ```json
  {
    "start_date": "2025-01-01",
    "end_date": "2025-01-07"
  }
  ```
- **Status Codes**: 200 (generated), 400 (bad date format), 500 (generation error)

### FR10: List Insights
- **Input**: User ID, Optional: limit, offset
- **Processing**:
  1. Query `insights` where uid = request.user.uid
  2. Sort by created_at descending
  3. Apply pagination
- **Output**: List of insights with summary info
- **Endpoint**: `GET /api/v1/insights`
- **Parameters**:
  - limit: 1-50 (default 50)
  - offset: ≥0 (default 0)

### FR11: Get Single Insight
- **Input**: User ID, insight_id
- **Processing**:
  1. Verify ownership
  2. Fetch full insight details including goals, progress, behaviors, etc.
  3. Optionally fetch associated entry_ids via insight_entry_mapping
- **Output**: Full insight object
- **Endpoint**: `GET /api/v1/insights/{insight_id}`

### FR12: Delete Insight
- **Input**: User ID, insight_id
- **Processing**:
  1. Verify ownership
  2. Delete insight from `insights`
  3. Delete all mappings from `insight_entry_mapping`
- **Output**: Confirmation
- **Endpoint**: `DELETE /api/v1/insights/{insight_id}`

## Media Recommendations

### FR13: Get Movie Recommendations
- **Input**: User ID, Optional: genre, mood, search, sort, limit, offset
- **Processing**:
  1. Build intent vector from recent journal entries
  2. Fetch candidate movies from `media_cache_movies` (~300 items)
  3. Apply hard filters:
     - Genre filter: Keep matching genres only
     - Mood filter: Mood-tagged items only
     - Search filter: Fuzzy title matching
  4. Apply personalized ranking:
     - Compute cosine similarity to intent vector
     - Apply MMR: λ=0.7 for diversity
     - Apply temporal decay: -15% per day for old interactions
     - Hybrid scoring: 50% similarity, 20% interaction freq, 20% popularity, 10% recency
  5. Apply sort order: default (relevance), rating, trending, recent
  6. Paginate with limit/offset
  7. Strip internal fields (embeddings, similarity)
- **Output**: Normalized response with movies, pagination, filters applied
- **Endpoint**: `GET /api/v1/movies/recommend`
- **Query Params**:
  - genre: Genre filter (optional)
  - mood: Mood filter (optional)
  - search: Search query (optional)
  - sort: default|rating|trending|recent (default: default)
  - limit: 1-100 (default 10)
  - offset: ≥0 (default 0)
- **Response**: JSON with movies array, total_count, applied_filters

### FR14: Get Song Recommendations
- **Input**: User ID, Optional: genre, mood, search, language, sort, limit, offset
- **Processing**: Same pipeline as FR13, with language filter
- **Endpoint**: `GET /api/v1/songs/recommend`
- **Additional Parameter**: language (hindi, english, neutral)

### FR15: Get Book Recommendations
- **Input**: User ID, Optional: genre, mood, search, sort, limit, offset
- **Processing**: Same pipeline as FR13
- **Endpoint**: `GET /api/v1/books/recommend`

### FR16: Get Podcast Recommendations
- **Input**: User ID, Optional: genre, mood, search, language, sort, limit, offset
- **Processing**: Same pipeline as FR13, with language filter
- **Endpoint**: `GET /api/v1/podcasts/recommend`

### FR17: Search Media
- **Input**: User ID, media_type (movies|songs|books|podcasts), search query, Optional: limit
- **Processing**:
  1. Search in media cache for matching items
  2. Fallback to live provider API if cache insufficient
  3. Fuzzy match on title/artist/author
  4. Return top matches
- **Output**: List of matching media items
- **Endpoint**: `GET /api/v1/{media_type}/search?query={search}`
- **Status Codes**: Same as recommendations

### FR18: Track User Interaction
- **Input**: User ID, media_type, media_id, signal (click|save|skip), context (recommendation|search)
- **Processing**:
  1. Validate signal type and media type
  2. Rate limit: max 10 per media type per hour
  3. Store in `user_interactions` with uid, media_type, media_id, signal, timestamp
  4. Update taste vector based on signal weight
  5. Adjust recommendation weights accordingly
- **Output**: Confirmation
- **Endpoint**: `POST /api/v1/media/interaction`
- **Request Body**:
  ```json
  {
    "media_type": "movies",
    "media_id": "550",
    "signal": "save",
    "context": "recommendation"
  }
  ```
- **Signal Weights**:
  - click: 0.02
  - save: 0.05
  - skip: -0.01

## User Management

### FR19: Get User Settings
- **Input**: User ID
- **Processing**:
  1. Fetch user document from `users` collection
  2. Return user settings (mood_tracking_enabled, etc.)
- **Output**: User settings JSON
- **Endpoint**: `GET /api/v1/user/settings`

### FR20: Update User Settings
- **Input**: User ID, settings object (mood_tracking_enabled, etc.)
- **Processing**:
  1. Update `users` document with new settings
  2. Create if doesn't exist
- **Output**: Updated settings
- **Endpoint**: `PUT /api/v1/user/settings`

## Data Export

### FR21: Export User Data
- **Input**: User ID, Optional: format (json|csv|pdf)
- **Processing**:
  1. Fetch all user data (entries, analysis, insights)
  2. Format as requested
  3. Generate downloadable file
- **Output**: File download
- **Endpoint**: `GET /api/v1/export/data?format=json`
- **Formats**: JSON (default), CSV (flat), PDF (formatted)

## System Health

### FR22: Health Check
- **Input**: None
- **Processing**:
  1. Check database connectivity
  2. Check model availability
  3. Return system status
- **Output**: Health status JSON
- **Endpoint**: `GET /api/v1/health`
- **Response**: `{"status": "ok", "models": {...}, "db": "connected"}`

