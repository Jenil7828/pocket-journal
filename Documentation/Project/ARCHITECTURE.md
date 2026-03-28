# Architecture: Pocket Journal Backend

## Architecture Layers

```
┌─────────────────────────────────────────────────────┐
│           Presentation Layer (HTTP)                 │
│    Flask Routes: /api/v1/{auth,entries,media...}   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         Application Layer (Business Logic)          │
│  ├─ Service modules (entries, media, insights)     │
│  ├─ Middleware (auth, logging, error handling)     │
│  └─ Dependency injection (get_db, get_predictor)   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         Domain Layer (Core Services)                │
│  ├─ ML Inference (Mood, Summarization, Insights)  │
│  ├─ Embedding Service (Semantic vectors)          │
│  ├─ Media Recommendation Engine                    │
│  ├─ Search Service (Hybrid cache-first)           │
│  └─ Export & Analytics Services                    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│       Data Access Layer (Persistence)               │
│  ├─ DBManager (Firestore CRUD)                    │
│  ├─ MediaCacheStore (Cache operations)            │
│  └─ Embedding persistence                         │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│         External Integration Layer                  │
│  ├─ Firebase Admin SDK (Auth, Firestore)          │
│  ├─ Media Providers (TMDb, Spotify, Google Books) │
│  └─ LLM APIs (Gemini, Ollama, HuggingFace)       │
└─────────────────────────────────────────────────────┘
```

---

## Service Layer Breakdown

### 1. **Routes (Presentation)**

#### Authentication Routes (`routes/auth.py`)
- `POST /api/v1/auth/create-user`: Register new user
- `POST /api/v1/auth/login`: (Firebase token-based)
- Validates email, password, name
- Returns Firebase UID + user document

#### Journal Entries Routes (`routes/entries.py`)
- `POST /api/v1/entries`: Create new entry
- `GET /api/v1/entries`: List user's entries (paginated)
- `GET /api/v1/entries/<id>`: Fetch single entry
- `GET /api/v1/entries/<id>/analysis`: Fetch mood + summary
- `PUT /api/v1/entries/<id>`: Update entry text
- `DELETE /api/v1/entries/<id>`: Delete single entry
- `DELETE /api/v1/entries/batch`: Batch delete
- `POST /api/v1/entries/<id>/reanalyze`: Re-run ML analysis

#### Media Routes (`routes/media.py`)
- `GET /api/v1/<media_type>/recommend`: Get recommendations
  - Path: `media_type` ∈ {songs, movies, books, podcasts}
  - Query: `limit` (default=10, max=50)
- `GET /api/v1/<media_type>/search`: Search media
  - Query: `query` (required), `language` (optional), `limit`
  - Returns: Results array + metrics (cache_hit, latency)
- `GET /api/v1/media/debug_verify`: Cache statistics

#### Insights Routes (`routes/insights.py`)
- `POST /api/v1/generate_insights`: Generate insights for date range
- `GET /api/v1/insights`: List user's insights (paginated)
- `GET /api/v1/insights/<id>`: Fetch single insight

#### Stats Routes (`routes/stats.py`)
- `GET /api/v1/stats/mood_timeline`: Mood trend over time
- `GET /api/v1/stats/mood_summary`: Today's mood distribution
- `GET /api/v1/stats/frequency`: Entry frequency metrics

#### Export Routes (`routes/export_route.py`)
- `GET /api/v1/export/csv`: Export entries to CSV
- `GET /api/v1/export/json`: Export entries + analysis to JSON

---

### 2. **ML Inference Services**

#### Mood Detection (`ml/inference/mood_detection/roberta/`)
```python
from ml.inference.mood_detection.roberta.predictor import SentencePredictor

predictor = SentencePredictor(model_dir)
result = predictor.predict(text)
# result = {"dominant": "happy", "probabilities": {"anger": 0.01, ...}}
```
- Model: `roberta-base` (fp16-optimized + ONNX)
- Input: Journal entry text
- Output: 7-class emotion distribution
- Threshold: 0.35 (predictions below threshold → "neutral")
- Latency: ~400-500ms per entry

