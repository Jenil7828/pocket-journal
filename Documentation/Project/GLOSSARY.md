# Glossary: Pocket Journal Backend

## Machine Learning & NLP

**Embedding** (Vector, Latent Representation)
- Dense numerical representation of text meaning
- **Example**: "I'm happy" → [0.12, -0.34, 0.56, ... (768 dimensions)]
- **Use**: Intent building, similarity ranking, media matching
- **Model**: sentence-transformers `all-mpnet-base-v2`
- **Dimensions**: 768 (per token)
- **Normalization**: L2 (enables cosine similarity)

**Mood Detection** (Emotion Classification)
- ML task: Classify entry into 7 emotions
- **Classes**: anger, disgust, fear, happy, neutral, sad, surprise
- **Model**: RoBERTa-base (fine-tuned on SemEval-2018 dataset)
- **Confidence**: Probability distribution across 7 classes
- **Threshold**: Predictions below 0.35 → "neutral"
- **Version**: v2 (fp16 optimized + ONNX runtime)

**Summarization** (Abstractive Text Generation)
- ML task: Generate concise summary from longer text
- **Model**: BART-large-cnn (facebook/bart-large-cnn)
- **Output**: 20-128 tokens (configurable)
- **Algorithm**: Seq2Seq with beam search (num_beams=4)
- **Metric**: ROUGE score (measures overlap with reference summaries)
- **Version**: v2 (fp16 optimized)

**Intent Vector** (Recommendation Context)
- Blended embedding capturing user's current state + preferences
- **Formula**: `intent = (journal_embedding × 0.05) + (taste_vector × 0.95)`
- **Purpose**: Used to rank media recommendations
- **Dimensionality**: 768-dim (matches embedding model)
- **Update**: Built on-demand per recommendation request

**Cosine Similarity** (Vector Distance Metric)
- Measure of angle between two vectors (0 to 1)
- **Formula**: `cos(θ) = (A · B) / (||A|| × ||B||)`
- **Interpretation**: 1.0 = identical, 0.0 = orthogonal, -1.0 = opposite
- **Use**: Rank media by semantic relevance to intent vector
- **Performance**: O(n) for n items

**Taste Vector** (User Profile Embedding)
- Aggregate embedding representing user's long-term preferences
- **Computation**: Mean of user's last 50 entry embeddings
- **Normalization**: L2 normalized
- **Update Frequency**: Daily batch job (or on-demand)
- **Purpose**: Personalization (weighted 95% in intent blending)

**ONNX** (Open Neural Network Exchange)
- Model format for efficient inference
- **Benefits**: 2-3x speedup vs PyTorch, CPU/GPU portable
- **Conversion**: PyTorch model → ONNX → Optimized runtime
- **Quantization**: fp16 (half-precision, 50% memory)
- **Used for**: RoBERTa, BART models

**Beam Search** (Decoding Strategy)
- Algorithm for seq2seq generation (summarization, insights)
- **num_beams**: Number of partial hypotheses to track
- **Trade-off**: Higher beams → better quality, slower inference
- **Current**: num_beams=4 for summarization

**Transformer** (Neural Network Architecture)
- State-of-the-art for NLP tasks
- **Key Mechanism**: Self-attention (compare all token pairs)
- **Models Used**:
  - RoBERTa: Classification (mood detection)
  - BART: Seq2Seq (summarization)
  - Qwen2: Generative (insight generation)

---

## Recommendation & Ranking

**Media Recommendation** (Personalized Content Suggestion)
- Task: Suggest movies, songs, books based on user state
- **Pipeline**:
  1. Build intent vector (mood + taste)
  2. Query media cache
  3. Rank by similarity + popularity
  4. Fallback to live providers if needed
- **Providers**: TMDb, Spotify, Google Books

**Cache-First Strategy** (Hybrid Lookup)
- Preference for serving cached data over live API calls
- **Benefits**: Speed (3x faster), cost (80% fewer API calls), reliability
- **Fallback**: If cache miss or insufficient results, call live provider
- **Deduplication**: Merge cache + live results, remove duplicates

**Cold Start Problem** (New User Challenge)
- Recommendation difficulty when user has no history
- **Solutions in Pocket Journal**:
  - Day 1: Serve popular/trending items
  - Day 2-7: Mix popular + mood-based
  - Week 2+: Full personalization (taste vector ready)

