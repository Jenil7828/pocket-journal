# Pocket Journal — Media Recommendation System
## Phases 3 to 5: Technical Documentation

**Project:** Pocket Journal Backend  
**Component:** AI-Powered Media Recommendation Engine  
**Stack:** Flask, Firebase Firestore, Sentence-Transformers (all-mpnet-base-v2), Spotify API, TMDb API, Google Books API  
**Base path:** `Backend/services/media_recommender/`

---

## Table of Contents

1. [Current State After Phase 2.5](#current-state-after-phase-25)
2. [Phase 3 — Media Cache & Latency Reduction](#phase-3--media-cache--latency-reduction)
3. [Phase 4 — Personalization Feedback Loop](#phase-4--personalization-feedback-loop)
4. [Phase 5 — Multi-Modal & Advanced Ranking](#phase-5--multi-modal--advanced-ranking)
5. [Firestore Schema (Full)](#firestore-schema-full)
6. [Performance Targets](#performance-targets)
7. [Known Issues Carried Forward](#known-issues-carried-forward)
8. [Engineering Decisions & Tradeoffs](#engineering-decisions--tradeoffs)

---

## Current State After Phase 2.5

### What Works
- Intent vector built from taste + journal blend (adaptive beta)
- All 4 providers working: TMDb, Spotify songs, Google Books, Spotify podcasts
- Language filter working for songs and podcasts (hindi/english)
- All routes logging request/response with uid, email, duration_ms
- Response fields fully populated: poster_url, album_image_url, album_name, thumbnail_url, external_url

### Current Latency Profile (RTX 3040 4GB GPU, Docker)
| Stage | Time |
|---|---|
| Spotify/TMDb live fetch 200 items | 3–4s |
| Batch embed 200 candidates (GPU) | 3–4s |
| Firestore reads for intent (3 sequential) | 0.4s |
| Cosine similarity + ranking | <0.1s |
| **Total per request** | **~8–12s** |

### Known Issues Going Into Phase 3
- `publisher` field empty in podcast responses (Spotify episode search doesn't return full show object)
- Duplicate log lines on login (double route registration)
- 3 sequential Firestore reads for intent building (should be parallel)
- No process-level cache for media candidates (re-embeds 200 items on every request)

---

## Phase 3 — Media Cache & Latency Reduction

**Status:** 🔲 Not Started  
**Target latency:** < 2 seconds end-to-end  
**Depends on:** Phase 2.5 complete ✅

### Problem

### Completion Update

- Phase 3 implementation is complete and verified through the working cache refresh, cache status, and recommendation endpoints
- Cache-first recommendation flow is active for movies, songs, books, and podcasts
- Cache refresh jobs, forced refresh support, and background stale-cache refresh are implemented
- Cache writes now use incremental add-only behavior across all four media types
- Newly cached media entries now store an `added_at` timestamp
- This document section should be treated as the completed Phase 3 baseline for moving into Phase 4

Every recommendation request hits live external APIs and re-embeds 200 candidates from scratch. This is:
- Slow (8–12 seconds)
- Wasteful (same popular Bollywood songs embedded 1000x per day)
- Fragile (Spotify rate limit or downtime = failed request)

### Solution

Pre-fetch and pre-embed candidates daily. Store embedded candidates in Firestore with a `language` field for filtering. Serve recommendations directly from cache with zero external API calls and zero embedding compute at request time.

After response is sent, asynchronously check if cache is stale and trigger refresh in background — the user never waits for this.

---

### 3.1 Firestore Cache Schema

**Single collection per media type. Language as a field, not a separate collection.**

```
media_cache_movies/{tmdb_id}
├── id: str                        # TMDb movie id
├── title: str
├── description: str               # TMDb overview
├── poster_url: str                # Full URL: https://image.tmdb.org/t/p/w500{poster_path}
├── rating: float                  # vote_average
├── release_date: str              # YYYY-MM-DD
├── popularity: float              # TMDb popularity score
├── language: "neutral"            # movies don't have language filter — always "neutral"
├── embedding: List[float]         # 768-dim L2-normalized vector
└── cached_at: timestamp

media_cache_songs/{spotify_track_id}
├── id: str
├── title: str
├── description: str               # "Artist: X. Album: Y"
├── artist_names: str
├── album_name: str
├── album_image_url: str
├── external_url: str              # Spotify track URL
├── duration_ms: int
├── popularity: int                # Spotify popularity 0–100
├── language: "hindi" | "english" | "neutral"   ← FILTER KEY
├── embedding: List[float]
└── cached_at: timestamp

media_cache_books/{google_books_id}
├── id: str
├── title: str
├── description: str
├── authors: List[str]
├── thumbnail_url: str
├── published_date: str
├── page_count: int
├── info_link: str
├── language: "neutral"            # books not language-filtered currently
├── embedding: List[float]
└── cached_at: timestamp

media_cache_podcasts/{spotify_episode_id}
├── id: str
├── title: str
├── description: str
├── publisher: str                 # show name — enriched during cache build
├── show_image_url: str
├── external_url: str
├── duration_ms: int
├── release_date: str
├── language: "hindi" | "english" | "neutral"   ← FILTER KEY
├── embedding: List[float]
└── cached_at: timestamp

# Metadata document in each collection (not a media item)
media_cache_songs/_metadata
├── last_refreshed: timestamp
├── item_count: int
├── item_count_by_language: {hindi: int, english: int, neutral: int}
└── schema_version: str            # bump when schema changes to trigger full rebuild
```

**Why `language` as a field:**
- Single `collection.where("language", "==", "hindi").stream()` call
- No duplicate embedding storage across collections
- Neutral items (no language restriction) can be returned for any language query
- Adding a new language requires no schema change — just populate the field

**Why not a single `media_cache` collection with `media_type` field:**
- Firestore charges per document read regardless of filtering
- With a combined collection, reading 500 songs would also scan 500 movies
- Separate collections = only read what you need

---

### 3.2 Cache Store (`services/media_recommender/cache_store.py`)

Handles all Firestore cache reads and writes. No business logic — pure data layer.

```python
class MediaCacheStore:
    
    def __init__(self, db):
        self.db = db
    
    def collection_name(self, media_type: str) -> str:
        # "songs" -> "media_cache_songs"
        return f"media_cache_{media_type}"
    
    def read_cache(self, media_type: str, language: str = None) -> List[dict]:
        """
        Read all cached items for a media type, optionally filtered by language.
        
        For language-filtered reads:
        - If language="hindi": WHERE language == "hindi" OR language == "neutral"
        - If language="english": WHERE language == "english" OR language == "neutral"
        - If language=None: all items
        
        Returns list of dicts with all fields including embedding as List[float].
        Skips _metadata document automatically.
        
        Implementation note: Firestore does not support OR queries directly.
        Run two separate queries (one for the specific language, one for "neutral")
        and merge results in Python. Deduplicate by id.
        """
    
    def write_cache(self, media_type: str, items: List[dict]) -> None:
        """
        Batch write items to cache collection.
        Each item must have: id, title, description, embedding, language.
        
        Uses Firestore batch writes in chunks of 400 (max 500, leave headroom).
        Overwrites existing docs by id (idempotent).
        Writes _metadata doc after all items committed.
        
        _metadata.schema_version = current SCHEMA_VERSION constant.
        _metadata.last_refreshed = SERVER_TIMESTAMP.
        _metadata.item_count = len(items).
        _metadata.item_count_by_language = Counter(item["language"] for item in items).
        """
    
    def is_cache_fresh(self, media_type: str, max_age_hours: int = 24) -> bool:
        """
        Read _metadata.last_refreshed for the collection.
        Return True if (now - last_refreshed) < max_age_hours.
        Return False if _metadata doc doesn't exist.
        max_age_hours configurable via MEDIA_CACHE_MAX_AGE_HOURS env var.
        """
    
    def get_cache_stats(self, media_type: str) -> dict:
        """
        Return {item_count, last_refreshed, age_hours, is_fresh, item_count_by_language}.
        Used for health checks and monitoring.
        """
```

**Firestore batch write pattern:**
```python
BATCH_SIZE = 400  # Firestore max is 500, leave headroom for metadata doc

for i in range(0, len(items), BATCH_SIZE):
    batch = self.db.batch()
    chunk = items[i : i + BATCH_SIZE]
    for item in chunk:
        ref = self.db.collection(self.collection_name(media_type)).document(str(item["id"]))
        batch.set(ref, item)  # set = upsert (overwrites existing)
    batch.commit()

# Write metadata after all items
meta_ref = self.db.collection(self.collection_name(media_type)).document("_metadata")
meta_ref.set({
    "last_refreshed": firestore.SERVER_TIMESTAMP,
    "item_count": len(items),
    "item_count_by_language": dict(Counter(i["language"] for i in items)),
    "schema_version": SCHEMA_VERSION,
})
```

---

### 3.3 Cache Refresh Script (`scripts/cache_media.py`)

Standalone script. Runs as a daily cron job. No Flask context required.

**What it does per media type:**
1. Initialize the provider (no user context — fetches popular/trending content)
2. Fetch `CACHE_FETCH_LIMIT` candidates (default 500 per language bucket for songs/podcasts)
3. Assign `language` field to each item
4. Batch embed all candidates in one `embed_texts()` call
5. Write to Firestore via `cache_store.write_cache()`
6. Log: items fetched, items embedded, items written, total duration, per-language counts

**Language buckets for songs and podcasts:**
```python
LANGUAGE_BUCKETS = {
    "songs": [
        {"language": "hindi",   "queries": ["hindi songs", "bollywood hits", "hindi film songs"],   "market": "IN"},
        {"language": "english", "queries": ["english pop hits", "top english songs", "top 40"],     "market": "US"},
        {"language": "neutral", "queries": ["top hits", "popular songs"],                           "market": None},
    ],
    "podcasts": [
        {"language": "hindi",   "queries": ["hindi podcast", "bollywood podcast"],  "market": "IN"},
        {"language": "english", "queries": ["popular podcast", "top podcast"],      "market": "US"},
        {"language": "neutral", "queries": ["top podcast episodes"],                "market": None},
    ],
    "movies": [
        {"language": "neutral", "queries": None, "market": None},  # TMDb doesn't need query
    ],
    "books": [
        {"language": "neutral", "queries": None, "market": None},  # Google Books generic search
    ],
}
```

**Per-bucket fetch limit:** `500 // len(buckets)` items per bucket to stay within total limit.

**Embedding:** All items across all buckets are embedded in a single `embed_texts()` batch call per media type — minimizes model overhead.

**Enrichment during cache build:**
- Songs: `duration_ms` already fetched in provider
- Podcasts: fetch `show.name` via `/v1/episodes/{id}` for `publisher` field — this is where the empty publisher bug gets fixed, done once at cache build time not at request time
- Movies: `poster_url` already built in provider
- Books: `thumbnail_url` already extracted in provider

**Script interface:**
```bash
# Refresh all media types
python scripts/cache_media.py

# Refresh specific media type
python scripts/cache_media.py --media-type songs

# Dry run: fetch + embed but don't write to Firestore
python scripts/cache_media.py --dry-run

# Force refresh even if cache is fresh
python scripts/cache_media.py --force
```

**Cron schedule:**
```cron
0 3 * * * cd /app && python scripts/cache_media.py >> /var/log/cache_refresh.log 2>&1
```
3am daily — low traffic window, Spotify/TMDb rate limits reset overnight.

**Error handling:**
- If one media type fails, continue with the others — partial cache is better than no refresh
- Log failure with full traceback per media type
- If all media types fail, send alert (Phase 3: log only; Phase 4: webhook/email)

---

### 3.4 Modified Recommendation Pipeline (`recommendation.py`)

Cache-first flow with async background staleness check.

**Request flow:**
```
1. Build intent vector (unchanged, 3 Firestore reads — parallelized in Phase 3)
2. Determine cache key from media_type + language filter
3. Read from cache (Firestore query with language filter)
4. If cache empty → fall back to live pipeline (existing code, unchanged)
5. Run cosine similarity + ranking on cached embeddings
6. Format response
7. Send response to client  ← user gets result here
8. [Background] Check if cache is stale → trigger refresh if needed
```

**Cache key logic:**
```python
def _get_cache_language(filters: dict, media_type: str) -> str:
    if media_type not in ("songs", "podcasts"):
        return "neutral"
    lang = (filters or {}).get("language", "").lower()
    if lang in ("hi", "hindi"):
        return "hindi"
    if lang in ("en", "english"):
        return "english"
    return "neutral"
```

**Background refresh pattern (Flask after_this_request):**
```python
import threading

def _trigger_background_refresh(media_type: str):
    def _refresh():
        try:
            from scripts.cache_media import refresh_cache
            refresh_cache(media_type)
            logger.info("Background cache refresh complete: media_type=%s", media_type)
        except Exception as e:
            logger.warning("Background cache refresh failed: media_type=%s error=%s", media_type, str(e))
    
    thread = threading.Thread(target=_refresh, daemon=True)
    thread.start()

# In recommend_media, after results are ready but before return:
if not cache_store.is_cache_fresh(media_type):
    _trigger_background_refresh(media_type)
# Return results immediately — background refresh runs independently
```

**Why threading and not Celery/RQ:**
- No additional infrastructure required (no Redis, no worker process)
- Daemon threads are killed when main process exits — no zombie workers
- Cache refresh is idempotent — if it fails silently, next request will retry
- At current scale this is sufficient. Re-evaluate if refresh takes > 60 seconds

**Parallelized Firestore reads for intent building:**
```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def build_intent_vector(uid, media_type):
    with ThreadPoolExecutor(max_workers=3) as executor:
        f_taste   = executor.submit(_fetch_taste_vector, uid, media_type)
        f_journal = executor.submit(_fetch_latest_journal_embedding, uid)
        f_emotion = executor.submit(_fetch_latest_emotional_state, uid)
    
    taste_vec   = f_taste.result()    # blocks until done
    journal_vec = f_journal.result()
    emotion     = f_emotion.result()
    # All 3 reads happen in parallel → ~0.15s instead of ~0.45s
```

**Expected latency after Phase 3:**
| Stage | Before | After |
|---|---|---|
| External API fetch | 3–4s | 0s |
| Batch embedding | 3–4s | 0s |
| Firestore cache read (500 docs) | — | 0.3–0.8s |
| Intent Firestore reads (parallel) | 0.4s | 0.15s |
| Cosine similarity + ranking | 0.1s | 0.1s |
| **Total** | **8–12s** | **< 1.5s** |

---

### 3.5 Cache Staleness & Consistency

**Staleness threshold:** 24 hours default. Configurable:
```
MEDIA_CACHE_MAX_AGE_HOURS=24   # in .env
```

**Schema version:** `SCHEMA_VERSION = "v1"` constant in `cache_store.py`. If schema changes (new field added, field renamed), bump to `"v2"`. `is_cache_fresh()` also checks schema version — if version mismatch, treat cache as stale and trigger rebuild.

**Cache miss fallback:** If cache is empty or all items filtered out after language filter, fall back to live pipeline transparently. Log a warning. Never return empty results.

**Concurrent refresh safety:** If two requests trigger background refresh simultaneously, the second write will overwrite the first (last-write-wins). Firestore `set()` is atomic per document. This is acceptable — the result is a valid cache either way.

---

### 3.6 Process-Level In-Memory Cache (Optional Optimization)

If Firestore costs become a concern at scale, add an in-memory LRU cache on top of the Firestore cache:

```python
from functools import lru_cache
import time

_MEMORY_CACHE: dict = {}
_MEMORY_CACHE_TTL = 300  # 5 minutes

def read_cache_with_memory(media_type, language):
    key = f"{media_type}:{language}"
    entry = _MEMORY_CACHE.get(key)
    if entry and (time.time() - entry["ts"]) < _MEMORY_CACHE_TTL:
        return entry["data"]  # memory hit — zero Firestore reads
    
    data = cache_store.read_cache(media_type, language)
    _MEMORY_CACHE[key] = {"data": data, "ts": time.time()}
    return data
```

**Trade-off:** Each gunicorn worker has its own memory cache. With 4 workers, same data is cached 4 times. Acceptable at current scale. Use Redis if memory becomes a concern.

---

## Phase 4 — Personalization Feedback Loop

**Status:** 🔲 Planned  
**Depends on:** Phase 3 complete  
**Goal:** Taste vectors improve automatically based on what users interact with

### 4.1 Interaction Event API

New endpoint to receive implicit feedback signals from the mobile client.

```
POST /api/media/interaction
Authorization: Bearer {token}
Content-Type: application/json

{
    "media_type": "songs",
    "item_id": "spotify_track_id",
    "signal": "click" | "save" | "skip",
    "context": "recommendation" | "search"
}
```

**Signal weights:**
| Signal | Weight | Meaning |
|---|---|---|
| `click` | +0.02 | Mild positive — user tapped to see more |
| `save` | +0.05 | Strong positive — user explicitly saved |
| `skip` | -0.01 | Mild negative — user dismissed |

Response: `{"status": "ok", "updated": true | false}` (updated=false if rate limited)

**Firestore storage:**
```
user_interactions/{uid}/events/{auto_id}
├── media_type: str
├── item_id: str
├── signal: str
├── weight: float          # pre-computed from signal type
├── timestamp: timestamp
└── context: str
```

---

### 4.2 Taste Vector Online Update

When an interaction event arrives, update the user's taste vector for that media domain.

**Algorithm (lightweight gradient-free online update):**
```python
def update_taste_vector(uid, media_type, item_id, signal_weight):
    # 1. Get item embedding from cache
    item = cache_store.get_item(media_type, item_id)
    if not item or not item.get("embedding"):
        return False  # item not in cache, skip update
    
    item_vec = np.array(item["embedding"], dtype=np.float32)
    
    # 2. Get current taste vector
    uv_ref = db.collection("user_vectors").document(uid)
    uv_doc = uv_ref.get()
    domain_key = f"{media_type}_vector"
    current_vec = np.array(uv_doc.to_dict().get(domain_key, []), dtype=np.float32)
    
    if current_vec.size == 0:
        return False  # no taste vector yet, skip
    
    # 3. Apply update
    new_vec = current_vec + signal_weight * item_vec
    new_vec = new_vec / (np.linalg.norm(new_vec) + 1e-12)  # re-normalize
    
    # 4. Write back
    uv_ref.update({domain_key: new_vec.tolist(), "updated_at": firestore.SERVER_TIMESTAMP})
    return True
```

**Why this works:** The taste vector is an L2-normalized centroid of embedded content the user likes. Adding a small scaled version of a liked item's embedding nudges the centroid toward that item's semantic region. Subtracting (for skip) nudges it away.

**Rate limiting:** Max 1 taste vector update per user per media type per hour. Prevents a single binge session from overriding the long-term taste profile.

```python
def _is_rate_limited(uid, media_type) -> bool:
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent = (
        db.collection("user_interactions").document(uid)
        .collection("events")
        .where("media_type", "==", media_type)
        .where("timestamp", ">=", one_hour_ago)
        .count()
        .get()
    )
    return recent[0][0].value >= 10  # max 10 interactions per hour trigger update
```

---

### 4.3 Preference Initialization Improvement

Currently `PUT /me/preferences` embeds user's text preferences into taste vectors. Phase 4 improves this:

**Current (Phase 2.5):**
```
"I like Bollywood romance, AR Rahman" → embed entire string → songs_vector
```

**Phase 4 improvement:**
```
1. Parse preferences into structured fields: {artists: ["AR Rahman"], genres: ["Bollywood", "romance"]}
2. Look up matching items in media cache by artist/genre text match
3. Build taste vector as weighted average of matched items' embeddings
4. Much more accurate than embedding raw preference text
```

This gives new users a meaningful taste vector from day 1 without any interaction history.

---

### 4.4 Cold Start Strategy

New users with no journal entries and no interaction history have no vectors — recommendations would fail.

**Cold start flow:**
1. User creates account → `user_vectors` document does not exist
2. First `/me/preferences` call → builds initial taste vectors from preference text (Phase 4.3)
3. If preferences also empty → use generic popular content from cache (no personalization, no failure)
4. First journal entry → `journal_embeddings` document created → journal signal available
5. First interaction → taste vector starts updating

**Implementation in `build_intent_vector`:**
```python
if taste_vec is None and journal_vec is None:
    # Cold start: return generic popular recommendations
    logger.info("Cold start for uid=%s media_type=%s — using generic cache", uid, media_type)
    raise ColdStartException(media_type)  # caught in recommend_media

# In recommend_media:
except ColdStartException as e:
    # Skip intent building, return top items from cache sorted by popularity
    cache_items = cache_store.read_cache(e.media_type, language)
    cache_items.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    return format_results(e.media_type, cache_items[:top_k])
```

---

## Phase 5 — Multi-Modal & Advanced Ranking

**Status:** 🔲 Future  
**Depends on:** Phase 4 complete  
**Goal:** Smarter ranking, less redundancy, temporal awareness

### 5.1 Diversity Re-ranking (MMR)

After Phase 3/4 ranking produces top-50, apply Maximal Marginal Relevance to select final top-k with maximum diversity.

**MMR algorithm:**
```python
def mmr_rerank(intent_vec, candidates, top_k, lambda_param=0.7):
    """
    lambda_param: 0 = pure diversity, 1 = pure relevance. 0.7 = balanced.
    """
    selected = []
    remaining = list(candidates)
    
    while len(selected) < top_k and remaining:
        if not selected:
            # First pick: highest similarity to intent
            best = max(remaining, key=lambda c: c["similarity"])
        else:
            # Subsequent picks: balance relevance vs redundancy
            def mmr_score(candidate):
                relevance = candidate["similarity"]
                redundancy = max(
                    cosine_similarity(candidate["_embedding"], s["_embedding"])
                    for s in selected
                )
                return lambda_param * relevance - (1 - lambda_param) * redundancy
            best = max(remaining, key=mmr_score)
        
        selected.append(best)
        remaining.remove(best)
    
    return selected
```

**Why this matters:** Without MMR, top-10 songs might be 8 AR Rahman tracks from different albums — technically high similarity but not a useful recommendation set. MMR ensures variety.

**Configuration:** `MMR_LAMBDA=0.7` env var. Lower for more diversity, higher for more relevance.

---

### 5.2 Temporal Decay on Journal Embeddings

Instead of using only the most recent journal entry, blend the last N entries with exponential decay.

```python
def build_journal_vector_with_decay(uid, n_entries=5, decay_factor=0.5):
    """
    Fetch last n_entries journal embeddings.
    Weight by recency: today=1.0, yesterday=0.5, 2 days ago=0.25, etc.
    """
    entries = (
        db.collection("journal_embeddings")
        .where("uid", "==", uid)
        .order_by("created_at", direction="DESCENDING")
        .limit(n_entries)
        .stream()
    )
    
    weighted_sum = np.zeros(768, dtype=np.float32)
    total_weight = 0.0
    
    now = datetime.now(tz=pytz.UTC)
    for entry in entries:
        data = entry.to_dict()
        vec = np.array(data["embedding"], dtype=np.float32)
        days_ago = (now - data["created_at"]).days
        weight = decay_factor ** days_ago  # 0 days=1.0, 1 day=0.5, 2 days=0.25
        weighted_sum += weight * vec
        total_weight += weight
    
    if total_weight == 0:
        return None
    
    blended = weighted_sum / total_weight
    return blended / (np.linalg.norm(blended) + 1e-12)
```

**Why:** A user writing about stress for 3 days in a row should have stronger journal signal than someone who wrote one stressed entry a week ago but has been cheerful since.

---

### 5.3 Contextual Soft Filter

If the user's emotional state is extreme (very high arousal + very negative valence — detected distress), apply a soft downweight to content that is tonally mismatched.

**This is NOT a hard filter.** It is a 10–15% score adjustment.

```python
def apply_contextual_adjustment(scores, items, emotional_state):
    valence = emotional_state.get("valence", 0.0)
    arousal = emotional_state.get("arousal", 0.0)
    
    # Detect distress: high arousal + negative valence
    is_distressed = arousal > 0.7 and valence < -0.5
    
    if not is_distressed:
        return scores  # no adjustment
    
    for i, item in enumerate(items):
        desc = (item.get("description") or "").lower()
        title = (item.get("title") or "").lower()
        text = f"{title} {desc}"
        
        # Downweight aggressively upbeat content during distress
        upbeat_markers = ["party", "dance", "celebration", "banger", "hype", "club"]
        if any(marker in text for marker in upbeat_markers):
            scores[i] *= 0.85  # 15% penalty
    
    return scores
```

**Important:** This adjustment is applied after ranking, before final top-k selection. It does not remove items — it only reorders them slightly.

---

### 5.4 Cross-Domain Coherence Signal (Optional)

If a user has strong taste vectors across multiple domains, use cross-domain similarity as a weak additional signal.

**Example:** User loves Tamil movie soundtracks. Their `movies_vector` and `songs_vector` are both in a similar semantic region. When generating song recommendations, blend a small amount of the movies vector:

```python
cross_domain_weight = 0.05  # very small
songs_intent = normalize(
    0.95 * songs_intent_vec + 
    cross_domain_weight * movies_taste_vec  # borrow from movies taste
)
```

Only applied when:
1. Both domain vectors exist
2. Cosine similarity between them is > 0.6 (they are already coherent)
3. User has > 50 interactions (enough history to trust the pattern)

---

## Firestore Schema (Full)

### Existing Collections

```
users/{uid}
user_vectors/{uid}
journal_entries/{auto_id}
entry_analysis/{auto_id}
journal_embeddings/{auto_id}
insights/{auto_id}
insight_entry_mapping/{auto_id}
```

### Phase 3 Additions

```
media_cache_movies/{tmdb_id | "_metadata"}
media_cache_songs/{spotify_id | "_metadata"}
media_cache_books/{google_books_id | "_metadata"}
media_cache_podcasts/{spotify_episode_id | "_metadata"}
```

Each item doc: `{id, title, description, [media fields], language, embedding, added_at}`  
Each `_metadata` doc: `{last_refreshed, item_count, item_count_by_language, schema_version}`

### Phase 4 Additions

```
user_interactions/{uid}/events/{auto_id}
├── media_type: str
├── item_id: str
├── signal: "click" | "save" | "skip"
├── weight: float
├── timestamp: timestamp
└── context: "recommendation" | "search"
```

### Firestore Index Requirements

**Phase 3:**
```
Collection: media_cache_songs
  Composite index: language ASC, added_at DESC
  
Collection: media_cache_podcasts
  Composite index: language ASC, added_at DESC
```

**Phase 4:**
```
Collection: user_interactions/{uid}/events
  Composite index: media_type ASC, timestamp DESC
```

---

## Performance Targets

| Phase | P50 Latency | P99 Latency | Notes |
|---|---|---|---|
| 2.5 (current) | 8s | 15s | Live API + embedding on every request |
| 3 (cache) | 1.5s | 3s | Cache read + cosine only |
| 3 (memory cache) | 0.3s | 0.8s | Process-level LRU on top of Firestore |
| 4 (no change) | same as Phase 3 | same | Personalization adds no latency |
| 5 (MMR) | +0.05s | +0.1s | MMR over 50 candidates is negligible |

---

## Known Issues Carried Forward

| Issue | Phase to Fix | Notes |
|---|---|---|
| `publisher` empty in podcasts | Phase 3 cache build | Enrich via `/v1/episodes/{id}` at cache build time, not request time |
| Duplicate login log lines | Phase 3 cleanup | Double route registration in `register_all` |
| Sequential Firestore reads for intent | Phase 3 | Parallelize with `ThreadPoolExecutor` |
| No retry on Spotify 429 | Phase 3 | Add exponential backoff in cache refresh script |
| No integration tests | Ongoing | Minimum: test intent builder, cache store read/write, end-to-end recommendation |

---

## Engineering Decisions & Tradeoffs

### Why `language` as a field vs separate collections?

**Separate collections** (`media_cache_songs_hindi/`) would require:
- 3x write operations at cache build time
- Maintaining 3 metadata documents
- Schema changes duplicated across 3 collections
- Code that knows about collection naming by language

**Single collection with field** requires:
- Firestore composite index on `(language, added_at)`
- Two queries for "hindi OR neutral" (Firestore doesn't support OR)
- Merging two result sets in Python

The single-collection approach is cleaner operationally. The two-query overhead for language-filtered reads is ~50ms — negligible compared to the 1.5s we're targeting.

### Why threading for background refresh vs Celery/RQ?

At current scale (< 500 users), a full cache refresh takes 10–30 seconds. Daemon threads are sufficient:
- No Redis dependency
- No worker process to manage
- No task queue infrastructure
- If refresh fails, next request retries silently

Switch to Celery + Redis when:
- Refresh takes > 2 minutes (Spotify/TMDb API slowness)
- Need retry guarantees (not just best-effort)
- Need task monitoring/visibility

### Why not use Pinecone or Weaviate for cache?

Vector databases add operational complexity (another service to deploy, monitor, pay for). At 500 items × 4 types = 2000 vectors of 768 dimensions each:
- In-memory: 2000 × 768 × 4 bytes = ~6MB — trivially fits in RAM
- Firestore storage cost: negligible
- Query time with numpy matrix multiply: < 5ms

Re-evaluate when:
- Cache grows to > 50,000 items per type
- Similarity search becomes the measured bottleneck

### Why online taste vector updates instead of periodic retraining?

Periodic retraining (batch gradient descent on interaction history) would require:
- Storing all interaction history
- A training pipeline
- Model versioning
- Redeployment on new model

Online updates (add scaled item embedding to taste vector) require:
- One Firestore read + one Firestore write
- ~5ms total
- No model, no training, no deployment

The quality difference at our scale is unmeasurable. The operational difference is enormous. Switch to batch retraining if the online update approach shows drift or instability over time.

### Why cap beta (journal weight) at 0.40?

Testing showed that with `beta > 0.40`, a single unusual journal entry completely overrides weeks of taste history. Examples of the failure mode:
- User writes about a work presentation → song recommendations shift toward productivity podcasts
- User writes about watching a cricket match → movie recommendations shift toward sports documentaries

The 0.40 cap ensures taste profile (built over time, more stable) always has at least 60% weight. The journal provides recency and emotional context — it should influence, not dominate.
