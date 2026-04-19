# 🏗️ System Architecture

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│              (Flask Routes & Request Handlers)              │
├─────────────────────────────────────────────────────────────┤
│ journal_domain.py │ insights_domain.py │ media_domain.py     │
│ auth.py │ user.py │ health.py │ stats.py │ export_route.py  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│         (Business Logic & Domain Operations)                 │
├─────────────────────────────────────────────────────────────┤
│ ┌──────────────────┐  ┌──────────────────┐                  │
│ │ Journal Entries  │  │ Insights Service │                  │
│ │ Service          │  │                  │                  │
│ ├──────────────────┤  ├──────────────────┤                  │
│ │ process_entry()  │  │ generate_insights│                  │
│ │ get_entries()    │  │ get_insights()   │                  │
│ │ update_entry()   │  │ delete_insight() │                  │
│ │ delete_entry()   │  │                  │                  │
│ └──────────────────┘  └──────────────────┘                  │
│                                                              │
│ ┌──────────────────┐  ┌──────────────────┐                  │
│ │Recommendation    │  │ Search Service   │                  │
│ │Pipeline          │  │                  │                  │
│ ├──────────────────┤  ├──────────────────┤                  │
│ │get_recommendations  │ search_entries()│                  │
│ │_rank_candidates()  │ fuzzy_match()    │                  │
│ │_apply_filters()    │                  │                  │
│ │_apply_sorting()    │                  │                  │
│ └──────────────────┘  └──────────────────┘                  │
│                                                              │
│ ┌──────────────────┐  ┌──────────────────┐                  │
│ │ Media Service    │  │ Stats Service    │                  │
│ │                  │  │                  │                  │
│ └──────────────────┘  └──────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ML Inference Layer                              │
│         (Model Predictions & Analytics)                      │
├─────────────────────────────────────────────────────────────┤
│ SentencePredictor  │ SummarizationPredictor │ InsightsGen   │
│ (RoBERTa v2)       │ (BART-Large-CNN v2)   │ (Gemini/Qwen2)│
│                                                              │
│ EmbeddingService   │                                         │
│ (All-MpNet-Base-V2)│                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Data Access & Persistence Layer                   │
│              (Firestore Operations)                          │
├─────────────────────────────────────────────────────────────┤
│              DBManager (Connection mgmt)                      │
│                                                              │
│ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐   │
│ │ Journal Queries │ │ Analysis Ops    │ │ Insight Ops  │   │
│ └─────────────────┘ └─────────────────┘ └──────────────┘   │
│                                                              │
│ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐   │
│ │ User Management │ │ Interaction Log │ │ Cache Store  │   │
│ └─────────────────┘ └─────────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           External & Cloud Services                          │
├─────────────────────────────────────────────────────────────┤
│ Firebase Admin SDK (Auth, Firestore)                         │
│ Gemini API (Insights)                                        │
│ TMDb API (Movies)                                            │
│ Spotify API (Songs/Podcasts)                                 │
│ Google Books API (Books)                                     │
└─────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Presentation Layer (Routes)

**journal_domain.py** (11 endpoints)
- `POST /api/v1/journal` → create_journal_entry()
- `GET /api/v1/journal` → list_journal_entries()
- `GET /api/v1/journal/search` → search_journal_entries()
- `GET /api/v1/journal/{id}` → get_journal_entry()
- `PUT /api/v1/journal/{id}` → update_entry()
- `DELETE /api/v1/journal/{id}` → delete_entry()
- ... (additional endpoints for reanalysis, etc.)

**insights_domain.py** (4 endpoints)
- `POST /api/v1/insights/generate` → generate_insights()
- `GET /api/v1/insights` → list_insights()
- `GET /api/v1/insights/{id}` → get_insight()
- `DELETE /api/v1/insights/{id}` → delete_insight()

**media_domain.py** (6+ endpoints)
- `GET /api/v1/movies/recommend` → recommend_movies()
- `GET /api/v1/songs/recommend` → recommend_songs()
- `GET /api/v1/books/recommend` → recommend_books()
- `GET /api/v1/podcasts/recommend` → recommend_podcasts()
- `GET /api/v1/{media_type}/search` → search_media()
- `POST /api/v1/media/interaction` → track_interaction()

