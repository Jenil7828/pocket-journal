# 📦 Module Breakdown and Responsibilities

## Backend/ Directory Structure

```
Backend/
├── app.py                          # Flask entry point, model initialization
├── config.yml                      # Configuration (YAML)
├── config_loader.py               # Configuration loader with env overrides
├── requirements.txt               # Python dependencies
│
├── routes/                        # HTTP request handlers (11 modules)
│   ├── __init__.py               # Central route registration
│   ├── journal_domain.py         # Journal entry CRUD endpoints (6)
│   ├── insights_domain.py        # Insights generation & retrieval (4)
│   ├── media_domain.py           # Media recommendations & search (6+)
│   ├── auth.py                   # Authentication endpoints
│   ├── user.py                   # User settings
│   ├── health.py                 # Health check
│   ├── stats.py                  # User statistics
│   ├── export_route.py           # Data export
│   ├── home.py                   # Landing page
│   ├── app_meta.py              # App metadata
│   └── jobs.py                   # Background jobs
│
├── services/                      # Business logic layer
│   ├── __init__.py              # Service module exports
│   │
│   ├── journal_entries/         # Journal entry operations
│   │   ├── __init__.py
│   │   ├── entry_create.py      # process_entry() - CREATE with ML
│   │   ├── entry_read.py        # get_entries_filtered(), get_single_entry()
│   │   ├── entry_update.py      # update_entry() - UPDATE with re-analysis
│   │   ├── entry_delete.py      # delete_entry() - DELETE cascade
│   │   └── entry_update_content_only.py # Update text without full re-analysis
│   │
│   ├── insights_service/        # Insight generation
│   │   ├── __init__.py
│   │   └── insights_generate.py # generate_insights(), get_insights(), delete_insight()
│   │
│   ├── media_recommender/       # Recommendation pipeline
│   │   ├── __init__.py
│   │   ├── recommendation_pipeline.py    # get_recommendations() (main)
│   │   ├── recommendation.py            # Legacy recommendation logic
│   │   ├── intent_builder.py            # build_intent_vector()
│   │   ├── enhanced_ranking_engine.py   # rank_candidates_phase5()
│   │   ├── advanced_ranking.py         # MMR, temporal decay, hybrid scoring
│   │   ├── candidate_generator.py       # Fetch candidates from cache
│   │   ├── filter_sort_service.py       # Apply filters & sorting
│   │   ├── search_service.py           # Search across cache + providers
│   │   ├── response_formatter.py       # Format recommendations for client
│   │   ├── response_schema.py          # Schema normalization & validation
│   │   ├── cache_store.py             # Media cache management
│   │   ├── media_recommendations.py    # Link to media package
│   │   ├── cold_start_handler.py      # Handle new users without history
│   │   └── providers/                  # Media provider integrations
│   │       ├── tmdb_provider.py       # TMDb API (movies)
│   │       ├── spotify_provider.py    # Spotify API (music/podcasts)
│   │       ├── google_books_provider.py # Google Books API
│   │       └── podcast_api_provider.py # Podcast API
│   │
│   ├── embeddings/              # Semantic embeddings
│   │   ├── __init__.py
│   │   └── embedding_service.py # All-MpNet-Base-V2 inference
│   │
│   ├── analytics/               # User analytics
│   │   ├── __init__.py
│   │   └── analytics_engine.py  # Mood trends, entry stats
│   │
│   ├── stats_service/           # Statistics aggregation
│   │   ├── __init__.py
│   │   └── stats_service.py     # User statistics & summaries
│   │
│   ├── export_service/          # Data export
│   │   ├── __init__.py
│   │   └── export_service.py    # Export to JSON/CSV/PDF
│   │
│   ├── personalization/         # User preference learning
│   │   ├── __init__.py
│   │   ├── interaction_service.py    # Track user interactions
│   │   ├── taste_vector_service.py   # Update user taste vectors
│   │   ├── cold_start_handler.py    # Initial recommendation for new users
│   │   └── search_service.py         # Semantic search support
│   │
│   ├── media/                   # Media-specific operations
│   │   ├── __init__.py
│   │   └── media_service.py     # Media CRUD & caching
│   │
│   ├── system/                  # System utilities
│   │   ├── __init__.py
│   │   └── health_service.py    # System health checks
│   │
│   └── utils/                   # Service utilities
│       ├── __init__.py
│       ├── cache_utils.py       # Caching utilities
│       ├── suppression.py       # HF library warning suppression
│       └── rate_limiter.py      # Rate limiting for interactions
│
├── ml/                          # Machine learning modules
│   ├── __init__.py
│   │
│   ├── inference/              # Model inference
│   │   ├── mood_detection/
│   │   │   ├── roberta/
│   │   │   │   ├── predictor.py        # SentencePredictor class
│   │   │   │   ├── config.py           # RoBERTa config (labels, threshold, etc.)
│   │   │   │   └── trainer.py          # Training code (optional)
│   │   │   └── v2/ (symlink to models)
│   │   │
│   │   ├── summarization/
│   │   │   ├── bart/
│   │   │   │   ├── predictor.py        # SummarizationPredictor class
│   │   │   │   ├── config.py           # BART config (beam size, lengths, etc.)
│   │   │   │   └── trainer.py          # Training code (optional)
│   │   │   └── v2/ (symlink to models)
│   │   │
│   │   ├── insight_generation/
│   │   │   ├── gemini/
│   │   │   │   └── insight_analyzer.py # InsightsGenerator (Gemini backend)
│   │   │   ├── qwen2/
│   │   │   │   ├── predictor.py        # Qwen2 initialization
│   │   │   │   └── insight_analyzer.py # InsightsGenerator (Qwen2 backend)
│   │   │   └── v1/ (symlink to models)
│   │   │
│   │   └── __init__.py
│   │
│   ├── models/                 # Model weights directory
│   │   ├── mood_detection/
│   │   │   └── roberta/
│   │   │       ├── v1/ (legacy)
│   │   │       └── v2/ (current) [config.json, pytorch_model.bin, ...]
│   │   │
│   │   ├── summarization/
│   │   │   └── bart/
│   │   │       ├── v1/ (legacy)
│   │   │       └── v2/ (current) [config.json, pytorch_model.bin, ...]
│   │   │
│   │   └── insight_generation/
│   │       └── qwen2/
│   │           ├── v1/ [config.json, generation_config.json, model.safetensors, ...]
│   │
│   ├── training/              # Training scripts
│   │   ├── mood_training/
│   │   │   ├── train.py       # RoBERTa fine-tuning
│   │   │   ├── evaluate.py    # Evaluation metrics
│   │   │   ├── data_loader.py # Training data loading
│   │   │   └── losses.py      # Loss functions
│   │   │
│   │   ├── summarization_training/
│   │   │   ├── train.py       # BART fine-tuning
│   │   │   ├── evaluate.py    # ROUGE evaluation
│   │   │   └── data_loader.py
│   │   │
│   │   └── __init__.py
│   │
│   └── utils/                 # ML utilities
│       ├── __init__.py
│       ├── model_loader.py    # resolve_model_path() - Find models
│       ├── preprocessing.py   # Text normalization
│       └── postprocessing.py  # Output cleaning
│
├── persistence/               # Database layer
│   ├── __init__.py
│   ├── db_manager.py         # DBManager class - All Firestore operations
│   │                         # Methods: insert_entry(), insert_analysis(),
│   │                         # fetch_entries_with_analysis(), etc.
│   └── database_schema.py    # DatabaseSchema class - Validation & schema
│
├── utils/                     # Application utilities
│   ├── __init__.py
│   ├── logger.py             # Logger initialization
│   ├── log_formatter.py      # Colored log formatting
│   ├── logging_utils.py      # Log request/response timing
│   ├── firestore_serializer.py # Custom JSON serialization
│   └── __init__.py (exports: extract_dominant_mood(), etc.)
│
├── data/                      # Data directory
│   ├── mood_detection_data/  # Training data (or empty if proprietary)
│   │   ├── train.jsonl
│   │   ├── val.jsonl
│   │   └── test.jsonl
│   │
│   └── summarization_data/   # Training data
│       ├── train.jsonl
│       ├── val.jsonl
│       └── test.jsonl
│
├── scripts/                   # Utility scripts
│   ├── entrypoint.sh         # Docker entrypoint
│   ├── download_models.py    # Download models from GCS/S3
│   └── operational/          # Operational scripts
│       ├── migrate_db.py     # Database migration
│       └── cache_refresh.py  # Refresh media cache
│
├── templates/                 # HTML templates
│   └── home.html             # Landing page template
│
├── secrets/                   # Service account keys (DO NOT COMMIT)
│   ├── pocket-journal-be-firebase-adminsdk-*.json
│   └── gen-lang-client-*.json
│
└── __pycache__/              # Python bytecode (auto-generated)
```