#### Summarization (`ml/inference/summarization/bart/`)
```python
from ml.inference.summarization.bart.predictor import SummarizationPredictor

summarizer = SummarizationPredictor(model_path=model_dir)
summary = summarizer.summarize(text)
```
- Model: `facebook/bart-large-cnn` (fp16-optimized + ONNX)
- Input: Journal entry text
- Output: Summary (20-128 tokens)
- Num beams: 4 (controls diversity)
- Latency: ~1-2s per entry

#### Insight Generation (`ml/inference/insight_generation/qwen2/`)
```python
from ml.inference.insight_generation.qwen2.insight_analyzer import LocalLLM

llm = LocalLLM(backend="huggingface")  # or "ollama"
response = llm.invoke(prompt)
# response = JSON with goals, progress, remedies, etc.
```
- **Qwen2** (local, 1.5B parameters)
  - Backend options: HuggingFace, Ollama
  - Temperature: 0.7
  - Max tokens: 4096
- **Gemini** (cloud, optional)
  - Fallback if local unavailable
  - Model: `gemini-2.0-flash`
  - Max retries: 2

---

### 3. **Embedding Service**

#### Service: `services/embedding_service.py`
```python
from services.embedding_service import get_embedding_service

emb_service = get_embedding_service()
vector = emb_service.embed(text)  # Returns 768-dim vector
```
- Model: `all-mpnet-base-v2` (768 dimensions)
- Cached globally (singleton)
- Used for:
  - Journal entry intent vectors (for recommendations)
  - Media title similarity ranking
- Latency: ~200-300ms per entry

---

### 4. **Media Recommendation Engine**

#### Main Module: `services/media_recommender/recommendation.py`
```python
def recommend_media(uid, media_type, filters=None, fetch_limit=200):
    # Returns: {
    #   "uid": uid,
    #   "media_type": media_type,
    #   "results": [media_item1, ...],
    #   "source": "cache" | "live"
    # }
```

#### Recommendation Pipeline

**Step 1: Build Intent Vector**
- Fetch user's dominant mood (from today's entries)
- Generate embedding from mood + user profile
- Blend weights: Journal 5%, Taste 95%

**Step 2: Query Media Cache**
- Firestore query: media_type + language (if applicable)
- Filter by TTL (24 hours)
- Limit: 200 candidates

**Step 3: Rank Cached Results**
- Similarity score: cosine(intent_vector, media_embedding)
- Popularity score: normalized media popularity metric
- Ranking formula: `0.9 * similarity + 0.1 * popularity`
- Return top 10

**Step 4: Fallback (if cache miss)**
- Call live provider (TMDb, Spotify, Google Books)
- Fetch new candidates
- Rank, deduplicate, format, cache for 24h

#### Media Providers

**TMDbProvider** (`services/media_recommender/providers/tmdb_provider.py`)
- Endpoints: trending, popular, top-rated, upcoming, now-playing
- API Key: `TMDB_API_KEY` (env var)
- Results: Title, release date, overview, poster URL
- Retry: 1 attempt on 5xx

**SpotifyProvider** (`services/media_recommender/providers/spotify_provider.py`)
- Endpoints: search, track details
- Auth: OAuth2 client credentials
- Results: Track name, artist, album, preview URL
- Language support: hindi, english, neutral
- Retry: 1 attempt on 5xx

**GoogleBooksProvider** (`services/media_recommender/providers/books_provider.py`)
- Endpoint: `/books/v1/volumes`
- API Key: `GOOGLE_BOOKS_API_KEY` (env var)
- Results: Title, author, publication date, thumbnail
- Retry: 1 attempt on 5xx

---

### 5. **Search Service**

#### Module: `services/search_service.py`
```python
class SearchService:
    def search(media_type, query, language, limit):
        # 1. Query cache first
        # 2. Fuzzy match on title/metadata
        # 3. Fallback to provider if needed
        # 4. Deduplicate, rank, return with metrics
```