**System Routes**:
- auth.py: `POST /api/v1/auth/login`
- user.py: `GET/PUT /api/v1/user/settings`
- health.py: `GET /api/v1/health`
- stats.py: `GET /api/v1/stats/...`
- export_route.py: `GET /api/v1/export/data`

### 2. Service Layer

**journal_entries Service Package**
```
journal_entries/
├── entry_create.py      → process_entry(user, data, db, predictor, summarizer)
├── entry_read.py        → get_entries_filtered(), get_single_entry()
├── entry_update.py      → update_entry()
├── entry_delete.py      → delete_entry(), delete_entries_batch()
└── entry_update_content.py → update_entry_content_only()
```

**Workflow: Entry Creation (process_entry)**
```
Input: user, entry_text, title
  ↓
1. Insert entry → Firestore (journal_entries collection)
  ↓
2. Parallel Processing:
   ├─ Summarization: text → BART → summary
   ├─ Mood Detection: text → RoBERTa → emotion probabilities
   └─ Embedding: summary → All-MpNet → 384D vector
  ↓
3. Store Analysis:
   ├─ Analysis doc (entry_analysis): mood + summary
   └─ Embeddings doc (journal_embeddings): vector
  ↓
4. Update User Vector:
   └─ Blend taste_vector + journal_vector → user_vectors
  ↓
Output: entry_id, mood, summary, analysis_id
```

**insights_service Package**
```
insights_service/
└── insights_generate.py → generate_insights(user, data, db, insights_predictor)
                        → get_insights(uid, limit, offset, db)
                        → get_insight(insight_id, uid, db)
                        → delete_insight(insight_id, uid, db)
```

**Workflow: Insight Generation**
```
Input: uid, start_date, end_date
  ↓
1. Query entries for date range
  ↓
2. Build prompt with:
   ├─ Entry texts/summaries
   ├─ Mood distributions
   └─ User context
  ↓
3. Send to LLM:
   ├─ Gemini 2.0 Flash (if use_gemini=true)
   └─ Qwen2-1.5B (if offline)
  ↓
4. Parse response → structured object
  ↓
5. Store in insights + create entry_mappings
  ↓
Output: goals, progress, behaviors, remedies, appreciation, conflicts
```

**Recommendation Pipeline Service**
```
recommendation_pipeline.py
└── get_recommendations(uid, media_type, genre, mood, search, sort, limit, offset)

Workflow:
  ↓
Step 1: Fetch Candidates (~300 items from media_cache_{type})
  ↓
Step 2: Apply Hard Filters
  ├─ Genre filter: Keep items with matching genres
  ├─ Mood filter: Keep mood-tagged items only
  └─ Search filter: Fuzzy text match on title
  ↓
Step 3: Build Intent Vector
  ├─ Fetch recent entries + summaries
  ├─ Generate entry embeddings
  ├─ Blend with user taste vector
  └─ Result: 384D intent vector
  ↓
Step 4: Personalized Ranking (Phase 5)
  ├─ Cosine similarity: intent vs each item
  ├─ Apply MMR: λ=0.7 (relevance vs diversity)
  ├─ Apply temporal decay: -15% per day
  └─ Hybrid scoring: 50% sim + 20% freq + 20% pop + 10% recency
  ↓
Step 5: Apply Sorting
  └─ Options: default, rating, trending, recent
  ↓
Step 6: Paginate & Strip Internal Fields
  └─ Remove embeddings, similarity scores from response
  ↓
Output: Normalized media items with pagination
```

### 3. ML Inference Layer

**Mood Detection (RoBERTa)**
```
ml/inference/mood_detection/roberta/
├── predictor.py         → SentencePredictor class
│   ├── __init__(model_path)
│   ├── _load_model()    → Load RoBERTa from disk/HF
│   ├── predict(text, threshold)
│   └── predict_batch(texts)
└── config.py            → Model config (labels, max_length, etc.)

Inference:
  text (≤512 tokens)
  ├─ Tokenize
  ├─ to_device (GPU/CPU)
  ├─ Forward pass
  ├─ Get logits
  ├─ Sigmoid activation → probabilities [0,1]
  └─ Apply threshold → binary predictions

Output format:
{
  "probabilities": {"anger": 0.05, ..., "happy": 0.8},
  "predictions": {"anger": false, ..., "happy": true},
  "threshold": 0.25
}
```

