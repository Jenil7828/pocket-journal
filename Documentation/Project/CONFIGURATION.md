# Configuration: Pocket Journal Backend

## Configuration Philosophy

All system parameters are centralized in `config.yml` with environment variable overrides. This enables:
- Development, staging, and production variants
- Runtime tuning without code changes
- Easy rollback (change env var, restart)

**Load Order**:
1. `config.yml` base defaults
2. Environment variable overrides (if specified)
3. Command-line arguments (if applicable)

---

## Configuration File Structure

### `Backend/config.yml`

Located in the Backend directory. Organized into namespaces:

```yaml
server:           # Flask server settings
app:              # Application feature flags
logging:          # Log levels
firestore:        # Firestore collection names
api:              # External API configuration
ml:               # Machine learning settings
recommendation:   # Recommendation engine config
cache:            # Media cache settings
jobs:             # Background job configuration
```

---

## Server Configuration

```yaml
server:
  port: 5000                          # PORT env var
  flask_debug: true                   # FLASK_DEBUG
  disable_reloader: true              # DISABLE_RELOADER (production)
```

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `port` | 5000 | int | Flask HTTP port |
| `flask_debug` | true | bool | Debug mode (dev only) |
| `disable_reloader` | true | bool | Disable auto-reload on changes |

**Environment Variable**:
```bash
export FLASK_PORT=8080
```

---

## Application Flags

```yaml
app:
  timezone: "Asia/Kolkata"                        # APP_TIMEZONE
  enable_llm: true                                # ENABLE_LLM
  enable_insights: true                           # ENABLE_INSIGHTS
  force_color: true                               # FORCE_COLOR
  hf_hub_disable_xet: true                        # HF_HUB_DISABLE_XET
  tf_cpp_min_log_level: "2"                       # TF_CPP_MIN_LOG_LEVEL
  mood_tracking_enabled_default: true             # APP_MOOD_TRACKING_ENABLED_DEFAULT
  summary_fallback_length: 200                    # APP_SUMMARY_FALLBACK_LENGTH
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `timezone` | "Asia/Kolkata" | Timestamp timezone for all records |
| `enable_llm` | true | Enable LLM endpoints |
| `enable_insights` | true | Enable insight generation |
| `force_color` | true | Force colored log output |
| `hf_hub_disable_xet` | true | Disable HuggingFace XET (performance) |
| `tf_cpp_min_log_level` | "2" | TensorFlow verbosity (2=warning) |
| `mood_tracking_enabled_default` | true | Default mood tracking on new entries |
| `summary_fallback_length` | 200 | Fallback summary length if model fails |

**Override Examples**:
```bash
export APP_TIMEZONE="America/New_York"
export ENABLE_INSIGHTS=false
export APP_SUMMARY_FALLBACK_LENGTH=150
```

---

## Logging Configuration

```yaml
logging:
  app_level: "INFO"                   # APP_LOG_LEVEL
  werkzeug_level: "WARNING"           # WERKZEUG_LOG_LEVEL
  firebase_level: "WARNING"           # FIREBASE_LOG_LEVEL
```

| Logger | Default | Environment Var |
|--------|---------|-----------------|
| Pocket Journal | INFO | APP_LOG_LEVEL |
| Werkzeug (Flask) | WARNING | WERKZEUG_LOG_LEVEL |
| Firebase SDK | WARNING | FIREBASE_LOG_LEVEL |

**Valid Log Levels** (in order of verbosity):
```
DEBUG > INFO > WARNING > ERROR > CRITICAL
```

**Example Development Config**:
```yaml
logging:
  app_level: "DEBUG"        # See all details
  werkzeug_level: "INFO"    # See Flask routing
  firebase_level: "DEBUG"   # Debug Firebase calls
```

**Example Production Config**:
```yaml
logging:
  app_level: "INFO"         # Only important events
  werkzeug_level: "ERROR"   # Only errors
  firebase_level: "WARNING" # Only warnings+
```

---

## Firestore Configuration

```yaml
firestore:
  collections:
    journal_entries: "journal_entries"
    entry_analysis: "entry_analysis"
    insights: "insights"
    insight_entry_mapping: "insight_entry_mapping"
    users: "users"
    journal_embeddings: "journal_embeddings"
    user_vectors: "user_vectors"