**Cache-First Strategy**
1. Query Firestore media_cache
2. Fuzzy match title/description (RapidFuzz) with threshold 70%
3. If cache results < limit: fetch from live provider
4. Merge, deduplicate (by title), return

**Metrics Returned**
- `cache_hit_count`: Number of results from cache
- `fallback_triggered`: Boolean (true if provider called)
- `cache_latency_ms`: Time to query Firestore
- `provider_latency_ms`: Time to fetch from provider
- `final_result_count`: Total results returned
- `deduplication_count`: Duplicates removed

---

### 6. **Database Layer**

#### DBManager: `persistence/db_manager.py`
```python
class DBManager:
    def insert_entry(uid, entry_text) -> entry_id
    def insert_analysis(entry_id, interpreted_response, raw_analysis)
    def fetch_entries(uid, limit, offset) -> entries
    def fetch_entry_analysis(entry_id) -> analysis
    def fetch_today_entries_with_mood_summary(uid) -> mood_dict
    def insert_insights(uid, start_date, end_date, ...) -> insight_id
    # ... 30+ more methods
```

#### MediaCacheStore: `services/media_recommender/cache_store.py`
```python
class MediaCacheStore:
    def cache_media(media_type, items) -> None
    def get_media(media_type, language) -> items
    def is_cache_fresh(media_type) -> bool
    def clear_expired_cache() -> int  # Returns count deleted
```

---

## Dependency Graph

```
main (app.py)
  ├─ DBManager
  │   └─ Firebase Admin SDK
  ├─ ML Predictors (Mood, Summarization, Insights)
  │   ├─ transformers
  │   ├─ torch (GPU)
  │   └─ sentence-transformers
  ├─ MediaCacheStore
  │   └─ DBManager
  ├─ EmbeddingService
  │   └─ sentence-transformers
  └─ Routes
      ├─ MediaRecommendationService
      │   ├─ EmbeddingService
      │   ├─ MediaCacheStore
      │   └─ Providers (TMDb, Spotify, GoogleBooks)
      ├─ SearchService
      │   ├─ MediaCacheStore
      │   ├─ Providers
      │   └─ RapidFuzz
      ├─ InsightsService
      │   ├─ DBManager
      │   └─ LLM (Qwen2 or Gemini)
      ├─ ExportService
      │   └─ DBManager
      └─ StatsService
          └─ DBManager
```

---

## Design Patterns

### 1. **Singleton Pattern**
- Global `_db`, `_predictor`, `_summarizer`, `_insights_predictor`
- Lazy initialization on first access
- Ensures single model instance in GPU memory

```python
_db = None

def get_db():
    global _db
    if _db is None:
        _db = DBManager(firebase_json_path=...)
    return _db
```

### 2. **Dependency Injection**
- Routes receive dependencies via `deps` dict
- Decouples route logic from service creation

```python
def register(app, deps):
    login_required = deps["login_required"]
    db = deps.get("db")
    # routes can now use injected dependencies
```

### 3. **Factory Pattern**
- Providers (TMDb, Spotify, GoogleBooks) implement `MediaProvider` interface
- `recommend_media` dynamically selects provider based on `media_type`

### 4. **Cache-Aside Pattern**
- Check cache first (media_cache collection)
- If miss → fetch from provider
- Update cache (Firestore TTL-based)
- Return merged results

### 5. **Strategy Pattern**
- Insights generation: Switch between Gemini (cloud) or Qwen2 (local)
- Fallback to HuggingFace if Ollama unavailable

### 6. **Pipeline Pattern**
- Recommendation pipeline: Intent → Fetch → Rank → Deduplicate → Format
- Entry processing: Validate → Mood → Summary → Embedding → Cache

---

## External Integrations

### Firebase
- **Auth**: User registration, token validation
- **Firestore**: All data persistence
- **Configuration**: Credentials from `FIREBASE_CREDENTIALS_PATH` env var