**Summarization (BART)**
```
ml/inference/summarization/bart/
├── predictor.py         → SummarizationPredictor class
│   ├── __init__(model_path)
│   ├── _load_model()    → Load BART-Large-CNN
│   ├── summarize(text, max_length, min_length, num_beams)
│   └── summarize_batch(texts)
└── config.py            → Generation config

Inference:
  text (≤1024 tokens)
  ├─ Tokenize with padding
  ├─ Generate with beam search (num_beams=4)
  ├─ Constraints:
  │  ├─ min_length: 20
  │  ├─ max_length: 128
  │  ├─ no_repeat_ngram_size: 3
  │  └─ early_stopping: True
  └─ Decode tokens → summary string

Output: 1-2 sentence summary (20-128 tokens)
```

**Embeddings Generation**
```
services/embeddings/
├── __init__.py          → get_embedding_service()
└── embedding_service.py → EmbeddingService class
    ├── __init__()       → Load All-MpNet-Base-V2
    └── embed_text(text) → 384D vector

Model: All-MpNet-Base-V2
  Dimensions: 384
  Parameters: 110M
  Pooling: Mean pooling
  Device: Auto (CUDA/CPU)

Usage:
  summary_text
  ├─ Tokenize
  ├─ Generate embeddings
  ├─ Mean pool → 384D vector
  └─ Store as list[float]
```

**Insights Generation (LLM)**
```
ml/inference/insight_generation/
├── gemini/              → Cloud-based via Gemini API
│   └── insight_analyzer.py
├── qwen2/               → Local LLM (HuggingFace/Ollama)
│   └── insight_analyzer.py
└── __init__.py          → Factory pattern

Configuration:
  use_gemini: true/false
  
Gemini Path (Production):
  ├─ Model: gemini-2.0-flash
  ├─ Latency: <2s per request
  ├─ Prompt: Entry texts + mood + instruction
  └─ Response: JSON-structured insights

Qwen2 Path (Fallback/Offline):
  ├─ Model: Qwen/Qwen2-1.5B-Instruct
  ├─ Backend: HuggingFace or Ollama
  ├─ Latency: <5s per request  
  ├─ Prompt: Same structure as Gemini
  └─ Response: Parsed into structured format

Output Structure:
{
  "goals": [{"title": "", "description": ""}],
  "progress": "...",
  "negative_behaviors": "...",
  "remedies": "...",
  "appreciation": "...",
  "conflicts": "..."
}
```

### 4. Data Persistence Layer

**Collections Diagram**
```
Firestore Database
├── journal_entries (journal_entries)
│   ├── uid (indexed)
│   ├── entry_text
│   ├── title (optional)
│   ├── created_at (indexed)
│   └── updated_at
│
├── entry_analysis
│   ├── entry_id (ref)
│   ├── mood (map of probabilities)
│   ├── summary
│   ├── emotional_state (interpreted)
│   ├── semantic_context (interpreted)
│   ├── temporal_context (interpreted)
│   ├── recommendation_strategy (interpreted)
│   └── created_at
│
├── journal_embeddings
│   ├── uid (indexed)
│   ├── entry_id
│   ├── embedding (array[float], 384D)
│   └── created_at (indexed)
│
├── user_vectors
│   ├── uid (key)
│   ├── movies_vector (array, 384D)
│   ├── songs_vector (array, 384D)
│   ├── books_vector (array, 384D)
│   ├── podcasts_vector (array, 384D)
│   └── updated_at
│
├── insights
│   ├── uid (indexed)
│   ├── start_date
│   ├── end_date
│   ├── goals (array)
│   ├── progress (text)
│   ├── negative_behaviors (text)
│   ├── remedies (text)
│   ├── appreciation (text)
│   ├── conflicts (text)
│   ├── raw_response (text)
│   └── created_at
│
├── insight_entry_mapping
│   ├── insight_id (ref)
│   └── entry_id (ref)
│
├── users
│   ├── uid (key)
│   └── settings (map)
│       └── mood_tracking_enabled (bool)
│
├── user_interactions
│   ├── uid (indexed)
│   ├── media_type (indexed)
│   ├── media_id
│   ├── signal (click/save/skip)
│   ├── context (recommendation/search)
│   └── timestamp (indexed)
│
├── media_cache_movies (media_cache_movies)
│   ├── title
│   ├── genre (array)
│   ├── rating
│   ├── popularity
│   ├── mood_tags (array)
│   ├── embedding (384D)
│   └── last_updated
│
├── media_cache_songs
│   ├── title
│   ├── artist
│   ├── genre (array)
│   ├── language
│   ├── popularity
│   ├── embedding
│   └── last_updated
│
├── media_cache_books
│   └── (similar structure)
│
└── media_cache_podcasts
    └── (similar structure)
```

