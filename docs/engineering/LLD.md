# LOW-LEVEL DESIGN (LLD)
## Pocket Journal — AI-Powered Digital Journaling Platform

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## TABLE OF CONTENTS
1. [Class Diagrams](#class-diagrams)
2. [Function Specifications](#function-specifications)
3. [Internal Logic & Algorithms](#internal-logic--algorithms)
4. [Sequence Flows](#sequence-flows)
5. [Error Handling](#error-handling)

---

## CLASS DIAGRAMS

### Module 1: Authentication & User Management

```python
class FirebaseAuthManager:
    """
    Manages Firebase authentication operations
    """
    __init__(firebase_json_path: str)
    
    Methods:
    ├─ verify_token(token: str) -> dict
    │  ├─ Input: JWT token string
    │  ├─ Process: Call firebase_admin.auth.verify_id_token()
    │  ├─ Returns: {uid: str, email: str, claims: dict}
    │  └─ Raises: FirebaseException if invalid
    │
    ├─ create_user(email: str, password: str) -> str
    │  ├─ Input: email, password
    │  ├─ Process: firebase_admin.auth.create_user()
    │  ├─ Returns: uid
    │  └─ Raises: AlreadyExistsException
    │
    └─ get_user(uid: str) -> dict
       ├─ Input: uid
       ├─ Returns: {uid, email, displayName, createdAt}
       └─ Raises: NotFoundException

class UserDocument:
    """
    Firestore user document model
    """
    __init__(uid: str, email: str, displayName: str)
    
    Fields:
    ├─ uid: str (Primary Key)
    ├─ email: str
    ├─ displayName: str
    ├─ createdAt: datetime
    ├─ preferences: dict
    │  ├─ theme: str (light/dark)
    │  ├─ notifications: bool
    │  └─ language: str
    │
    Methods:
    ├─ to_dict() -> dict
    ├─ from_dict(data: dict) -> UserDocument
    └─ validate() -> bool
```

### Module 2: Journal Entries

```python
class JournalEntry:
    """
    In-memory representation of a journal entry
    """
    __init__(uid: str, title: str, content: str, tags: list = [])
    
    Fields:
    ├─ entry_id: str
    ├─ uid: str
    ├─ title: str
    ├─ content: str
    ├─ tags: list[str]
    ├─ created_at: datetime
    ├─ updated_at: datetime
    │
    Methods:
    ├─ to_dict() -> dict
    ├─ from_dict(data: dict) -> JournalEntry
    ├─ is_valid() -> tuple[bool, str]
    │  ├─ Check: 1 <= len(content) <= 5000
    │  ├─ Check: 1 <= len(title) <= 500
    │  └─ Returns: (valid, error_message)
    │
    └─ get_summary_preview(max_length=100) -> str

class EntryManager:
    """
    Service for journal entry CRUD operations
    """
    __init__(db_manager: DBManager)
    
    Methods:
    ├─ create_entry(uid: str, title: str, content: str, tags: list) -> dict
    │  ├─ Validate input
    │  ├─ Generate entry_id (UUID)
    │  ├─ Store in journal_entries collection
    │  ├─ Returns: {entry_id, created_at, updated_at}
    │  └─ Raises: ValidationException, DatabaseException
    │
    ├─ get_entry(uid: str, entry_id: str) -> dict
    │  ├─ Query: journal_entries WHERE uid=uid AND id=entry_id
    │  ├─ Returns: Full entry object
    │  └─ Raises: NotFoundException, PermissionException
    │
    ├─ list_entries(uid: str, limit: int, offset: int, sort_order: str) -> list
    │  ├─ Query: journal_entries WHERE uid=uid ORDER BY created_at DESC
    │  ├─ Apply: Pagination (limit, offset)
    │  ├─ Returns: list[entry_dict], total_count
    │  └─ Performance: Index on (uid, created_at)
    │
    ├─ update_entry(uid: str, entry_id: str, updates: dict) -> dict
    │  ├─ Check: Ownership verification
    │  ├─ Merge: with existing entry
    │  ├─ Update: updated_at timestamp
    │  └─ Returns: Updated entry
    │
    ├─ delete_entry(uid: str, entry_id: str) -> bool
    │  ├─ Check: Ownership verification
    │  ├─ Delete: From journal_entries
    │  ├─ Cascade: Delete from entry_analysis
    │  ├─ Cascade: Delete from insight_entry_mapping
    │  └─ Returns: Success status
    │
    └─ search_entries(uid: str, query: str, limit: int) -> list
       ├─ Query: journal_entries WHERE uid=uid AND content CONTAINS query
       ├─ Rank: By relevance score
       └─ Returns: list[matched_entries]

class EntryAnalysis:
    """
    Analysis metadata for an entry (mood, summary, etc.)
    """
    __init__(entry_id: str, summary: str, mood: dict)
    
    Fields:
    ├─ entry_id: str (FK to journal_entries)
    ├─ summary: str
    ├─ mood: dict {mood_label: confidence}
    ├─ primary_mood: str
    ├─ confidence: float
    ├─ created_at: datetime
    │
    Methods:
    ├─ to_dict() -> dict
    ├─ from_dict(data: dict) -> EntryAnalysis
    └─ get_emotion_label() -> str
       └─ Returns highest-scoring mood label
```

### Module 3: Mood Detection

```python
class SentencePredictor:
    """
    RoBERTa predictor for emotion classification
    Location: ml/inference/mood_detection/roberta/predictor.py
    """
    __init__(model_path: str)
    
    Fields:
    ├─ model: transformers.RobertaForSequenceClassification
    ├─ tokenizer: transformers.RobertaTokenizer
    ├─ device: str ('cuda' | 'cpu')
    ├─ labels: list[str] = [anger, disgust, fear, happy, neutral, sad, surprise]
    │
    Methods:
    ├─ predict(text: str) -> dict
    │  ├─ Input: text (max 5000 chars)
    │  ├─ Tokenize: text → token_ids (max_length=128)
    │  ├─ Inference: Forward pass through RoBERTa
    │  ├─ Softmax: Convert logits to probabilities
    │  ├─ Returns: {
    │  │    "anger": 0.05, "disgust": 0.02, "fear": 0.03,
    │  │    "happy": 0.75, "neutral": 0.08, "sad": 0.05, "surprise": 0.02,
    │  │    "primary": "happy", "confidence": 0.75
    │  │  }
    │  └─ Time: < 500ms
    │
    ├─ predict_batch(texts: list[str], batch_size: int = 32) -> list
    │  ├─ Process multiple texts efficiently
    │  └─ Returns: list[prediction_dict]
    │
    ├─ _tokenize(text: str) -> dict
    │  ├─ Truncate/pad to max_length=128
    │  ├─ Returns: {input_ids, attention_mask}
    │  └─ Handles special tokens [CLS], [SEP]
    │
    └─ _tensor_to_device(tensor) -> tensor
       └─ Move to appropriate device (GPU/CPU)

class MoodAnalyzer:
    """
    High-level mood analysis orchestrator
    """
    __init__(predictor: SentencePredictor)
    
    Methods:
    ├─ analyze(text: str) -> dict
    │  ├─ Input: Journal entry text
    │  ├─ Call: predictor.predict(text)
    │  ├─ Returns: Full analysis with confidences
    │  └─ Caching: Per-entry (avoid re-prediction)
    │
    └─ batch_analyze(texts: list[str]) -> list
       └─ Efficient batch processing
```

### Module 4: Insights Generation

```python
class InsightGenerator:
    """
    Generates personalized insights from journal entries
    Location: services/insights_service/
    """
    __init__(db_manager: DBManager, config: dict)
    
    Fields:
    ├─ db: DBManager
    ├─ use_gemini: bool
    ├─ gemini_client: google.generativeai.GenerativeModel (if use_gemini)
    ├─ qwen2_predictor: InsightsPredictor (if not use_gemini)
    │
    Methods:
    ├─ generate(uid: str, start_date: str, end_date: str) -> dict
    │  ├─ Input: uid, date range (format: YYYY-MM-DD)
    │  │
    │  ├─ Step 1: Retrieve Entries
    │  │  └─ Query: journal_entries WHERE uid=uid AND date IN [start_date, end_date]
    │  │
    │  ├─ Step 2: Retrieve Analysis
    │  │  └─ Join with entry_analysis, get moods + summaries
    │  │
    │  ├─ Step 3: Aggregate Data
    │  │  ├─ Mood distribution
    │  │  ├─ Common themes
    │  │  └─ Emotional patterns
    │  │
    │  ├─ Step 4: Build Prompt
    │  │  └─ Structured prompt with entry data
    │  │
    │  ├─ Step 5: Call LLM
    │  │  ├─ IF use_gemini: Call Google Gemini API
    │  │  │  └─ max_output_tokens=4096, temperature=0.7
    │  │  └─ ELSE: Call Qwen2 locally
    │  │      └─ Load model, batch_size=5
    │  │
    │  ├─ Step 6: Parse Response
    │  │  ├─ Extract JSON structure
    │  │  ├─ Validate required fields
    │  │  └─ Fallback to raw response if parsing fails
    │  │
    │  ├─ Step 7: Store Results
    │  │  ├─ Create insights document
    │  │  ├─ Create entry mappings
    │  │  └─ Index by uid, date
    │  │
    │  └─ Returns: {insightId, goals, progress, remedies, ...}
    │
    ├─ _build_prompt(entries: list, moods: dict, themes: list) -> str
    │  └─ Structures prompt for LLM
    │
    ├─ _parse_insights_response(response: str) -> dict
    │  ├─ Try: JSON parsing
    │  └─ Fallback: Regex extraction
    │
    ├─ _call_gemini(prompt: str) -> str
    │  ├─ Initialize: generativeai client
    │  ├─ Call: generate_content (with retries)
    │  ├─ Timeout: 30 seconds
    │  ├─ Retries: 2 max with exponential backoff
    │  └─ Returns: Raw text response
    │
    └─ _call_qwen2(prompt: str) -> str
       ├─ Load: InsightsPredictor (cached)
       ├─ Tokenize: prompt
       └─ Generate: with sampling (temperature=0.7)

class InsightsPredictor:
    """
    Local Qwen2 inference for insights
    Location: ml/inference/insight_generation/qwen2/predictor.py
    """
    __init__(model_path: str)
    
    Fields:
    ├─ model: transformers.AutoModelForCausalLM
    ├─ tokenizer: transformers.AutoTokenizer
    ├─ device: str
    │
    Methods:
    └─ generate(prompt: str, max_new_tokens: int = 4096) -> str
       ├─ Tokenize prompt
       ├─ Generate with temperature=0.7
       └─ Detokenize output
```

### Module 5: Media Recommendations

```python
class RecommendationEngine:
    """
    Main recommendation engine orchestrator
    Location: services/media_recommender/recommendation_engine.py
    """
    __init__(db_manager: DBManager, config: dict, embedding_service: EmbeddingService)
    
    Fields:
    ├─ db: DBManager
    ├─ config: dict (ranking, candidate, intent settings)
    ├─ embedding_service: EmbeddingService
    ├─ cache_store: MediaCacheStore
    │
    Methods:
    ├─ recommend(uid: str, mood: str, media_type: str, top_k: int = 10) -> list
    │  ├─ Step 1: Cold-start check
    │  │  └─ If new user: Return popular items
    │  │
    │  ├─ Step 2: Get Mood Embedding
    │  │  └─ embedding = embedding_service.get_mood_embedding(mood)
    │  │
    │  ├─ Step 3: Fetch Candidates
    │  │  ├─ Query cache_store
    │  │  ├─ If cache hit: Use cached results
    │  │  └─ If cache miss: Fetch from provider (TMDb, Spotify, etc.)
    │  │
    │  ├─ Step 4: Filter Candidates
    │  │  ├─ Remove: duplicates
    │  │  ├─ Remove: already-interacted items
    │  │  └─ Apply: popularity threshold
    │  │
    │  ├─ Step 5: Ranking
    │  │  ├─[Phase 1-4] Basic ranking
    │  │  │  └─ score = (similarity × 0.9) + (popularity × 0.1)
    │  │  │
    │  │  └─[Phase 5] Advanced ranking (if config.use_phase5)
    │  │     ├─ Hybrid scoring
    │  │     ├─ MMR diversification
    │  │     └─ Temporal decay
    │  │
    │  ├─ Step 6: Select Top K
    │  │  └─ Sort by score, limit to top_k
    │  │
    │  └─ Returns: list[recommended_items]
    │
    ├─ _fetch_candidates(media_type: str, mood: str, limit: int) -> list
    │  ├─ Build provider query
    │  ├─ Call appropriate provider
    │  └─ Returns: candidate list
    │
    ├─ _rank_candidates(candidates: list, mood_embedding: list) -> list
    │  ├─ Calculate: Cosine similarity for each candidate
    │  ├─ Calculate: Popularity score
    │  ├─ Combine: Based on ranking config
    │  └─ Returns: Ranked candidates
    │
    ├─ _apply_mmr(candidates: list, embedding: list, lambda_param: float) -> list
    │  ├─ Maximal Marginal Relevance algorithm
    │  ├─ Progressively select diverse items
    │  └─ Returns: Diversified list
    │
    └─ _apply_temporal_decay(items: list) -> list
       ├─ Decay old interactions
       └─ Adjust scores based on recency

class MediaProvider:
    """
    Abstract base for media providers
    """
    abstract
    
    Methods:
    ├─ search(query: str, limit: int) -> list
    └─ get_details(media_id: str) -> dict

class TMDbProvider(MediaProvider):
    """
    The Movie Database provider
    Location: services/media_recommender/providers/tmdb_provider.py
    """
    __init__(api_key: str)
    
    Methods:
    ├─ get_trending() -> list[Movie]
    │  └─ Calls: /3/trending/movie/week
    │
    ├─ get_popular(page: int = 1) -> list[Movie]
    │  └─ Calls: /3/movie/popular
    │
    ├─ search_by_mood(mood: str, limit: int = 100) -> list[Movie]
    │  └─ Maps mood → genre keywords → search API
    │
    └─ get_details(movie_id: int) -> dict
       └─ Calls: /3/movie/{movie_id}

class SpotifyProvider(MediaProvider):
    """
    Spotify provider for songs and podcasts
    Location: services/media_recommender/providers/spotify_provider.py
    """
    __init__(client_id: str, client_secret: str)
    
    Methods:
    ├─ get_token() -> str
    │  └─ OAuth2 token refresh
    │
    ├─ search_songs(query: str, limit: int = 20) -> list[Song]
    │  └─ Calls: /v1/search?type=track
    │
    ├─ search_playlists(mood: str) -> list[Playlist]
    │  └─ Mood-mapped playlist search
    │
    └─ get_track_details(track_id: str) -> dict
       └─ Calls: /v1/tracks/{id}

class MediaCacheStore:
    """
    Firestore-backed media cache
    Location: services/media_recommender/cache_store.py
    """
    __init__(db: firestore.Client)
    
    Fields:
    ├─ db: firestore.Client
    ├─ ttl_hours: int = 24
    ├─ collections: dict = {
    │    'movies': 'media_cache_movies',
    │    'songs': 'media_cache_songs',
    │    'books': 'media_cache_books',
    │    'podcasts': 'media_cache_podcasts'
    │  }
    │
    Methods:
    ├─ get(media_type: str, query: str) -> list
    │  ├─ Query: media_cache_{type} WHERE query=query AND age < 24h
    │  └─ Returns: Cached items or empty list
    │
    ├─ set(media_type: str, query: str, items: list) -> bool
    │  ├─ Store: items in media_cache_{type}
    │  ├─ Metadata: {query, timestamp, ttl}
    │  └─ Returns: Success
    │
    ├─ is_expired(item: dict) -> bool
    │  └─ Check: (now - timestamp) > ttl_hours
    │
    └─ clear_expired() -> int
       └─ Delete expired items, return count
```

### Module 6: Analytics & Statistics

```python
class StatsCalculator:
    """
    Computes user analytics and statistics
    Location: services/stats_service/stats_calculator.py
    """
    __init__(db_manager: DBManager)
    
    Methods:
    ├─ get_overview(uid: str, period: str = 'month') -> dict
    │  ├─ Calls multiple methods below
    │  └─ Returns: {totalEntries, avgLength, moodDist, trends, ...}
    │
    ├─ calculate_total_entries(uid: str, start_date: str, end_date: str) -> int
    │  └─ COUNT from journal_entries
    │
    ├─ calculate_mood_distribution(uid: str, start_date: str, end_date: str) -> dict
    │  ├─ Query: entry_analysis WHERE uid=uid AND date IN range
    │  ├─ Count: per mood label
    │  └─ Returns: {anger: 5, happy: 10, ...}
    │
    ├─ calculate_entry_frequency(uid: str, start_date: str, end_date: str) -> dict
    │  ├─ Group: entries by date
    │  └─ Returns: {2025-01-01: 2, 2025-01-02: 1, ...}
    │
    ├─ calculate_writing_patterns(uid: str, days: int = 30) -> dict
    │  ├─ Analyze: by hour, day-of-week
    │  ├─ Calculate: peak hours, average time
    │  └─ Returns: {peakHours: [20, 21, 22], avgEntries: 0.8}
    │
    ├─ calculate_mood_trend(uid: str, days: int = 30) -> dict
    │  ├─ Aggregate: mood scores over time
    │  ├─ Linear regression: mood_score ~ days
    │  ├─ Returns: {trend: 'improving', slope: 0.05}
    │  └─ Algorithm: numpy.polyfit(days, scores, 1)
    │
    └─ calculate_streak(uid: str) -> int
       └─ Count consecutive days with entries
```

### Module 7: Export Service

```python
class ExportManager:
    """
    Exports user data in multiple formats
    Location: services/export_service/export_manager.py
    """
    __init__(db_manager: DBManager)
    
    Methods:
    ├─ export_csv(uid: str, start_date: str = None, end_date: str = None) -> bytes
    │  ├─ Query: journal_entries + entry_analysis
    │  ├─ Format: Pandas DataFrame
    │  │  └─ Columns: [date, title, content, mood, summary, tags]
    │  ├─ Serialize: to CSV (RFC 4180)
    │  └─ Returns: CSV bytes
    │
    ├─ export_json(uid: str, start_date: str = None, end_date: str = None) -> bytes
    │  ├─ Query: journal_entries
    │  ├─ Format: JSON structure
    │  │  └─ {entries: [...], metadata: {total, export_date}}
    │  └─ Return: JSON bytes
    │
    ├─ export_pdf(uid: str, start_date: str = None, end_date: str = None, include_analytics: bool = False) -> bytes
    │  ├─ Query: journal_entries
    │  ├─ Format: Reportlab PDF document
    │  ├─ Content:
    │  │  ├─ Header: User info, date range
    │  │  ├─ Entries: Formatted entries
    │  │  └─ Analytics: (if requested)
    │  └─ Returns: PDF bytes
    │
    ├─ _filter_by_date_range(entries: list, start_date: str, end_date: str) -> list
    │  └─ Filter entries within date range
    │
    └─ _serialize_entry(entry: dict) -> str
       └─ Format entry for export
```

### Module 8: Health & Jobs

```python
class HealthChecker:
    """
    System health check service
    Location: services/health_service.py
    """
    __init__(db_manager: DBManager)
    
    Methods:
    ├─ check_health() -> dict
    │  └─ Returns: {status, services, timestamp}
    │
    ├─ _check_database() -> dict
    │  ├─ Query: firestore (test query)
    │  └─ Returns: {status: 'ok'|'error', msg}
    │
    ├─ _check_models() -> dict
    │  ├─ Test: RoBERTa inference
    │  ├─ Test: BART availability
    │  └─ Returns: {roberta: 'ok', bart: 'ok', ...}
    │
    └─ _check_external_apis() -> dict
       ├─ Test: TMDb API
       ├─ Test: Spotify API
       └─ Returns: Results for each API

class JobManager:
    """
    Background job tracking
    Location: services/jobs_service.py
    """
    Methods:
    ├─ get_job_status(job_id: str) -> dict
    │  └─ Returns: {job_id, status, progress, result}
    │
    └─ update_job_status(job_id: str, status: str, progress: int) -> bool
       └─ Update job in persistence layer
```

### Support Module: Database Manager

```python
class DBManager:
    """
    Database abstraction layer for Firestore
    Location: persistence/db_manager.py
    """
    __init__(firebase_json_path: str = None)
    
    Fields:
    ├─ db: firestore.Client
    ├─ collections: dict = {config collections}
    │
    Methods:
    ├─ create(collection: str, doc_id: str, data: dict) -> bool
    │  ├─ Firestore: db.collection(collection).document(doc_id).set(data)
    │  ├─ Raises: DocumentAlreadyExistsException
    │  └─ Returns: Success
    │
    ├─ read(collection: str, doc_id: str) -> dict
    │  ├─ Firestore: db.collection(collection).document(doc_id).get()
    │  └─ Returns: document data or None
    │
    ├─ update(collection: str, doc_id: str, data: dict) -> bool
    │  ├─ Firestore: db.collection(collection).document(doc_id).update(data)
    │  └─ Returns: Success
    │
    ├─ delete(collection: str, doc_id: str) -> bool
    │  ├─ Firestore: db.collection(collection).document(doc_id).delete()
    │  └─ Returns: Success
    │
    ├─ query(collection: str, filters: list, limit: int = 100) -> list
    │  ├─ Build query with filters
    │  ├─ Example filter: {'field': 'uid', 'op': '==', 'value': uid}
    │  └─ Returns: list[documents]
    │
    ├─ batch_write(operations: list) -> bool
    │  ├─ Atomic write batch (max 500 operations)
    │  └─ Returns: Success
    │
    └─ transaction(callback) -> result
       ├─ Execute callback in transaction
       └─ Returns: callback result
```

### Support Module: Embeddings Service

```python
class EmbeddingService:
    """
    Text embeddings via Sentence Transformers
    Location: services/embeddings/embedding_service.py
    """
    __init__(model_name: str = 'all-mpnet-base-v2', device: str = 'auto')
    
    Fields:
    ├─ model: SentenceTransformer
    ├─ device: str ('cuda' | 'cpu' | 'auto')
    ├─ embedding_dim: int = 384
    │
    Methods:
    ├─ embed(text: str) -> list[float]
    │  ├─ Input: text string
    │  ├─ Process: model.encode(text)
    │  └─ Returns: 384-dim embedding
    │
    ├─ embed_batch(texts: list[str], batch_size: int = 32) -> list[list]
    │  ├─ Input: list of texts
    │  ├─ Process: Batch encoding
    │  └─ Returns: list of embeddings
    │
    ├─ similarity(embedding1: list, embedding2: list) -> float
    │  ├─ Cosine similarity between two embeddings
    │  └─ Returns: similarity score (0-1)
    │
    └─ get_mood_embedding(mood: str) -> list
       ├─ Get or generate embedding for mood
       └─ Return: 384-dim embedding
```

---

## FUNCTION SPECIFICATIONS

### Function: RoBERTa Mood Detection

```python
def predict_mood(text: str, predictor: SentencePredictor) -> dict:
    """
    Predict mood/emotion from text using RoBERTa
    
    Parameters:
        text (str): Journal entry text, max 5000 characters
        predictor (SentencePredictor): Loaded RoBERTa predictor
    
    Returns:
        dict: {
            "mood": {
                "anger": float,
                "disgust": float,
                "fear": float,
                "happy": float,
                "neutral": float,
                "sad": float,
                "surprise": float
            },
            "primary_mood": str,  # Label with highest score
            "confidence": float   # Score of primary mood
        }
    
    Raises:
        ValueError: If text is empty or too long
        RuntimeError: If model inference fails
    
    Algorithm:
        1. Validate input (1 <= len(text) <= 5000)
        2. Tokenize: text → token_ids (max_length=128, truncate)
        3. Forward pass through RoBERTa
        4. Softmax(logits) → probabilities
        5. Identify argmax → primary mood
        6. Return probabilities + primary + confidence
    
    Example:
        >>> result = predict_mood("Today was wonderful!", predictor)
        >>> result["primary_mood"]
        "happy"
        >>> result["confidence"]
        0.85
    """
    pass
```

### Function: BART Summarization

```python
def summarize_text(text: str, summarizer: SummarizationPredictor) -> str:
    """
    Generate abstractive summary using BART
    
    Parameters:
        text (str): Entry text to summarize (max 5000 chars)
        summarizer (SummarizationPredictor): Loaded BART model
    
    Returns:
        str: Summary text (20-128 tokens)
    
    Raises:
        ValueError: If text is empty
        RuntimeError: If inference fails
    
    Algorithm:
        1. Validate input length
        2. Tokenize: text → token_ids (max_length=1024)
        3. Generate summary using beam search
           - num_beams=4
           - max_length=128
           - min_length=20
           - early_stopping=True
        4. Decode token_ids → summary text
        5. Return summary
    
    Example:
        >>> summary = summarize_text(long_entry_text, summarizer)
        >>> len(summary)
        145  # tokens
    """
    pass
```

### Function: Generate Insights

```python
def generate_insights(uid: str, start_date: str, end_date: str, 
                      generator: InsightGenerator) -> dict:
    """
    Generate personalized insights from entries
    
    Parameters:
        uid (str): Firebase user UID
        start_date (str): Start date (YYYY-MM-DD)
        end_date (str): End date (YYYY-MM-DD)
        generator (InsightGenerator): Initialized generator
    
    Returns:
        dict: {
            "insight_id": str,
            "goals": [{"title": str, "description": str}],
            "progress": str,
            "negative_behaviors": str,
            "remedies": str,
            "appreciation": str,
            "conflicts": str,
            "created_at": datetime
        }
    
    Raises:
        PermissionError: If uid not authenticated
        ValueError: If date range invalid
        TimeoutError: If LLM call exceeds 30s
    
    Algorithm:
        1. Validate uid and date range (min 1 day)
        2. Query journal_entries for uid and date range
        3. Join with entry_analysis for moods/summaries
        4. Aggregate data:
           - mood distribution
           - common themes
           - patterns
        5. Build structured prompt
        6. Call LLM (Gemini or Qwen2)
        7. Parse JSON response
        8. Validate response structure
        9. Store in insights collection
        10. Create mappings in insight_entry_mapping
        11. Return insight object
    """
    pass
```

### Function: Get Media Recommendations

```python
def get_recommendations(uid: str, mood: str, media_type: str, 
                       top_k: int = 10, engine: RecommendationEngine) -> list:
    """
    Get personalized media recommendations
    
    Parameters:
        uid (str): User ID
        mood (str): Mood label (happy, sad, etc.) or None
        media_type (str): 'movie' | 'song' | 'book' | 'podcast'
        top_k (int): Number of recommendations (max 50)
        engine (RecommendationEngine): Recommendation engine instance
    
    Returns:
        list[dict]: [
            {
                "id": str,
                "title": str,
                "description": str,
                "popularity": float,
                "score": float,
                "metadata": {...}
            },
            ...
        ]
    
    Raises:
        PermissionError: If uid not authenticated
        ValueError: If mode_type invalid
    
    Algorithm:
        1. Check cold-start (user has < 3 entries)
           → Return popular items
        2. Get mood embedding
        3. Check cache for candidates
           - If HIT (< 24h old): Use cached
           - If MISS: Fetch from provider
        4. Filter candidates:
           - Remove duplicates
           - Remove already-seen
           - Apply popularity threshold (min 1.0)
        5. Rank candidates:
           - Compute similarity score
           - Compute popularity score
           - Phase 5: Apply MMR, temporal decay, hybrid scoring
        6. Select top K
        7. Log interaction (optional)
        8. Return recommendations
    """
    pass
```

---

## INTERNAL LOGIC & ALGORITHMS

### Algorithm 1: Mood Detection (RoBERTa)

```
INPUT: text string (max 5000 chars)
OUTPUT: emotion probabilities (7 classes)

PROCESS:
  1. Tokenization
     - Load tokenizer for RoBERTa
     - Encode text with:
       * max_length = 128
       * truncation = True (truncate if > 128)
       * padding = 'max_length'
       * return_tensors = 'pt'
     - Output: token_ids [batch_size, seq_length]
  
  2. Model Inference
     - Load RoBERTa-base pre-trained + fine-tuned model
     - Forward pass: token_ids → logits
       * logits.shape = [batch_size, num_classes=7]
  
  3. Softmax Normalization
     - Apply softmax to logits
     - probs = exp(logits) / sum(exp(logits))
     - probs ∈ [0, 1], sum(probs) = 1
  
  4. Label Mapping
     - anger (idx 0) → probs[0]
     - disgust (idx 1) → probs[1]
     - fear (idx 2) → probs[2]
     - happy (idx 3) → probs[3]
     - neutral (idx 4) → probs[4]
     - sad (idx 5) → probs[5]
     - surprise (idx 6) → probs[6]
  
  5. Apply Confidence Threshold
     - primary_idx = argmax(probs)
     - primary_mood = labels[primary_idx]
     - confidence = probs[primary_idx]
     - IF confidence < 0.35:
         primary_mood = 'neutral'

OUTPUT: {
  "mood": {...},
  "primary_mood": "happy",
  "confidence": 0.85
}
```

### Algorithm 2: Similarity-Based Ranking

```
INPUT: candidates (list of media items)
       mood_embedding (384-dim vector)
       config (ranking params)

OUTPUT: ranked candidates (sorted by score)

PROCESS:
  1. For each candidate:
     a) Get candidate embedding (from provider metadata or cache)
     b) Compute cosine similarity
        similarity = dot(mood_emb, candidate_emb) / (norm(mood_emb) * norm(candidate_emb))
     
     c) Get popularity score (normalized 0-100)
        pop_score = (popularity - min_pop) / (max_pop - min_pop)
     
     d) Combine scores
        score = (similarity * 0.9) + (pop_score * 0.1)
  
  2. Sort by score descending
  
  3. Return top K items

Example:
  mood_embedding = [0.1, 0.2, ..., 0.05]  # 384-dim
  candidate_embedding = [0.12, 0.21, ..., 0.04]
  
  similarity = 0.92
  popularity = 75 (normalized)
  score = (0.92 * 0.9) + (0.75 * 0.1) = 0.828 + 0.075 = 0.903
```

### Algorithm 3: MMR (Maximal Marginal Relevance)

```
INPUT: candidates (ranked by relevance)
       query_embedding
       lambda_param (0-1, higher = more relevant, less diverse)
       top_k

OUTPUT: diverse subset of top_k items

PROCESS:
  selected = []
  remaining = candidates
  
  WHILE len(selected) < top_k AND remaining not empty:
    1. IF selected is empty:
       - Add most relevant item (highest score)
       - selected = [candidates[0]]
    
    ELSE:
       - For each item i in remaining:
           relevance_i = similarity(query, item_i)
           diversity_i = min(similarity(item_i, item_j) for item_j in selected)
           mmr_score_i = lambda * relevance_i - (1 - lambda) * diversity_i
       
       - Select item with max MMR score
       - selected.append(best_item)
    
    2. Remove selected item from remaining
  
  RETURN selected

Example (lambda=0.7):
  Item A: relevance=0.95, diversity=0.2
    → MMR = 0.7*0.95 - 0.3*0.2 = 0.605
  Item B: relevance=0.90, diversity=0.8
    → MMR = 0.7*0.90 - 0.3*0.8 = 0.39
  
  Select Item A (higher MMR, more relevant while still diverse)
```

---

## SEQUENCE FLOWS

### Sequence Flow 1: Create Entry & Analyze

```
User                WebApp                 API                Services              Models              DB
│                   │                      │                  │                    │                   │
├─ write entry ────►│                      │                  │                    │                   │
│                   ├─ POST /api/entries ──►│                  │                    │                   │
│                   │                      │                  │                    │                   │
│                   │                      ├─ verify token ───────────────────────────────────────────►│
│                   │                      │◄─────── valid ─────────────────────────────────────────── │
│                   │                      │                  │                    │                   │
│                   │                      ├─ EntryManager.create_entry() ►│        │                   │
│                   │                      │                  │                    │                   │
│                   │                      │                  ├─ store entry ──────────────────────────►│
│                   │                      │                  │                    │                   │
│                   │                      │                  ├─ [Parallel Processing] ┐               │
│                   │                      │                  │                    │   │               │
│                   │                      │                  ├─ Mood Detection ──────────┐ predict  │
│                   │                      │                  │                    │   │   └──►│       │
│                   │                      │                  │                    │◄──────────◄│       │
│                   │                      │                  │                    │   │       │       │
│                   │                      │                  ├─ Summarization ───────┤ infer │       │
│                   │                      │                  │                    │   │   ┌──►│       │
│                   │                      │                  │                    │◄──────┤──◄│       │
│                   │                      │                  │                    │   │   │   │       │
│                   │                      │                  ├─ Embeddings ──────────┤────┤───►│       │
│                   │                      │                  │                    │   │   └──►│       │
│                   │                      │                  │                    │◄────────◄│       │
│                   │                      │                  ├─ [End Parallel] ◄─────┘               │
│                   │                      │                  │                    │                   │
│                   │                      │                  ├─ store analysis ──────────────────────►│
│                   │                      │                  │                    │                   │
│                   │                      │◄─ return result ──│                    │                   │
│                   │◄─ JSON response ────│                  │                    │                   │
│◄─ update UI ──────│                      │                  │                    │                   │
```

### Sequence Flow 2: Get Recommendations

```
User            WebApp             API             RecommEngine           Cache              Providers
│               │                  │               │                      │                  │
├─ request ────►│                  │               │                      │                  │
│               ├─ GET /api/media ─►│               │                      │                  │
│               │                  │               │                      │                  │
│               │                  ├─ verify token ────────────────────────────────────────│
│               │                  │◄─ valid ────────────────────────────────────────────│
│               │                  │               │                      │                  │
│               │                  ├─ recommend() ────────────────────────►│                │
│               │                  │               │                      │                │
│               │                  │               ├─ check cache ────────►│                │
│               │                  │               │                      │                │
│               │                  │               │◄─ cache HIT/MISS ────│                │
│               │                  │               │                      │                │
│               │                  │               ├─[CACHE MISS? ELSE SKIP]              │
│               │                  │               │                      │                │
│               │                  │               ├─ fetch candidates ────────────────────►│
│               │                  │               │                      │                │
│               │                  │               │                      │◄─ movies/songs─│
│               │                  │               │                      │                │
│               │                  │               ├─ cache results ──────►│                │
│               │                  │               │                      │                │
│               │                  │               ├─ rank candidates     │                │
│               │                  │               │                      │                │
│               │                  │               ├─ MMR/temporal decay  │                │
│               │                  │               │                      │                │
│               │                  │               ├─ select top K        │                │
│               │                  │               │                      │                │
│               │                  │◄─ recommendations                     │                │
│               │◄─ JSON array ────│               │                      │                │
│◄─ display ────│                  │               │                      │                │
```

---

## ERROR HANDLING

### Error Handling Strategy

```python
class PocketJournalException(Exception):
    """Base exception for Pocket Journal"""
    def __init__(self, message: str, code: str, status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(PocketJournalException):
    """Input validation errors"""
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)

class PermissionException(PocketJournalException):
    """Authorization errors"""
    def __init__(self, message: str):
        super().__init__(message, code="PERMISSION_DENIED", status_code=403)

class NotFoundException(PocketJournalException):
    """Resource not found"""
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found", code="NOT_FOUND", status_code=404)

class DatabaseException(PocketJournalException):
    """Database operation errors"""
    def __init__(self, message: str):
        super().__init__(message, code="DATABASE_ERROR", status_code=500)

class TimeoutException(PocketJournalException):
    """Operation timeout"""
    def __init__(self, operation: str, timeout_seconds: int):
        msg = f"{operation} timed out after {timeout_seconds}s"
        super().__init__(msg, code="TIMEOUT", status_code=504)

# Usage in routes:
@app.route('/api/entries', methods=['POST'])
@login_required
def create_entry():
    try:
        data = request.json
        
        # Validate
        if not data.get('content'):
            raise ValidationException("Content is required")
        
        if len(data['content']) > 5000:
            raise ValidationException("Content exceeds 5000 characters")
        
        # Process
        entry = EntryManager(db).create_entry(
            uid=request.user['uid'],
            title=data.get('title'),
            content=data['content'],
            tags=data.get('tags', [])
        )
        
        return jsonify(entry), 201
    
    except ValidationException as e:
        return jsonify({"error": e.code, "message": e.message}), e.status_code
    
    except PermissionException as e:
        return jsonify({"error": e.code, "message": e.message}), e.status_code
    
    except Exception as e:
        logger.exception("Unexpected error creating entry")
        return jsonify({"error": "INTERNAL_ERROR", "message": str(e)}), 500
```

---

**END OF LOW-LEVEL DESIGN DOCUMENT**