**Ranking Score** (Media Relevance Metric)
- Composite score combining similarity + popularity
- **Formula**: `score = (similarity × 0.9) + (popularity × 0.1)`
- **Similarity**: Cosine similarity of intent → media embeddings
- **Popularity**: Normalized provider popularity score
- **Range**: 0.0-1.0

**Fuzzy Matching** (Approximate String Matching)
- Algorithm for search tolerance
- **Example**: "Ceptions" matches "Inception" with 87% similarity
- **Threshold**: 70% (configured)
- **Library**: RapidFuzz (efficient C++ implementation)
- **Use**: Search deduplication, typo tolerance

---

## Caching & Performance

**Media Cache** (Firestore Document Collection)
- Stores frequently-accessed media from providers
- **Lifecycle**: Created on first request, expires after 24 hours
- **Contents**: 50-500 items (movies, songs, books, podcasts)
- **TTL**: 24 hours (configurable via `MEDIA_CACHE_MAX_AGE_HOURS`)
- **Indexing**: (media_type, language, expires_at)

**Cache Hit Rate** (Success Metric)
- Percentage of requests served from cache
- **Current**: 75% across all media types
- **Breakdown**:
  - Movies: 85%
  - Songs: 72%
  - Books: 68%
  - Podcasts: 65%
- **Impact**: 3x latency reduction on average

**Cache Invalidation** (Refresh Strategy)
- **TTL-based**: Firestore auto-deletes expired docs
- **Manual**: Background job queries expired docs
- **On-demand**: User can manually refresh if needed
- **Soft delete**: Uses `expires_at` field (no hard delete)