**DBManager (persistence/db_manager.py)**
```
class DBManager:
  ├── insert_entry(uid, entry_text, title)
  ├── insert_analysis(entry_id, summary/analysis, mood)
  ├── insert_insights(uid, dates, fields, goals, mappings)
  ├── fetch_entries_with_analysis(uid, dates)
  ├── get_entry(entry_id) 
  ├── update_entry(entry_id, new_text)
  ├── delete_entry(entry_id)
  └── ... (more query methods)
```

### 5. Configuration Management

**config.yml Structure**
```yaml
server:
  port: 5000
  debug: true
  
app:
  timezone: Asia/Kolkata
  enable_llm: true
  enable_insights: true
  mood_tracking_enabled_default: true
  
ml:
  mood_detection:
    model_version: v2
    prediction_threshold: 0.25
    labels: [anger, disgust, fear, happy, neutral, sad, surprise]
  summarization:
    model_version: v2
    max_summary_length: 128
  embedding:
    model_name: all-mpnet-base-v2
    embedding_dimension: 384
  insight_generation:
    use_gemini: true
    hf_model_name: Qwen/Qwen2-1.5B-Instruct
    
recommendation:
  ranking:
    use_mmr: true
    mmr_lambda: 0.7
    use_temporal_decay: true
    temporal_decay_rate: 0.15
    
firestore:
  collections:
    journal_entries: journal_entries
    entry_analysis: entry_analysis
    insights: insights
    ...
```

## Data Flow Diagrams

### Entry Creation Flow
```
User Creates Entry
    ↓
POST /api/v1/journal (body: entry_text, title)
    ↓
[Authentication Check] → Verify JWT token
    ↓
[Insert Entry] → Insert into journal_entries collection
    ↓
[Parallel Processing]
├─→ [Mood Detection]
│   ├─ RoBERTa inference
│   └─ Store mood in entry_analysis
│
├─→ [Summarization]
│   ├─ BART inference
│   └─ Store summary in entry_analysis
│
└─→ [Embedding Generation]
    ├─ All-MpNet inference
    └─ Store in journal_embeddings
    
[Blend User Vector]
├─ Fetch existing user_vectors
├─ Blend taste vectors with journal vector
└─ Update user_vectors
    
[Response to User]
└─ 200 OK with entry_id, mood, summary, created_at
```

### Recommendation Request Flow
```
User Requests Recommendations
    ↓
GET /api/v1/movies/recommend?genre=drama&limit=10
    ↓
[Authentication Check]
    ↓
[Build Intent Vector]
├─ Query recent 1 journal entry
├─ Generate embedding from summary
├─ Fetch user taste_vector (movies_vector)
├─ Blend: 95% taste + 5% journal
└─ Result: 384D intent vector
    
[Fetch Candidates]
├─ Query media_cache_movies (~300-500 items)
└─ Return sorted by recency
    
[Apply Filters]
├─ Genre filter: Keep "drama" only
├─ Mood filter: Keep mood-tagged items (if provided)
└─ Search filter: Text matching (if query provided)
    
[Personalized Ranking]
├─ For each candidate:
│  ├─ Cosine similarity(intent, item_embedding)
│  ├─ Apply MMR: λ=0.7
│  ├─ Temporal decay: score *= (1 - 0.15)^days_old
│  └─ Hybrid score: 50% sim + 20% freq + 20% pop + 10% recency
├─ Sort by score descending
└─ Return top k
    
[Apply Sorting]
├─ If sort="default": keep ranked order
├─ If sort="rating": sort by rating_score
└─ If sort="trending": sort by popularity
    
[Paginate]
├─ Return items [offset : offset+limit]
└─ Include total_count
    
[Strip Internal Fields]
├─ Remove embedding arrays
├─ Remove similarity scores
└─ Normalize to schema
    
[Response to User]
└─ 200 OK with movies, total_count, applied_filters
```