```

These are **not overridable** via environment (intentional).

| Collection | Purpose |
|-----------|---------|
| `journal_entries` | Raw entry text + metadata |
| `entry_analysis` | Mood, summary, raw ML outputs |
| `insights` | AI-generated reflections |
| `insight_entry_mapping` | Insight → Entry relationships |
| `users` | User profiles |
| `journal_embeddings` | Entry semantic vectors |
| `user_vectors` | Aggregated user taste vectors |

---

## API Configuration

```yaml
api:
  # General request behavior
  request_timeout: 10                 # API_REQUEST_TIMEOUT
  request_max_retries: 1              # API_REQUEST_MAX_RETRIES

  # Pagination defaults
  default_limit: 10                   # API_DEFAULT_LIMIT
  max_limit: 100                      # API_MAX_LIMIT

  # Journal entries
  entries_max_limit: 100              # API_ENTRIES_MAX_LIMIT

  # Google Books provider
  google_books:
    endpoint: "https://www.googleapis.com/books/v1/volumes"
    page_size: 40                     # API_GOOGLE_BOOKS_PAGE_SIZE

  # Spotify provider
  spotify:
    token_endpoint: "https://accounts.spotify.com/api/token"
    search_endpoint: "https://api.spotify.com/v1/search"
    track_endpoint: "https://api.spotify.com/v1/tracks"

  # TMDb provider
  tmdb:
    trending_endpoint: "https://api.themoviedb.org/3/trending/movie/week"
    popular_endpoint: "https://api.themoviedb.org/3/movie/popular"
    toprated_endpoint: "https://api.themoviedb.org/3/movie/top_rated"
    max_pages: 5                      # API_TMDB_MAX_PAGES
    results_per_page: 20              # API_TMDB_RESULTS_PER_PAGE
    default_max_results: 10           # API_TMDB_DEFAULT_MAX_RESULTS
    mood_movies_limit: 12             # API_TMDB_MOOD_MOVIES_LIMIT
```

| Setting | Default | Type | Purpose |
|---------|---------|------|---------|
| `request_timeout` | 10 | seconds | HTTP request timeout for providers |
| `request_max_retries` | 1 | int | Retry attempts on 5xx errors |
| `default_limit` | 10 | int | Default pagination limit |
| `max_limit` | 100 | int | Maximum pagination limit |

**Environment Variable Examples**:
```bash
export API_REQUEST_TIMEOUT=20
export API_REQUEST_MAX_RETRIES=2
export API_DEFAULT_LIMIT=20
export API_TMDB_MOOD_MOVIES_LIMIT=15
```

---

## ML Configuration

### Mood Detection (RoBERTa)

```yaml
ml:
  mood_detection:
    model_version: "v2"               # MOOD_MODEL_VERSION
    model_name: "roberta-base"        # MOOD_MODEL_NAME
    max_length: 128                   # MOOD_MAX_LENGTH
    prediction_threshold: 0.35        # MOOD_PREDICTION_THRESHOLD
    labels: [anger, disgust, fear, happy, neutral, sad, surprise]
```

| Setting | Default | Tuning |
|---------|---------|--------|
| `model_version` | v2 | v1 (slower), v2 (fp16 optimized) |
| `max_length` | 128 | Increase for longer entries; impacts speed |
| `prediction_threshold` | 0.35 | Lower = more strict; higher = more permissive |

**Performance Impact**:
- v1 model: ~600ms per entry
- v2 model (fp16): ~400ms per entry

### Summarization (BART)

```yaml
ml:
  summarization:
    model_version: "v2"               # SUMMARIZATION_MODEL_VERSION
    model_name: "facebook/bart-large-cnn"
    max_input_length: 1024            # SUMMARIZATION_MAX_INPUT_LENGTH
    max_summary_length: 128           # SUMMARIZATION_MAX_SUMMARY_LENGTH
    min_summary_length: 20            # SUMMARIZATION_MIN_SUMMARY_LENGTH
    num_beams: 4                      # SUMMARIZATION_NUM_BEAMS
```

| Setting | Default | Tuning |
|---------|---------|--------|
| `max_input_length` | 1024 | Truncate longer entries |
| `max_summary_length` | 128 | Shorter = faster inference |
| `num_beams` | 4 | Higher = better quality, slower |

**Performance Impact**:
- num_beams=4: ~2s per entry
- num_beams=2: ~1s per entry (lower quality)

### Embeddings

```yaml
ml:
  embedding:
    model_name: "all-mpnet-base-v2"   # EMBEDDING_MODEL_NAME
    journal_blend_weight: 0.05        # JOURNAL_BLEND_WEIGHT
    taste_blend_weight: 0.95          # TASTE_BLEND_WEIGHT
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `model_name` | all-mpnet-base-v2 | Pre-trained model from sentence-transformers |
| `journal_blend_weight` | 0.05 | Weight for latest journal entry (intent) |
| `taste_blend_weight` | 0.95 | Weight for user taste profile (intent) |

**Intent Vector Formula**:
```
Intent = (latest_journal_embedding × 0.05) + (user_taste_vector × 0.95)
```

Adjust weights to favor recent mood (higher journal weight) or historical taste (higher taste weight).