### TMDb API
- **Endpoint**: `https://api.themoviedb.org/3/`
- **Auth**: API key (query param)
- **Rate Limit**: 40 requests/10 seconds (tier-dependent)
- **Supported Operations**: trending, popular, top-rated, search

### Spotify Web API
- **Endpoint**: `https://api.spotify.com/v1/`
- **Auth**: OAuth2 client credentials
- **Rate Limit**: 429 backoff required
- **Supported Operations**: search (tracks, artists), track details

### Google Books API
- **Endpoint**: `https://www.googleapis.com/books/v1/`
- **Auth**: API key (query param)
- **Rate Limit**: 1000 requests/day (free tier)
- **Supported Operations**: volume search, volume details

### Google Gemini (Optional)
- **Endpoint**: LangChain integration
- **Auth**: API key from `GOOGLE_API_KEY` env var
- **Model**: `gemini-2.0-flash`
- **Use Case**: Insight generation fallback

---

## Configuration Management

**Config File**: `Backend/config.yml`
- YAML structure with nested namespaces
- Environment variable overrides via `config_loader.py`
- Supported override types: `str`, `int`, `float`, `bool`

**Example**:
```yaml
ml:
  mood_detection:
    prediction_threshold: 0.35  # Can override with MOOD_PREDICTION_THRESHOLD env var
```

**Loaded via**: `from config_loader import get_config()`
- Cached globally (immutable after first load)
- Raises `FileNotFoundError` if config.yml missing
- Raises `ValueError` if invalid YAML

---

## Error Handling Strategy

### HTTP Errors
- **400**: Validation errors, missing required fields
- **401**: Unauthorized (invalid/expired token)
- **403**: Forbidden (user_id mismatch)
- **404**: Resource not found
- **429**: Rate limited (external provider)
- **500**: Internal server error (log full traceback)

### ML Errors
- Mood/Summarization: Fallback to defaults if model unavailable
- Insights (Qwen2): Fallback to Gemini, then to generic template
- Embeddings: Return zero vector if embedding fails

### Provider Errors
- **Network timeout**: Retry once, then raise RuntimeError
- **401 Unauthorized**: Log warning, no retry
- **429 Rate Limited**: Log warning, return None (cache-only)
- **5xx Server Error**: Retry once, then raise RuntimeError

### Firestore Errors
- Connection: Retry with exponential backoff (Firebase Admin SDK default)
- Authentication: Fail fast (permissions issue)
- Quota exceeded: Return 503 Service Unavailable

---

## Performance Considerations

### Model Optimization
- **ONNX Runtime**: fp16 quantized models for 2x speedup
- **GPU Acceleration**: CUDA 12.1 for PyTorch inference
- **Batch Processing**: Insights generation processes up to 5 entries/batch

### Caching Strategy
- **Media Cache**: 24-hour TTL, Firestore-backed
- **Embeddings Cache**: In-memory (768 dims × N entries)
- **Model Cache**: Global singleton (loaded once, reused)

### Concurrency
- **Intent Builder**: Max 3 workers (concurrent intent vector builds)
- **Flask Workers**: Scale with Gunicorn (4 workers default in Docker)
- **Database**: Firestore auto-scales

### Query Optimization
- Composite indexes on (uid, created_at) for fast entry queries
- TTL on cache documents (auto-deletes expired entries)
- Paginated queries (limit 100 default, max 100)

---

## Scaling Strategy

**Horizontal Scaling**
- Add Gunicorn workers: `WORKERS=8 gunicorn app:app`
- Firestore auto-scales (no manual intervention)
- Cache hits reduce provider API calls (natural rate limit)

**Vertical Scaling**
- Larger GPU (H100 vs V100) for batch insights
- Increase model cache (more concurrent embeddings)

**Optimization Path**
1. Monitor bottleneck via latency metrics
2. If ML inference: upgrade GPU or enable quantization
3. If Firestore: add composite indexes
4. If providers: increase cache TTL or pre-warm popular queries


