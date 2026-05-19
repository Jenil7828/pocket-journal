# SYSTEM ARCHITECTURE DOCUMENT
## Pocket Journal — AI-Powered Digital Journaling Platform

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## TABLE OF CONTENTS
1. [Architecture Overview](#architecture-overview)
2. [Architecture Style](#architecture-style)
3. [Component Diagram](#component-diagram)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Pipelines & Engines](#pipelines--engines)
6. [Integration Points](#integration-points)
7. [Deployment Architecture](#deployment-architecture)

---

## ARCHITECTURE OVERVIEW

Pocket Journal follows a **layered microservices architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────┐
│           Presentation & API Gateway                 │
│  (Flask REST API, Routes, Authentication)            │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────┐
│   Business Logic & Service Layer     │
│  (Services, Domain Logic)            │
└──────────────────┬──────────────────┘
                   │
      ┌────────────┼────────────┬──────────────┐
      │            │            │              │
 ┌────▼──┐  ┌─────▼───┐  ┌────▼──┐  ┌──────▼────┐
 │   ML   │  │Persistence│ │Media  │  │ Analytics │
 │Engine  │  │  Layer    │ │Engine │  │ Service   │
 └────┬──┘  └─────┬───┘  └────┬──┘  └──────┬────┘
      │           │            │           │
      └───────────┼────────────┼───────────┘
                  │
      ┌───────────▼───────────┐
      │   Data Layer          │
      │  (Firestore + Cache)  │
      └───────────────────────┘
```

---

## ARCHITECTURE STYLE

### Adopted Pattern: Layered + Service-Oriented Architecture

**Characteristics:**
- **Separation of Concerns**: Each layer has distinct responsibility
- **Loose Coupling**: Services communicate via well-defined interfaces
- **High Cohesion**: Related functions grouped together
- **Scalability**: Stateless services can be horizontally scaled
- **Testability**: Layers can be tested independently

### Layers

1. **API Layer** (Routes & Entry Points)
   - HTTP request handling (Flask blueprints)
   - Request validation & authentication
   - Response formatting & error handling

2. **Service Layer** (Business Logic)
   - Domain logic implementation
   - Service orchestration
   - Cross-service communication

3. **ML Engine Layer** (Inference)
   - Model loading & inference
   - Preprocessing & postprocessing
   - Result caching

4. **Persistence Layer** (Data Access)
   - Database abstraction (DBManager)
   - CRUD operations
   - Transaction management

5. **External Integration Layer**
   - API clients (TMDb, Spotify, Gemini)
   - Cache providers
   - Authentication (Firebase)

---

## COMPONENT DIAGRAM

### High-Level Component View

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Application (app.py)                   │
│  Dependencies injection, Route registration, Middleware          │
└──────────┬─────────────────────────────────────────────────┬────┘
           │                                                 │
     ┌─────▼─────┐                                    ┌─────▼──────┐
     │   Routes   │                                    │   Auth     │
     │  Package   │                                    │   Layer    │
     │            │                                    │            │
     │ • auth.py  │◄──── login_required decorator ────│  Firebase  │
     │ • journal  │                                    │  Auth      │
     │ • insights │                                    └────────────┘
     │ • media    │
     │ • stats    │
     │ • export   │
     │ • health   │
     └─────┬──────┘
           │
      ┌────▼────────────────────────────────────────┐
      │     Services Package (services/)              │
      ├──────────────────────────────────────────────┤
      │ • journal_entries/                           │
      │   - EntryManager (CRUD)                      │
      │ • insights_service/                          │
      │   - InsightGenerator                         │
      │ • media_recommender/                         │
      │   - RecommendationEngine                     │
      │   - CacheStore                               │
      │ • stats_service/                             │
      │   - StatsCalculator                          │
      │ • embeddings/                                │
      │   - EmbeddingService                         │
      │ • export_service/                            │
      │   - ExportManager                            │
      │ • personalization/                           │
      │   - ColdStartHandler                         │
      │ • search_service/                            │
      │   - SearchEngine                             │
      │ • interaction_service/                       │
      │   - InteractionLogger                        │
      └────┬──────────────────────────────┬──────────┘
           │                              │
      ┌────▼────────────┐      ┌─────────▼──────────┐
      │  ML Inference   │      │  Persistence       │
      │  (ml/)          │      │  Layer (persistence/)
      ├─────────────────┤      ├────────────────────┤
      │ • mood_detectn/ │      │ • db_manager.py    │
      │   RoBERTa       │      │ • database_schema  │
      │ • summarization/│      │ • ORM abstractions │
      │   BART          │      └────────┬───────────┘
      │ • insight_gen/  │               │
      │   Qwen2/Gemini  │      ┌────────▼────────┐
      │ • utils/        │      │   Firestore DB   │
      │   model_loader  │      │   Collections:   │
      └────────┬────────┘      │                  │
               │               │ • journal_entries│
               │               │ • entry_analysis │
               │               │ • insights       │
               │               │ • users          │
               │               │ • embeddings     │
               │               │ • interactions   │
               │               │ • media_cache_*  │
               └───────────────┘
      
      ┌─────────────────────────────────────┐
      │  External API Integrations          │
      ├─────────────────────────────────────┤
      │ • TMDb API (movies)                 │
      │ • Spotify API (songs/podcasts)      │
      │ • Google Books API (books)          │
      │ • Google Gemini API (insights)      │
      │ • Firebase API (authentication)     │
      └─────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---|---|
| **API Routes** | HTTP endpoint handling, request validation | Flask Blueprints |
| **Services** | Business logic orchestration | Python services package |
| **ML Inference** | Model loading, inference execution | Transformers, PyTorch |
| **Persistence** | Database abstraction, CRUD ops | Firestore, Firebase Admin SDK |
| **External APIs** | Third-party integrations | HTTP clients (requests library) |

---

## DATA FLOW ARCHITECTURE

### Flow 1: Create and Analyze Journal Entry

```
User Web/Mobile App
    │
    ├─► POST /api/entries
    │   ├─ Title
    │   ├─ Content
    │   └─ Tags
    │
    ▼
┌──────────────────────────────────────┐
│   routes/journal_domain.py           │
│   (auth check + validation)          │
└────────────┬─────────────────────────┘
             │
             ├─► EntryManager.create_entry()
             │   (services/journal_entries)
             │
             ▼
    ┌────────────────────────┐
    │  Firestore             │
    │  journal_entries       │
    │  collection            │
    └────────────┬───────────┘
                 │
                 ├─► Trigger Analysis Pipeline:
                 │
                 ├─► 1. Mood Detection
                 │      ml/inference/mood_detection/roberta/predictor.py
                 │      ├─ Tokenize (Max 128 tokens)
                 │      ├─ RoBERTa inference (<500ms)
                 │      └─ Output: Mood probabilities
                 │
                 ├─► 2. Summarization
                 │      ml/inference/summarization/bart/predictor.py
                 │      ├─ Tokenize (Max 1024 tokens)
                 │      ├─ BART inference (<1000ms)
                 │      └─ Output: Summary (20-128 tokens)
                 │
                 ├─► 3. Embedding Generation
                 │      services/embeddings/
                 │      ├─ Sentence Transformer inference
                 │      └─ Output: 384-dim vector
                 │
                 └─► 4. Store Analysis
                      Firestore entry_analysis collection
                      └─ {entry_id, summary, mood, created_at}
                      
             ▼
    ┌────────────────────────────────┐
    │  Return to User                │
    │  {entryId, mood, summary,      │
    │   embedding, timestamp}        │
    └────────────────────────────────┘
```

### Flow 2: Get Media Recommendations

```
User Request
    │
    ├─► GET /api/media/recommendations?mood=happy&type=movie
    │
    ▼
┌──────────────────────────────────────┐
│   routes/media_domain.py             │
│   (Extract mood + user context)      │
└────────────┬─────────────────────────┘
             │
             ├─► RecommendationEngine (services/media_recommender/)
             │
             ├─ CHECK: Media Cache
             │  ├─► Firestore media_cache_movies collection
             │  ├─ If HIT (age < 24h):
             │  │   └─ Use cached results
             │  └─ If MISS:
             │      └─ Continue to Step 2
             │
             ├─► 2. Candidate Fetching
             │  ├─ Query TMDb API (trending, popular, etc.)
             │  ├─ Apply filters (popularity > threshold)
             │  └─ Store in cache (Firestore)
             │
             ├─► 3. Ranking Engine
             │  ├─ Similarity Scoring:
             │  │  ├─ Extract mood embeddings
             │  │  ├─ Calculate cosine similarity to each movie
             │  │  └─ Score: (similarity * 0.9) + (popularity * 0.1)
             │  │
             │  ├─ Phase 5 Advanced Ranking:
             │  │  ├─ MMR (Maximal Marginal Relevance)
             │  │  ├─ Temporal decay on interactions
             │  │  ├─ User interaction frequency
             │  │  └─ Hybrid scoring weights
             │  │
             │  └─ Sort and select Top K
             │
             ├─► 4. Diversification (if enabled)
             │  └─ Maximal Marginal Relevance algorithm
             │     └─ Remove genre duplicates
             │
             └─► 5. Track Interaction (Optional)
                services/interaction_service/
                └─ Log to user_interactions collection

             ▼
    ┌────────────────────────────┐
    │  Return Recommendations    │
    │  [{title, overview, rating,│
    │    posterUrl, popularity}] │
    └────────────────────────────┘
```

### Flow 3: Generate Weekly Insights

```
User Request
    │
    ├─► POST /api/insights/generate
    │   ├─ Start Date
    │   └─ End Date
    │
    ▼
┌────────────────────────────────────────┐
│   routes/insights_domain.py            │
│   (Validate date range)                │
└────────────┬──────────────────────────┘
             │
             ├─► InsightGenerator (services/insights_service/)
             │
             ├─► 1. Aggregate Entries
             │  ├─ Query journal_entries (uid=user, date range)
             │  ├─ Join with entry_analysis
             │  └─ Collect: {text, mood, summary}
             │
             ├─► 2. Build Insight Prompt
             │  ├─ Mood distribution
             │  ├─ Common themes
             │  ├─ Emotional patterns
             │  └─ User preferences from history
             │
             ├─► 3. Call LLM Backend
             │  │
             │  ├─[use_gemini=true] ──► Google Gemini API
             │  │  ├─ Call gemini-2.0-flash model
             │  │  ├─ Temperature: 0.7
             │  │  └─ Max tokens: 4096
             │  │
             │  └─[use_gemini=false] ──► Local Qwen2
             │      ml/inference/insight_generation/qwen2/
             │      ├─ Load model (if not cached)
             │      ├─ Tokenize prompt
             │      ├─ Generate with sampling
             │      └─ Detokenize output
             │
             ├─► 4. Parse LLM Output
             │  ├─ Extract JSON-structured insight
             │  ├─ Fields: goals, progress, remedies, conflicts
             │  └─ Fallback: return raw response if parsing fails
             │
             ├─► 5. Store Insight
             │  ├─ Firestore insights collection
             │  ├─ Create document with full insight data
             │  └─ Create mappings (insight_entry_mapping)
             │
             └─► 6. Return Insight
                └─ {insightId, goals, progress, remedies, ...}
```

### Flow 4: Analytics & Statistics

```
User Request
    │
    ├─► GET /api/stats/overview?period=month
    │
    ▼
┌────────────────────────────────────────┐
│   routes/stats.py                      │
│   (Extract period parameter)           │
└────────────┬──────────────────────────┘
             │
             ├─► StatsCalculator (services/stats_service/)
             │
             ├─► 1. Retrieve Raw Data
             │  ├─ Query journal_entries (uid, date range)
             │  └─ Query entry_analysis (mood scores)
             │
             ├─► 2. Compute Metrics
             │  ├─ Total entries count
             │  ├─ Average entry length (chars/count)
             │  ├─ Mood distribution (count per mood)
             │  ├─ Entry frequency (entries per day)
             │  ├─ Peak writing hours
             │  ├─ Mood trends (slope analysis)
             │  └─ Hourly/daily/weekly aggregates
             │
             ├─► 3. Format for Frontend
             │  ├─ Pie chart data (mood distribution)
             │  ├─ Line chart data (mood trends)
             │  ├─ Bar chart data (entry frequency)
             │  └─ Summary KPIs
             │
             └─► Return Dashboard Data
                └─ {totalEntries, avgLength, moodDist, trends, ...}
```

---

## PIPELINES & ENGINES

### Pipeline 1: Entry Processing Pipeline

**Trigger:** User creates/updates journal entry  
**Duration:** 2-3 seconds end-to-end

```
Entry Created
    │
    ├─► Validation Layer
    │   ├─ Content length check (1-5000 chars)
    │   ├─ User ownership verification
    │   └─ Rate limiting check
    │
    ├─► Persistence Layer
    │   ├─ Store in Firestore journal_entries
    │   └─ Generate entry_id
    │
    ├─► Parallel Processing (3 parallel tasks, <500ms each)
    │   │
    │   ├─ Task 1: Mood Detection
    │   │   ├─ Load RoBERTa model
    │   │   ├─ Tokenize text (max 128 tokens)
    │   │   ├─ Run inference
    │   │   └─ Return: 7-class probabilities
    │   │
    │   ├─ Task 2: Summarization
    │   │   ├─ Load BART model
    │   │   ├─ Tokenize text (max 1024 tokens)
    │   │   ├─ Run inference (beam search, num_beams=4)
    │   │   └─ Return: Summary text
    │   │
    │   └─ Task 3: Embedding Generation
    │       ├─ Load Sentence Transformer
    │       ├─ Generate 384-dim embedding
    │       └─ Return: Vector
    │
    ├─► Store Analysis Results
    │   └─ Firestore entry_analysis collection
    │
    └─► Return Full Entry Object
        ├─ Original content
        ├─ Detected mood
        ├─ Generated summary
        ├─ Embedding (if enabled)
        └─ Timestamp
```

### Pipeline 2: Media Recommendation Pipeline

**Trigger:** User requests recommendations  
**Duration:** 1-2 seconds (cache hit) or 2-5 seconds (cache miss)

```
Recommendation Request
    │
    ├─► Input Processing
    │   ├─ Extract mood (if provided)
    │   ├─ Map to media type (movie/song/podcast)
    │   ├─ Get user interactionhistory
    │   └─ Apply cold-start handling if needed
    │
    ├─► Cache Lookup
    │   ├─ Query Firestore media_cache_{type} collection
    │   ├─ Check TTL (max 24 hours)
    │   │
    │   ├─[Cache HIT] ──► Skip to Ranking
    │   │
    │   └─[Cache MISS] ──► Fetch from Provider
    │
    ├─► Provider Fetch (if cache miss)
    │   │
    │   ├─[type=movie] ──► TMDb API
    │   │   ├─ trending_endpoint (recent movies)
    │   │   ├─ Apply mood-based filters
    │   │   ├─ Fetch up to 100 candidates
    │   │   └─ Cache results
    │   │
    │   ├─[type=song] ──► Spotify API
    │   │   ├─ Mood-based playlist search
    │   │   ├─ Language buckets (hindi/english/neutral)
    │   │   ├─ Fetch up to 200 candidates
    │   │   └─ Cache results
    │   │
    │   ├─[type=podcast] ──► Podcast API
    │   │   ├─ Topics + mood-based search
    │   │   ├─ Fetch up to 100 episodes
    │   │   └─ Cache results
    │   │
    │   └─[type=book] ──► Google Books API
    │       ├─ Genre + mood search
    │       ├─ Fetch up to 100 books
    │       └─ Cache results
    │
    ├─► Candidate Refinement
    │   ├─ Apply popularity threshold (min_popularity=1.0)
    │   ├─ Remove duplicates
    │   ├─ Remove already-interacted items
    │   └─ Limit to 500 candidates
    │
    ├─► Ranking Engine
    │   │
    │   ├─[Phase 1-4] ──► Basic Similarity Ranking
    │   │   ├─ Embedding similarity (cosine)
    │   │   ├─ Popularity weighting
    │   │   ├─ Interaction frequency
    │   │   └─ Score = (sim*0.9) + (pop*0.1)
    │   │
    │   └─[Phase 5] ──► Advanced Ranking (if enabled)
    │       ├─ Hybrid Scoring
    │       │  └─ {sim:0.5, interaction:0.2, pop:0.2, recency:0.1}
    │       ├─ MMR Diversification
    │       │  └─ lambda=0.7 (relevance vs diversity)
    │       └─ Temporal Decay
    │           └─ decay_rate=0.15 per day
    │
    ├─► Select Top K Results
    │   ├─ Sort by final score
    │   └─ Limit to top_k (default=10, max=50)
    │
    ├─► Interaction Logging (Optional)
    │   ├─ Log query context
    │   ├─ Store user choice (click/save/skip)
    │   └─ Update user_interactions collection
    │
    └─► Return Results
        └─ {title, description, metadata, rating, url, ...}
```

### Pipeline 3: Insights Generation Pipeline

**Trigger:** User requests insights OR scheduled generation  
**Duration:** 5-30 seconds depending on backend

```
Insight Request
    │
    ├─► Preparation
    │   ├─ Validate date range (min 1 day, max 1 year)
    │   ├─ Retrieve entries & analysis for range
    │   ├─ Check for minimum entries (if < 2, return generic)
    │   └─ Build aggregation summary
    │
    ├─► Context Building
    │   ├─ Mood distribution analysis
    │   ├─ Common themes extraction
    │   ├─ Key phrases identification
    │   ├─ User interaction history
    │   └─ Previous insights for comparison
    │
    ├─► Prompt Engineering
    │   └─ Build structured prompt with sections:
    │       ├─ Date range
    │       ├─ Entry summaries
    │       ├─ Mood patterns
    │       ├─ User history context
    │       └─ Desired output format (JSON)
    │
    ├─► LLM Backend Selection
    │   │
    │   ├─[use_gemini=true] ──► Google Gemini
    │   │   ├─ Call gemini-2.0-flash API
    │   │   ├─ Temperature: 0.7
    │   │   ├─ Max tokens: 4096
    │   │   ├─ Retry up to 2 times on failure
    │   │   └─ Timeout: 30 seconds
    │   │
    │   └─[use_gemini=false] ──► Local Qwen2
    │       ├─ Load model (cached)
    │       ├─ Batch size: 5
    │       ├─ Min tokens: 100, Max: 4096
    │       └─ Generate response
    │
    ├─► Response Parsing
    │   ├─ Extract JSON structure
    │   ├─ Parse goals (array)
    │   ├─ Extract fields: progress, remedies, conflicts
    │   └─ Fallback to raw if parsing fails
    │
    ├─► Storage
    │   ├─ Store in insights collection
    │   ├─ Create mappings (insight_entry_mapping)
    │   └─ Index by user + date
    │
    └─► Return
        └─ {insightId, goals[], progress, remedies, conflicts, ...}
```

---

## INTEGRATION POINTS

### External Service Integrations

| Service | Purpose | Config | Response Time |
|---------|---------|--------|---|
| **Firebase** | Authentication, Database | firebase credentials JSON | < 100ms |
| **TMDb API** | Movie metadata | TMDB_API_KEY, endpoints | < 2s |
| **Spotify API** | Music/Podcast data | SPOTIFY_CLIENT_ID/SECRET | < 2s |
| **Google Books** | Book metadata | GOOGLE_BOOKS_ENDPOINT | < 2s |
| **Google Gemini** | Insight generation | GEMINI_API_KEY | < 30s |
| **Podcast API** | Podcast episodes | Podcast API endpoint | < 2s |

### Internal Service Communication

```
API Routes ──┬──► Journal Services
             ├──► Insight Services
             ├──► Media Services
             ├──► Stats Services
             └──► Export Services
              │
              └──► Database Manager
                   └─► Firestore
```

---

## DEPLOYMENT ARCHITECTURE

### Development Environment
```
Local Machine
├─ Python 3.10+ VENV
├─ Flask dev server (port 5000)
├─ Firestore emulator (optional)
├─ Environment files (.env)
└─ Local model files (optional)
```

### Production Environment (Docker)
```
┌─────────────────────────────────┐
│       Docker Container          │
├─────────────────────────────────┤
│                                 │
│  ┌─────────────────────────────┐│
│  │  Flask Application          ││
│  │  ├─ routes/                 ││
│  │  ├─ services/               ││
│  │  └─ ml/                     ││
│  └──────────┬────────────────┬─┘│
│             │                │  │
│  ┌──────────▼────────┐       │  │
│  │  GPU Runtime      │       │  │
│  │  (NVIDIA CUDA)    │       │  │
│  └───────────────────┘       │  │
│                              │  │
│  ┌──────────────────────────┐│
│  │  Persistent Volumes      ││
│  │  ├─ /secrets/            ││
│  │  └─ /models/             ││
│  └──────────────────────────┘│
│                              │
└─────────────────────────────────┘
        │
        ├─► Port 8080 (exposed)
        │
        └─► Firestore (cloud)
            TMDb, Spotify, Gemini, etc.
```

### Scaling Strategy
- **Horizontal**: Run multiple container instances behind load balancer
- **Vertical**: Increase CPU/Memory per instance
- **Database**: Firestore auto-scales
- **Model Caching**: In-process cache + external cache (Redis optional)

---

**END OF ARCHITECTURE DOCUMENT**