### Insight Generation

```yaml
ml:
  insight_generation:
    use_gemini: false                 # INSIGHTS_USE_GEMINI
    backend: "huggingface"            # INSIGHTS_BACKEND: huggingface | ollama
    model_version: "v1"               # INSIGHTS_MODEL_VERSION
    hf_model_name: "Qwen/Qwen2-1.5B-Instruct"
    hf_model_dir: "ml/models/insight_generation/qwen2/v1"
    ollama_model: "qwen2:1.5b"        # INSIGHTS_OLLAMA_MODEL
    ollama_base_url: "http://localhost:11434"
    temperature: 0.7                  # INSIGHTS_TEMPERATURE
    batch_size: 5                     # INSIGHTS_BATCH_SIZE
    max_new_tokens: 4096              # INSIGHTS_MAX_NEW_TOKENS
    gemini_model_name: "gemini-2.0-flash"
    gemini_max_retries: 2             # INSIGHTS_GEMINI_MAX_RETRIES
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `use_gemini` | false | true = Gemini API, false = local Qwen2 |
| `backend` | huggingface | Qwen2 backend: huggingface or ollama |
| `temperature` | 0.7 | Higher = more creative, lower = more deterministic |
| `batch_size` | 5 | Entries per batch (for batch processing) |
| `max_new_tokens` | 4096 | Max length of generated insight |

**Configuration Scenarios**:

**Scenario 1: Local Inference (GPU-enabled)**
```yaml
use_gemini: false
backend: huggingface
temperature: 0.7
```

**Scenario 2: Cloud Inference (Gemini)**
```yaml
use_gemini: true
gemini_model_name: gemini-2.0-flash
gemini_max_retries: 2
```

**Scenario 3: Ollama (Offline)**
```yaml
backend: ollama
ollama_base_url: http://localhost:11434
ollama_model: qwen2:1.5b
```

### Model Store

```yaml
ml:
  model_store:
    source: "local"                   # MODEL_SOURCE: local | gcs | s3
    local_path: ""                    # MODEL_STORE_PATH
    cache_dir: "/tmp/models"          # MODEL_CACHE_DIR
    gcs_bucket: ""                    # MODEL_GCS_BUCKET
    s3_bucket: ""                     # MODEL_S3_BUCKET
    s3_region: "us-east-1"            # MODEL_S3_REGION
    download_on_startup: true         # MODEL_DOWNLOAD_ON_STARTUP
    models:
      roberta:
        version: "v2"                 # MODEL_ROBERTA_VERSION
      bart:
        version: "v2"                 # MODEL_BART_VERSION
      qwen2:
        version: "v1"                 # MODEL_QWEN2_VERSION
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `source` | local | Where to load models from |
| `local_path` | "" | Local directory (if source=local) |
| `download_on_startup` | true | Download missing models at startup |

**Examples**:

**Local (Development)**:
```bash
export MODEL_SOURCE=local
export MODEL_STORE_PATH=./ml/models
```

**GCS (Production)**:
```bash
export MODEL_SOURCE=gcs
export MODEL_GCS_BUCKET=my-bucket
```

**S3 (Production)**:
```bash
export MODEL_SOURCE=s3
export MODEL_S3_BUCKET=my-bucket
export MODEL_S3_REGION=us-west-2
```

---

## Recommendation Engine Configuration

```yaml
recommendation:
  fetch_limit: 200                    # RECOMMENDATION_FETCH_LIMIT
  refine_top: 100                     # RECOMMENDATION_REFINE_TOP
  top_k: 10                           # RECOMMENDATION_TOP_K

  ranking:
    similarity_weight: 0.9            # RANKING_SIMILARITY_WEIGHT
    popularity_weight: 0.1            # RANKING_POPULARITY_WEIGHT
    low_std_threshold: 0.03           # RANKING_LOW_STD_THRESHOLD

  intent:
    beta_min: 0.15                    # INTENT_BETA_MIN
    beta_boost: 0.35                  # INTENT_BETA_BOOST
    beta_max: 0.40                    # INTENT_BETA_MAX
    journal_embedding_fetch_limit: 1  # INTENT_JOURNAL_EMBEDDING_FETCH_LIMIT

  candidate:
    min_title_length: 3               # CANDIDATE_MIN_TITLE_LENGTH
    min_popularity: 1.0               # CANDIDATE_MIN_POPULARITY

  concurrency:
    intent_builder_max_workers: 3     # INTENT_BUILDER_MAX_WORKERS
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `fetch_limit` | 200 | Initial candidates to fetch from cache |
| `refine_top` | 100 | Candidates to refine before ranking |
| `top_k` | 10 | Final results returned |
| `similarity_weight` | 0.9 | Emphasizes semantic match |
| `popularity_weight` | 0.1 | Tie-breaker for similar items |

**Tuning Examples**:

**More Personalized** (favor similarity):
```yaml
similarity_weight: 0.95
popularity_weight: 0.05
fetch_limit: 500
```

**More Popular** (favor trending):
```yaml
similarity_weight: 0.7
popularity_weight: 0.3
fetch_limit: 100
```

---

## Media Cache Configuration

```yaml
cache:
  max_age_hours: 24                   # MEDIA_CACHE_MAX_AGE_HOURS
  fetch_limit: 500                    # MEDIA_CACHE_FETCH_LIMIT
  batch_size: 400                     # MEDIA_CACHE_BATCH_SIZE
  schema_version: "v1"                # MEDIA_CACHE_SCHEMA_VERSION
  
  supported_media_types:
    - movies
    - songs
    - books
    - podcasts
  
  language_buckets:
    songs:
      - language: hindi
        queries: ["hindi songs", "bollywood hits"]
        market: IN
      - language: english
        queries: ["english pop hits", "top english songs"]
        market: US
      - language: neutral
        queries: ["top hits", "popular songs"]
        market: null