## Module Responsibilities

### Route Layer (routes/)
**Total Endpoints**: 44+ across 11 modules

**Responsibilities**:
- Parse HTTP requests (path, query, body, headers)
- Check authentication via @login_required decorator
- Extract parameters and validate types
- Call appropriate service methods
- Format and return responses (JSON)
- Log request/response for monitoring

**Not Responsible For**:
- Business logic (delegated to services)
- Database operations (delegated to persistence)
- ML model inference (delegated to ml/)

**Key Patterns**:
- Each domain (journal, insights, media) is in separate file
- Routes are thin - mostly parameter passing
- Consistent error handling and status codes
- Response formatting via response_schema.py

---

### Service Layer (services/)

**Journal Entries Service** (services/journal_entries/)
- **Responsibilities**:
  - Insert entries with full ML pipeline
  - Query entries with filtering (date, mood, text)
  - Update entries and re-analyze
  - Delete entries and cascade cleanup
  - Authorize user ownership

- **Key Functions**:
  - `process_entry()` - Create entry + mood + summary + embedding
  - `get_entries_filtered()` - List with optional filtering
  - `get_single_entry()` - Retrieve one entry
  - `update_entry()` - Modify and re-analyze
  - `delete_entry()` - Remove with cascade

- **Dependencies**: db (DBManager), predictor (RoBERTa), summarizer (BART)