### Insights Generation Flow
```
User Requests Insights
    ↓
POST /api/v1/insights/generate (body: start_date, end_date)
    ↓
[Authentication Check]
    ↓
[Query Entries for Date Range]
├─ Query journal_entries WHERE uid=user AND created_at BETWEEN dates
├─ Fetch associated analysis (mood, summary)
└─ Result: 5-100 entries
    
[Build LLM Prompt]
├─ Extract entry texts/summaries
├─ Include mood distributions
├─ Add user context (goals history, etc.)
└─ Create system prompt
    
[LLM Inference]
├─ IF use_gemini=true:
│  ├─ Call Gemini 2.0 Flash API
│  └─ Latency: <2s
│  
└─ IF use_gemini=false:
   ├─ Load Qwen2-1.5B locally
   ├─ Run HuggingFace inference
   └─ Latency: <5s
    
[Parse Response]
├─ Extract JSON fields:
│  ├─ goals: []
│  ├─ progress: ""
│  ├─ negative_behaviors: ""
│  ├─ remedies: ""
│  ├─ appreciation: ""
│  └─ conflicts: ""
└─ Validate structure
    
[Store Insights]
├─ Insert into insights collection
├─ Create insight_entry_mapping for each entry
└─ Set created_at timestamp
    
[Response to User]
└─ 200 OK with structured insights
```

## Deployment Architecture

```
┌──────────────────────────────────────┐
│     Docker Container (Flask App)     │
├──────────────────────────────────────┤
│                                      │
│  Flask (Python 3.10+)               │
│  ├─ Routes (journal, insights, etc) │
│  ├─ Services (business logic)       │
│  ├─ ML Models (loaded at startup)   │
│  └─ DB Connections (pooled)         │
│                                      │
│  Dependencies:                       │
│  ├─ transformers (HF library)       │
│  ├─ torch (PyTorch)                 │
│  ├─ firebase-admin                  │
│  ├─ sentence-transformers           │
│  └─ numpy, scipy                    │
│                                      │
└──────────────────────────────────────┘
           │          │          │
           ▼          ▼          ▼
    ┌─────────┐ ┌────────┐ ┌──────────┐
    │ Firestore │ │ Gemini │ │ TMDb/    │
    │ Database  │ │  API   │ │ Spotify  │
    │           │ │        │ │ APIs     │
    └─────────┘ └────────┘ └──────────┘
```

## Key Design Decisions

| Decision | Rationale | Trade-off |
|----------|-----------|-----------|
| **Eager Model Loading** | Models ready for first request | Startup time ~30s |
| **Parallel ML Inference** | Faster entry processing | Requires multi-GPU or async queuing |
| **Intent Vector Blending** | Balance taste + current mood | Intent less responsive to single entry |
| **Firestore over SQL** | Document flexibility, easy scaling | No complex joins, eventual consistency |
| **Gemini as Primary LLM** | Fast, high quality, fewer resources | Monthly API cost, internet required |
| **Phase 5 Ranking** | State-of-the-art recommendations | Complex math, harder to explain |
| **User Vectors in DB** | Fast recommendation computation | Need continuous update/maintenance |
| **Lazy Service Loading** | Memory efficiency | Higher first-request latency |

## Scaling Strategy

### Horizontal Scaling
- Add more Flask instances behind load balancer
- Firestore scales automatically
- Models cached locally per instance

### Vertical Scaling
- Increase GPU memory for larger batch sizes
- Increase CPU for more concurrent requests

### Caching Strategy
- Media cache: 24-hour TTL, Firestore collection
- User vectors: Persistent, updated on interaction
- Model weights: Local disk, no re-download

### Future Improvements
- Message queue (Cloud Tasks) for async insight generation
- Model serving via TFServing or Triton for scalability
- Batch API for multiple entries
- Recommendation pre-computation for popular users