```

| Setting | Default | Purpose |
|---------|---------|---------|
| `max_age_hours` | 24 | Cache TTL (Firestore TTL) |
| `fetch_limit` | 500 | Items to fetch per cache refresh |
| `batch_size` | 400 | Batch write size to Firestore |

**Language Buckets**: Define search queries per language for Spotify/podcasts.

---

## Background Jobs Configuration

```yaml
jobs:
  cache_refresh:
    # (Placeholder for future job scheduling)
```

**Planned Jobs**:
- `cache_refresh`: Update media cache every 6 hours
- `taste_vector_update`: Update user taste vectors daily
- `cleanup_expired_cache`: Delete expired media documents

---

## Complete Example Configurations

### Development Configuration

```bash
# .env.development

# Server
export FLASK_DEBUG=true
export FLASK_PORT=5000

# Logging
export APP_LOG_LEVEL=DEBUG
export WERKZEUG_LOG_LEVEL=INFO
export FIREBASE_LOG_LEVEL=DEBUG

# Models
export MODEL_SOURCE=local
export MODEL_STORE_PATH=./ml/models

# ML Settings
export MOOD_PREDICTION_THRESHOLD=0.35
export INSIGHTS_USE_GEMINI=false
export INSIGHTS_BACKEND=huggingface

# Recommendations
export RECOMMENDATION_FETCH_LIMIT=200
export RECOMMENDATION_TOP_K=10

# Cache
export MEDIA_CACHE_MAX_AGE_HOURS=24

# API
export API_REQUEST_TIMEOUT=10
export API_REQUEST_MAX_RETRIES=1
```

### Production Configuration

```bash
# .env.production

# Server
export FLASK_DEBUG=false
export FLASK_PORT=8080

# Logging
export APP_LOG_LEVEL=INFO
export WERKZEUG_LOG_LEVEL=ERROR
export FIREBASE_LOG_LEVEL=WARNING

# Models
export MODEL_SOURCE=gcs
export MODEL_GCS_BUCKET=my-prod-bucket

# ML Settings
export MOOD_PREDICTION_THRESHOLD=0.35
export INSIGHTS_USE_GEMINI=true
export INSIGHTS_GEMINI_MODEL_NAME=gemini-2.0-flash

# Recommendations
export RECOMMENDATION_FETCH_LIMIT=300
export RECOMMENDATION_TOP_K=15

# Cache
export MEDIA_CACHE_MAX_AGE_HOURS=48

# API
export API_REQUEST_TIMEOUT=30
export API_REQUEST_MAX_RETRIES=2

# Timezone
export APP_TIMEZONE=UTC
```

---

## Configuration Validation

At startup, the system validates:

1. **File existence**: `config.yml` must exist
2. **YAML syntax**: Valid YAML format
3. **Required fields**: All mandatory settings present
4. **Type consistency**: Env var overrides match expected types
5. **Firebase credentials**: Path valid and readable

**Validation Errors**:
```
FileNotFoundError: Config file not found at /app/config.yml
ValueError: Invalid config.yml: expected top-level mapping
RuntimeError: FIREBASE_CREDENTIALS_PATH not set
TypeError: API_REQUEST_TIMEOUT must be int, got str
```

---

## Configuration Best Practices

1. **Use environment variables in production** (never hardcode secrets)
2. **Test configuration changes** in staging before production
3. **Document custom overrides** in deployment runbooks
4. **Monitor performance** after configuration changes
5. **Keep defaults conservative** (prefer slower/safer over fast/risky)
6. **Version configuration** alongside code changes
7. **Use configuration management tools** (Terraform, Ansible) for infrastructure