**Recommendation Service** (services/media_recommender/)
- **Responsibilities**:
  - Build intent vectors from user history + mood
  - Fetch media candidates from cache
  - Apply filters (genre, mood, search)
  - Rank candidates using Phase 5 algorithm
  - Format response for client

- **Key Functions**:
  - `get_recommendations()` - Main pipeline
  - `build_intent_vector()` - Blend taste + journal
  - `_rank_candidates()` - Phase 5 ranking & MMR
  - `_apply_filters()` - Genre, mood, search
  - `_apply_sorting()` - Sort by rating/trending/etc

- **Dependencies**: db (MediaCacheStore), embedder (All-MpNet)

**Insights Service** (services/insights_service/)
- **Responsibilities**:
  - Fetch entries for date range
  - Build LLM prompt with context
  - Call Gemini or Qwen2 for analysis
  - Parse and validate response
  - Store insights and entry mappings

- **Key Functions**:
  - `generate_insights()` - Main generation
  - `get_insights()` - List user insights
  - `get_insight()` - Get single insight
  - `delete_insight()` - Remove insight

- **Dependencies**: db (DBManager), insights_predictor (Qwen2/Gemini)

**Personalization Service** (services/personalization/)
- **Responsibilities**:
  - Track user interactions (click, save, skip)
  - Update user taste vectors based on feedback
  - Handle cold start (new users without history)
  - Implement rate limiting

- **Key Classes**:
  - `InteractionService` - Track interactions
  - `TasteVectorService` - Update and retrieve taste vectors
  - `ColdStartHandler` - Default recommendations for new users

**Embeddings Service** (services/embeddings/)
- **Responsibilities**:
  - Lazy-load All-MpNet-Base-V2 model
  - Generate 384D embeddings for text
  - Cache model in memory
  - Handle device selection (GPU/CPU)

- **Key Functions**:
  - `get_embedding_service()` - Lazy loader
  - `embed_text()` - Generate embedding vector

---

### ML Layer (ml/)

**Mood Detection** (ml/inference/mood_detection/roberta/)
- **Input**: Journal entry text (≤512 tokens)
- **Output**: 7-emotion probability distribution
- **Model**: RoBERTa-base fine-tuned
- **Class**: `SentencePredictor`
- **Methods**:
  - `predict()` - Single text inference
  - `predict_batch()` - Multiple texts
  - `get_emotion_probabilities()` - Get probabilities only

**Summarization** (ml/inference/summarization/bart/)
- **Input**: Journal entry text (≤1024 tokens)
- **Output**: 20-128 token summary
- **Model**: BART-Large-CNN fine-tuned
- **Class**: `SummarizationPredictor`
- **Methods**:
  - `summarize()` - Generate summary
  - `summarize_batch()` - Batch summarization

**Insight Generation** (ml/inference/insight_generation/)
- **Input**: Prompt with entries + context
- **Output**: Structured JSON with insights
- **Model**: Gemini 2.0 Flash OR Qwen2-1.5B
- **Class**: `InsightsGenerator` (both backends)
- **Methods**:
  - `generate_insights()` - Main generation

**Model Utilities** (ml/utils/)
- `model_loader.py`: `resolve_model_path()` - Find model weights
- `preprocessing.py`: Text normalization before inference
- `postprocessing.py`: Output cleaning

---

### Persistence Layer (persistence/)