**Stale-While-Revalidate** (Cache Fallback)
- Serve cached data while refresh happens in background
- **Benefit**: Users see results immediately
- **Timing**: Asynchronous refresh (doesn't block response)
- **TTL**: Serve stale data for X seconds after expiry (grace period)

**Connection Pooling** (Network Optimization)
- Reuse HTTP connections to external APIs
- **Benefit**: 50-100ms latency reduction per request
- **Library**: requests (automatic)
- **Pool size**: Default 10 connections per provider

---

## API & Response

**REST API** (Architectural Style)
- HTTP-based interface for client communication
- **Methods**: GET, POST, PUT, DELETE
- **Status Codes**: 2xx (success), 4xx (client error), 5xx (server error)
- **Authentication**: JWT bearer token

**JWT** (JSON Web Token)
- Cryptographically signed token for authentication
- **Format**: Header.Payload.Signature (base64-encoded)
- **Validation**: Backend verifies signature
- **Lifetime**: 1 hour (Firebase default)
- **Refresh**: Client calls Firebase SDK automatically

**Pagination** (Result Limiting)
- Divide large result sets into pages
- **Parameters**: `limit` (per page), `offset` (starting position)
- **Max limit**: 100 (prevents excessive data transfer)
- **Response**: Includes `total_count` for navigation

**Rate Limiting** (Quota Management)
- Restrict requests to prevent abuse/overload
- **Scope**: Per-user, per-endpoint, or per-provider
- **Strategy**: Token bucket (refill X tokens per minute)
- **Response**: 429 (Too Many Requests) with retry hint

**Error Response** (Failure Communication)
```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "timestamp": "ISO 8601 format",
  "details": "Optional context"
}
```

---

## Database & Persistence

**Firestore** (NoSQL Database)
- Google Cloud-managed, real-time database
- **Data Model**: Collections → Documents → Fields
- **Queries**: Document-level, no traditional SQL joins
- **Transactions**: ACID compliant
- **Scaling**: Automatic (manages complexity)

**Document** (Firestore Record)
- Individual record in a collection
- **Structure**: Key-value pairs (flexible schema)
- **ID**: Auto-generated or custom (user-provided)
- **Timestamp**: Auto-managed (`created_at`, `updated_at`)
- **Size Limit**: 1 MB per document

**Collection** (Firestore Table)
- Group of related documents
- **7 collections in Pocket Journal**:
  - journal_entries (user writings)
  - entry_analysis (mood, summary)
  - insights (AI reflections)
  - journal_embeddings (vectors)
  - user_vectors (taste profiles)
  - media_cache (recommendations)
  - users (profiles)

**Index** (Query Optimization)
- Data structure for fast lookups
- **Single-field**: Indexed on one property
- **Composite**: Indexed on multiple properties
- **Example**: `(uid, created_at DESC)` for "all entries for user, newest first"
- **Cost**: Faster queries, slower writes

**TTL** (Time-to-Live, Document Expiration)
- Automatic deletion after specified duration
- **Implementation**: `expires_at` field + scheduled cleanup
- **Use**: Media cache cleanup (every 24 hours)
- **Cost**: Minimal (Firestore manages)

---

## External Services

**TMDb** (The Movie Database)
- Third-party API for movie data
- **Data**: Title, release date, poster, overview, ratings
- **Endpoints**: Popular, trending, top-rated, search
- **Rate Limit**: 40 requests/10 seconds (tier-dependent)
- **Quota**: Per-API-key usage tracking

**Spotify Web API** (Music Streaming)
- Third-party API for music/podcast data
- **Auth**: OAuth2 client credentials
- **Data**: Track, artist, album, preview URL, popularity
- **Search**: Full-text search with advanced filters
- **Rate Limit**: 429 backoff required (adaptive)

**Google Books API** (Book Database)
- Third-party API for book metadata
- **Data**: Title, author, publication date, thumbnail, ISBN
- **Search**: Queryable by title, author, ISBN
- **Rate Limit**: 1000 requests/day (free tier)
- **Quota**: Global project-level (not per-user)

**Google Gemini** (LLM API)
- Optional cloud-based large language model
- **Model**: gemini-2.0-flash
- **Use**: Insight generation (if local Qwen2 unavailable)
- **Auth**: API key
- **Fallback**: Used when local inference not available

---

## System Architecture

**Microservice** (vs Monolith)
- Independent, deployable service with single responsibility
- **Pocket Journal**: Primarily monolithic (Flask app)
- **Services**: Logically separated into modules
- **Future**: Could separate ML, caching into microservices

**Stateless Design** (No Server-Side State)
- Each request self-contained (no session storage)
- **Benefit**: Horizontal scaling (multiple instances)
- **Implementation**: JWT tokens carry auth info
- **Database**: Only Firestore holds state

**Event-Driven** (vs Request-Response)
- Asynchronous, decoupled communication
- **Pocket Journal**: Primarily synchronous
- **Future Consideration**: Queue-based insights generation

---

## Logging & Monitoring

**Log Level** (Verbosity Control)
- DEBUG: Detailed troubleshooting info
- INFO: Important events (entry created, analysis complete)
- WARNING: Recoverable issues (provider rate limited, fallback triggered)
- ERROR: Serious problems (model crash, API key invalid)
- CRITICAL: Service-breaking issues

**Structured Logging** (Machine-Readable Logs)
- Logs as JSON instead of plain text
- **Benefits**: Aggregation, filtering, alerting via log platform
- **Tools**: Cloud Logging, DataDog, ELK Stack

**Metrics** (Performance Quantification)
- Measurable data points (latency, error rate, throughput)
- **Examples**: p50, p95, p99 latencies; cache hit rate; error %
- **Tools**: Prometheus (collection), Grafana (visualization)

**SLA** (Service Level Agreement)
- Promised uptime/performance target
- **Example**: "99% uptime", "< 2s p99 latency"
- **Monitoring**: Track actual vs target

---

## Development & Operations

**Version Control** (Git Workflow)
- Git branching: main (stable), develop (integration), feature branches
- Commit messages: Semantic (feat, fix, docs, etc.)
- PR reviews: 2 approvals before merge

**CI/CD** (Continuous Integration/Deployment)
- Automated testing (on each commit)
- Automated deployment (on merge)
- **Tools**: GitHub Actions, Cloud Build

**Docker** (Containerization)
- Package app with dependencies
- **Benefits**: Reproducible, portable deployments
- **Base image**: nvidia/cuda (GPU support)

**Secrets Management** (Secure Credential Storage)
- Never commit API keys to version control
- **Storage**: Environment variables, Secret Manager
- **Rotation**: Every 90 days

---

## Quality Assurance

**Unit Test** (Single Function Testing)
- Test one function with mocked dependencies
- **Coverage**: Target > 80%
- **Framework**: pytest

**Integration Test** (Multi-Component Testing)
- Test services working together
- **Example**: Entry creation → mood analysis → Firestore storage

**E2E Test** (Full User Flow)
- Test complete workflows end-to-end
- **Example**: Create account → Add entry → Get recommendations
- **Tools**: Postman, Newman

**Load Test** (Stress Testing)
- Simulate many concurrent users
- **Goal**: Identify bottlenecks, verify SLA
- **Tools**: Locust, Apache Bench


