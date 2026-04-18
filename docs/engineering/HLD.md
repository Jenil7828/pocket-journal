# HIGH-LEVEL DESIGN (HLD)
## Pocket Journal — AI-Powered Digital Journaling Platform

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## TABLE OF CONTENTS
1. [Module Overview](#module-overview)
2. [Module Responsibilities](#module-responsibilities)
3. [Module Interactions](#module-interactions)
4. [Data Flow Between Modules](#data-flow-between-modules)
5. [Interface Contracts](#interface-contracts)

---

## MODULE OVERVIEW

Pocket Journal is organized into 9 major modules, plus supporting utilities:

```
┌────────────────────────────────────────────────────────────────┐
│                    POCKET JOURNAL MODULES                       │
├─────────────┬──────────────┬─────────────┬──────────────────────┤
│             │              │             │                      │
│   Module 1  │   Module 2   │   Module 3  │     Module 4         │
│  CORE AUTH  │   JOURNAL    │    MOOD     │      INSIGHTS        │
│             │   ENTRIES    │  DETECTION  │                      │
└─────────────┴──────────────┴─────────────┴──────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                    ADDITIONAL MODULES                           │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│              │              │              │                  │
│   Module 5   │   Module 6   │   Module 7   │    Module 8      │
│    MEDIA     │  ANALYTICS   │  DATA EXPORT │  HEALTH & JOBS   │
│     RECS     │  & STATS     │              │                  │
└──────────────┴──────────────┴──────────────┴──────────────────┘

┌────────────────────────────────────────────────────────────────┐
│               SUPPORTING MODULES                                │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│              │              │              │                  │
│  Persistence │   Embeddings │  Personalize │     Search       │
│  & Database  │   Service    │  & Feedback  │     Service      │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

---

## MODULE RESPONSIBILITIES

### Module 1: Authentication & User Management

**Location:** `routes/auth.py`, Firebase Admin SDK  
**Responsibility:** User registration, login, token verification  
**Key Functions:**
- User registration with email/password validation
- OAuth token issuance via Firebase
- Token verification & user context extraction
- Session management (stateless via JWT)

**Dependencies:**
- Firebase Admin SDK
- Python-jose for JWT handling

**Data In/Out:**
- IN: {email, password, display_name}
- OUT: {uid, auth_token, user_document}

---

### Module 2: Journal Entries Management

**Location:** `routes/journal_domain.py`, `services/journal_entries/`  
**Responsibility:** CRUD operations for journal entries  
**Key Functions:**
- Create new entries with title, content, tags
- Retrieve entries with pagination
- Update entry content (metadata tracking)
- Delete entries (cascade delete dependencies)
- Search entries by keyword

**Dependencies:**
- Database Manager (Firestore)
- Entry Analysis Service (for metadata)

**Data In/Out:**
- IN: {title, content, tags, uid}
- OUT: {entry_id, content, mood, summary, created_at, updated_at}

---

### Module 3: Mood Detection Engine

**Location:** `ml/inference/mood_detection/roberta/`  
**Responsibility:** Emotion classification from text  
**Key Functions:**
- Load RoBERTa model from disk or cache
- Tokenize input text (max 128 tokens)
- Run inference on GPU/CPU
- Return probability distribution over 7 emotions

**Models:**
- RoBERTa-base fine-tuned for emotion classification
- Version: v2 (fp16 + ONNX optimized)
- Labels: [anger, disgust, fear, happy, neutral, sad, surprise]

**Performance:**
- Inference time: < 500ms
- Confidence threshold: 0.35

**Data In/Out:**
- IN: text (string)
- OUT: {mood_probs: {anger: 0.x, ..., surprise: 0.x}}

---

### Module 4: Insights Generation Service

**Location:** `services/insights_service/`, `ml/inference/insight_generation/`  
**Responsibility:** Generate personalized insights from entries  
**Key Functions:**
- Aggregate entries for date range
- Build LLM prompt with context
- Call Gemini API or local Qwen2 model
- Parse & validate output
- Store insights in database

**LLM Backends:**
- Primary: Google Gemini (cloud, if use_gemini=true)
- Secondary: Qwen2-1.5B (local, if use_gemini=false)

**Output Structure:**
- goals: [{title, description}]
- progress: string
- negative_behaviors: string
- remedies: string
- appreciation: string
- conflicts: string
- raw_response: string

**Data In/Out:**
- IN: {uid, start_date, end_date, entry_summaries}
- OUT: {insightId, goals[], progress, remedies, ...}

---

### Module 5: Media Recommendation Engine

**Location:** `services/media_recommender/`  
**Responsibility:** Personalized media recommendations  
**Key Functions:**
- Fetch candidates from providers (TMDb, Spotify, Google Books, Podcast API)
- Cache media in Firestore (24h TTL)
- Rank candidates by similarity + popularity
- Apply Phase 5 advanced ranking (MMR, temporal decay, hybrid scoring)
- Log user interactions for feedback loop

**Providers:**
- TMDb: Movies
- Spotify: Songs, Podcasts
- Google Books: Books
- Podcast API: Podcasts

**Ranking Algorithm:**
1. Basic: (similarity × 0.9) + (popularity × 0.1)
2. Advanced Phase 5:
   - Hybrid scores: {sim: 0.5, interaction: 0.2, pop: 0.2, recency: 0.1}
   - MMR diversification (λ=0.7)
   - Temporal decay (0.15/day)

**Data In/Out:**
- IN: {mood, user_id, media_type, top_k}
- OUT: [{title, description, popularity, url, metadata}]

---

### Module 6: Analytics & Statistics Service

**Location:** `routes/stats.py`, `services/stats_service/`  
**Responsibility:** Compute user analytics & visualizations  
**Key Functions:**
- Calculate mood distribution (pie chart data)
- Entry frequency analysis (bar chart data)
- Mood trend analysis (line chart data, regression)
- Writing pattern detection (hour, day-of-week)
- User engagement metrics

**Metrics Computed:**
- Total entries, average length
- Entries per day (last 7/30/90 days)
- Most frequent mood
- Mood trend slope (improving/declining)
- Peak writing hours

**Data In/Out:**
- IN: {uid, start_date, end_date, period}
- OUT: {totalEntries, avgLength, moodDist, trends, patterns}

---

### Module 7: Data Export Service

**Location:** `routes/export_route.py`, `services/export_service/`  
**Responsibility:** Export user data in multiple formats  
**Key Functions:**
- Export as CSV (spreadsheet-friendly)
- Export as JSON (machine-readable)
- Export as PDF (human-readable with formatting)
- Optional include analytics summary
- Support date range filtering

**Formats:**
- CSV: columns = [date, title, content, mood, summary]
- JSON: structured {entries: [], metadata: {}}
- PDF: formatted pages with entries and charts

**Data In/Out:**
- IN: {uid, format, start_date, end_date, include_analytics}
- OUT: File (bytes) + Content-Type header

---

### Module 8: System Health & Background Jobs

**Location:** `routes/health.py`, `routes/jobs.py`, `services/health_service.py`  
**Responsibility:** System monitoring and async job management  
**Key Functions:**
- Health check (Firebase, Database, Models)
- Background job status tracking
- Model loading status
- Service availability reporting

**Health Checks:**
- Database connectivity
- Model availability (mood, summarization, insights)
- External API availability (TMDb, Spotify)
- System memory/CPU

**Data In/Out:**
- IN: None (except job_id for status)
- OUT: {status, services, models, timestamp}

---

### Supporting Module: Persistence & Database

**Location:** `persistence/db_manager.py`, `persistence/database_schema.py`  
**Responsibility:** Database abstraction layer  
**Key Functions:**
- CRUD operations on Firestore collections
- Transaction management
- Query building & filtering
- Schema validation
- Document serialization/deserialization

**Collections Managed:**
- journal_entries
- entry_analysis
- insights
- insight_entry_mapping
- users
- journal_embeddings
- user_interactions
- media_cache_* (4 collections)

**Data In/Out:**
- IN: Queries, document data, filters
- OUT: Documents, aggregations, query results

---

### Supporting Module: Embeddings Service

**Location:** `services/embeddings/`  
**Responsibility:** Text embeddings for similarity matching  
**Key Functions:**
- Load Sentence-Transformers model (all-mpnet-base-v2)
- Generate 384-dimensional embeddings
- Batch embedding for efficiency
- Cache embeddings in journal_embeddings collection

**Model:** all-mpnet-base-v2  
**Dimensions:** 384  
**Usage:** Media recommendation similarity, entry clustering

**Data In/Out:**
- IN: text (string or array)
- OUT: embeddings (float32 array or batch)

---

### Supporting Module: Personalization & Cold Start

**Location:** `services/personalization/`  
**Responsibility:** Handle new users without history  
**Key Functions:**
- Detect cold-start users (< 3 entries)
- Return popular/generic recommendations
- Gradually warm-up as user adds entries
- Default mood fallback

**Strategy:**
- Popular items globally
- High-rated items
- Trending items
- Mood-agnostic fallback

---

### Supporting Module: Search Service

**Location:** `services/search_service/`  
**Responsibility:** Full-text and fuzzy search across media  
**Key Functions:**
- Fuzzy matching on media cache
- Deduplication (fuzzy score > 90)
- Case-insensitive search
- Typo tolerance
- Provider fallback (query live API if cache miss)

**Thresholds:**
- Relevance: 75 (minimum to include)
- Dedup: 90 (consider duplicate)

---

### Supporting Module: Interaction Service

**Location:** `services/interaction_service/`  
**Responsibility:** Track user-media interactions for feedback  
**Key Functions:**
- Log click, save, skip signals
- Track interaction context (recommendation vs search)
- Rate limit per user/hour
- Feed data to recommendation ranking

**Signals & Weights:**
- Click: +0.02
- Save: +0.05
- Skip: -0.01

---

## MODULE INTERACTIONS

### Interaction Graph

```
User   ─────────────────────────┐
        (Authentication)        │
        │                       ▼
        │              ┌───────────────┐
        └──────────────►│  Module 1:    │
                        │  Auth & Users │◄──────┐
                        └───────────────┘       │
                               │                │
                               │                │
        ┌──────────────────────▼──────────────┐│
        │                                      ││
        │    ┌──────────────────────────┐     ││
        │    │  Module 2:               │     ││
        │    │  Journal Entries (CRUD)  │     ││
        │    └────┬─────────────────────┘     ││
        │         │                            ││
        │         ├──────┬─────────┬──────┐   ││
        │         │      │         │      │   ││
        │         ▼      ▼         ▼      ▼   ││
        │      Module 3  Module 4  Embed  │   ││
        │      Mood      Insights  Service│   ││
        │      Detection            │     │   ││
        │      │         │          │     │   ││
        │      │         │          │     │   ││
        │      └─────┬───┴──────────┘     │   ││
        │            │                    │   ││
        │            ▼                    │   ││
        │      ┌────────────────┐         │   ││
        │      │  Persistence & │         │   ││
        │      │  Database      │         │   ││
        │      └────────────────┘         │   ││
        │            │                    │   ││
        │            ▼                    │   ││
        │      ┌────────────────┐         │   ││
        │      │  Firestore     │         │   ││
        │      │  Collections   │         │   ││
        │      └────────────────┘         │   ││
        │                                 │   ││
        └─────────────┬────────────────────┘   ││
                      │                        ││
                      ├──────────────┬─────────┘│
                      │              │         │
                      ▼              ▼         │
              ┌──────────────┐ ┌────────────┐  │
              │ Module 5:    │ │ Module 6:  │  │
              │ Media Recs   │ │ Analytics  │  │
              └──────┬───────┘ └────────────┘  │
                     │              │          │
                     └──────┬───────┘          │
                            │                 │
                            ▼                 │
                  ┌──────────────────┐        │
                  │ External APIs:   │        │
                  │ TMDb, Spotify,   │        │
                  │ Gemini, Books    │        │
                  └──────────────────┘        │
                            │                 │
                            └─────────────────┘
                                   │
                                   ▼
                  ┌──────────────────────┐
                  │ Module 7: Export &   │
                  │ Module 8: Health     │
                  └──────────────────────┘
```

---

## DATA FLOW BETWEEN MODULES

### Flow 1: From Entry Creation to Analytics

```
User Creates Entry
   │
   ├─► Module 1 (Auth)
   │   └─ Verify user token
   │
   ├─► Module 2 (Journal Entries)
   │   ├─ Store entry in database
   │   └─ Generate entry_id
   │
   ├─► [Parallel Execution]
   │   │
   │   ├─► Module 3 (Mood Detection)
   │   │   └─ Generate mood scores
   │   │
   │   ├─► Embeddings Service
   │   │   └─ Generate entry embedding
   │   │
   │   └─► New entry summarization (via BART inference)
   │
   ├─► Database (Persistence)
   │   ├─ Store analysis in entry_analysis
   │   └─ Index embedding in journal_embeddings
   │
   ├─► Module 6 (Analytics)
   │   └─ Update aggregated statistics
   │
   └─► Return to User
       └─ Full entry with mood, summary, embedding
```

### Flow 2: From Request to Recommendations

```
User Requests Media Recommendations
   │
   ├─► Module 1 (Auth)
   │   └─ Verify user token
   │
   ├─► Module 5 (Media Recommender)
   │   │
   │   ├─ Check Search Service cache
   │   │  └─ Query media_cache_* collections
   │   │
   │   ├─[Cache MISS]
   │   │   └─ Call External APIs (TMDb/Spotify/Books)
   │   │      └─ Store results in cache
   │   │
   │   ├─ Apply Ranking:
   │   │   ├─ Get embeddings for mood
   │   │   ├─ Calculate similarity to candidates
   │   │   ├─ Apply Phase 5 ranking (if enabled)
   │   │   └─ Sort by score
   │   │
   │   └─ Return Top K results
   │
   ├─► Interaction Service (optional)
   │   └─ Log user choice (click/save/skip)
   │
   └─► Return to User
       └─ Ranked recommendations list
```

### Flow 3: Insights Generation to Storage

```
User Requests Insights
   │
   ├─► Module 1 (Auth)
   │   └─ Verify user token
   │
   ├─► Database (Persistence)
   │   └─ Retrieve entries + analysis for date range
   │
   ├─► Module 4 (Insights)
   │   │
   │   ├─ Aggregate entry data
   │   ├─ Build LLM prompt
   │   │
   │   ├─ Call LLM Backend
   │   │   ├─[Gemini] → External API call
   │   │   └─[Qwen2]  → Local model inference
   │   │
   │   ├─ Parse output JSON
   │   └─ Validate structure
   │
   ├─► Database (Persistence)
   │   ├─ Store insight in insights collection
   │   └─ Map entries to insight (insight_entry_mapping)
   │
   └─► Return to User
       └─ Insight object with goals, progress, etc.
```

---

## INTERFACE CONTRACTS

### Module 1 → Module 2 Interface
```python
# Input
{
    "uid": "firebase_uid",
    "title": "Entry Title",
    "content": "Entry content text...",
    "tags": ["tag1", "tag2"]
}

# Output
{
    "entry_id": "entry_unique_id",
    "uid": "firebase_uid",
    "title": "Entry Title",
    "content": "...",
    "created_at": "timestamp",
    "updated_at": "timestamp"
}
```

### Module 2 → Module 3 Interface
```python
# Input
{
    "text": "Entry content for analysis"
}

# Output
{
    "mood": {
        "anger": 0.05, "disgust": 0.02, "fear": 0.03,
        "happy": 0.75, "neutral": 0.08, "sad": 0.05, "surprise": 0.02
    },
    "primary_mood": "happy",
    "confidence": 0.75
}
```

### Module 2 → Module 4 Interface
```python
# Input
{
    "uid": "firebase_uid",
    "start_date": "2025-01-01",
    "end_date": "2025-01-07",
    "entries": [{"id": "...", "content": "...", "summary": "..."}]
}

# Output
{
    "insight_id": "insight_unique_id",
    "goals": [{"title": "Goal", "description": "..."}],
    "progress": "Progress description...",
    "negative_behaviors": "...",
    "remedies": "...",
    "appreciation": "...",
    "conflicts": "...",
    "created_at": "timestamp"
}
```

### Module 2 → Module 5 Interface
```python
# Input
{
    "mood": "happy",
    "user_id": "uid",
    "media_type": "movie",
    "top_k": 10,
    "exclude_ids": ["already_seen_ids"]
}

# Output
[
    {
        "id": "movie_id",
        "title": "Movie Title",
        "overview": "...",
        "release_date": "2025-01-01",
        "popularity": 75.5,
        "vote_average": 7.8,
        "poster_path": "...",
        "score": 0.95
    },
    ...
]
```

### Module 2 → Module 6 Interface
```python
# Input
{
    "uid": "firebase_uid",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "period": "month"
}

# Output
{
    "total_entries": 25,
    "avg_length": 250,
    "mood_distribution": {
        "happy": 10, "sad": 5, "angry": 2, "neutral": 8, ...
    },
    "entries_per_day": 0.8,
    "trend": "improving",
    "peak_hours": [20, 21, 22]
}
```

---

**END OF HIGH-LEVEL DESIGN DOCUMENT**