**DBManager** (persistence/db_manager.py)
- **Responsibilities**:
  - Initialize Firebase connection
  - Create entries, analysis, insights
  - Query entries with filters
  - Update and delete documents
  - Handle Firestore-specific operations

- **Key Methods**:
  - `insert_entry()` - Create journal entry
  - `insert_analysis()` - Store mood + summary
  - `fetch_entries_with_analysis()` - Get with analysis
  - `get_entry()` - Single entry retrieval
  - `update_entry()` - Modify entry
  - `delete_entry()` - Remove entry

**DatabaseSchema** (persistence/database_schema.py)
- **Responsibilities**:
  - Define collection schemas
  - Validate documents before storage
  - Generate schema examples
  - Provide security rules reference

- **Key Methods**:
  - `get_journal_entry_schema()` - Entry structure
  - `validate_journal_entry()` - Validate before insert
  - `get_collection_rules()` - Firestore security rules

---

### Configuration (config_loader.py)

**Responsibilities**:
- Load YAML configuration
- Override with environment variables
- Provide default values
- Validate required settings

**Key Functions**:
- `get_config()` - Returns global config dict

**Config Sections**:
- server (port, debug, reloader)
- app (timezone, feature flags, defaults)
- logging (log levels)
- ml (models, thresholds, backends)
- recommendation (ranking parameters)
- firestore (collection names)
- cache (media cache settings)

---

### Utilities (utils/)

**logger.py**: Logger initialization for app
**log_formatter.py**: Colored console output
**logging_utils.py**: Helper functions - log_request(), log_response()
**firestore_serializer.py**: JSON serialization for Firestore timestamps
**__init__.py**: Export utility functions like `extract_dominant_mood()`

---

## Module Dependency Graph

```
Routes (thin layer)
  ├─ journal_domain → journal_entries service
  ├─ insights_domain → insights_service
  └─ media_domain → recommendation service

Services (business logic)
  ├─ journal_entries → DBManager, RoBERTa, BART, embedder
  ├─ recommendations → DBManager, intent_builder, ranking_engine, embedder
  ├─ insights → DBManager, LLM (Gemini/Qwen2)
  └─ personalization → DBManager, taste_vector_service

ML (inference)
  ├─ RoBERTa → PyTorch, HuggingFace
  ├─ BART → PyTorch, HuggingFace
  ├─ Sentence-Transformers → PyTorch
  └─ Qwen2 / Gemini API → HuggingFace / Google Cloud

Persistence (Firestore)
  └─ Firebase Admin SDK

Config (global)
  ├─ config.yml (file)
  └─ Environment variables (override)
```

---

## Data Flow Through Modules

### Entry Creation Flow (Complete Path)
```
1. Route: POST /api/v1/journal → journal_domain.create_journal_entry()

2. Service: journal_entries.process_entry()
   ├─ Calls: db.insert_entry() → DBManager
   ├─ Calls: summarizer.summarize() → BART model
   ├─ Calls: predictor.predict() → RoBERTa model
   ├─ Calls: embedder.embed_text() → Sentence-Transformers
   └─ Calls: db.insert_analysis() → DBManager

3. Persistence: Multiple Firestore writes
   ├─ journal_entries collection
   ├─ entry_analysis collection
   ├─ journal_embeddings collection
   └─ user_vectors update

4. Response: Route formats and returns to client
```

---

## Module Communication Patterns

**Dependency Injection**:
- Routes receive deps dict: `{"db": DBManager, "predictor": RoBERTa, ...}`
- Services receive individual dependencies
- ML models lazy-loaded via getter functions

**Error Handling**:
- Each layer catches exceptions
- Logs with context (uid, operation, traceback)
- Returns appropriate HTTP status codes

**Logging**:
- app.py logs startup (models loaded, config, port)
- Routes log request timing via log_request()/log_response()
- Services log operations (entries created, insights generated)
- ML logs model loading, inference timing, device info

**Configuration**:
- Global config loaded once at startup
- All modules access via `from config_loader import get_config`
- Can add new settings without code changes

---

## Module Quality Metrics

| Module | LOC | Dependencies | Testability | Stability |
|--------|-----|--------------|-------------|-----------|
| app.py | 295 | High (26 imports) | Medium (global state) | High |
| journal_domain | 321 | Low (routes only) | High | High |
| recommendations pipeline | 405 | Medium (services) | Medium | Medium |
| RoBERTa predictor | 90 | Medium (PyTorch) | High | High |
| DBManager | 397 | Low (Firestore) | High | High |
| Intent builder | Variable | Medium (embeddings) | Medium | Medium |
| Phase 5 ranking | Variable | Low (math) | High | High |

