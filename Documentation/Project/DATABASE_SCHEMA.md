# Database Schema: Pocket Journal

## Firestore Collections Overview

```
pocket-journal-db/
├── journal_entries/        (User-written entries)
├── entry_analysis/         (ML analysis: mood, summary)
├── journal_embeddings/     (Entry semantic vectors)
├── insights/               (AI-generated reflections)
├── insight_entry_mapping/  (Insight → Entry relationships)
├── users/                  (User profiles)
├── user_vectors/           (User taste embeddings)
└── media_cache/            (Cached media from providers)
```

---

## Collection: `journal_entries`

**Purpose**: Store raw journal entry text and metadata

**Document Structure**:
```json
{
  "uid": "firebase_auth_uid",
  "entry_text": "Today was productive. I completed the project milestone...",
  "created_at": Timestamp("2026-03-29 10:30:00 IST"),
  "updated_at": Timestamp("2026-03-29 10:30:00 IST")
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uid` | string | Yes | Firebase Auth UID (owner) |
| `entry_text` | string | Yes | Journal entry content (unbounded) |
| `created_at` | timestamp | Yes | Entry creation time (IST) |
| `updated_at` | timestamp | Yes | Last modification time |

**Indexes**:
- Composite: `(uid, created_at DESC)` — Fast user entry listing
- Single: `uid` — Query by user
- Single: `created_at` — Time-based queries

**Document ID**: Auto-generated (Firestore default)

**Data Lifecycle**:
- Created: On POST `/api/v1/entries`
- Updated: On PUT `/api/v1/entries/<id>` (entry_text + updated_at)
- Deleted: On DELETE `/api/v1/entries/<id>` (cascade deletes analysis)
- Retention: Indefinite (user can delete manually)

**Example Query**:
```python
# Get all entries for user, ordered by date (newest first)
db.collection("journal_entries").where("uid", "==", user_id).order_by("created_at", direction="DESCENDING").limit(10).stream()
```

---

## Collection: `entry_analysis`

**Purpose**: Store ML-generated mood, summary, and raw analysis data

**Document Structure**:
```json
{
  "entry_id": "journal_entries/doc_id_123",
  "emotional_state": {
    "dominant_mood": "happy",
    "confidence": 0.85,
    "alternative_moods": [
      {"mood": "surprised", "probability": 0.08},
      {"mood": "neutral", "probability": 0.05}
    ]
  },
  "summary": "User had a productive day completing project milestone.",
  "raw_analysis": {
    "mood_probs": {
      "anger": 0.01,
      "disgust": 0.02,
      "fear": 0.01,
      "happy": 0.85,
      "neutral": 0.05,
      "sad": 0.03,
      "surprise": 0.03
    },
    "model_version": "roberta-v2"
  },
  "created_at": Timestamp("2026-03-29 10:30:00 IST")
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | string | Yes | Reference to journal_entries doc ID |
| `emotional_state` | object | Yes | Parsed mood with confidence + alternatives |
| `summary` | string | Yes | AI-generated summary (20-128 tokens) |
| `raw_analysis` | object | No | Raw model outputs (probabilities, version) |
| `created_at` | timestamp | Yes | Analysis generation time |

**Backward Compatibility Fields** (for legacy code):
- `mood` (string): Alias for `emotional_state.dominant_mood`

**Indexes**:
- Single: `entry_id` — Fast lookup by entry
- Single: `created_at` — Time-based queries

**Document ID**: Auto-generated

**Data Lifecycle**:
- Created: After entry creation (async via ML pipeline)
- Updated: On `/api/v1/entries/<id>/reanalyze` (re-run mood/summary)
- Deleted: Cascade delete when entry deleted
- Retention: Indefinite (tied to entry lifecycle)

---

## Collection: `journal_embeddings`

**Purpose**: Store dense semantic vectors (embeddings) for intent-based recommendations

**Document Structure**:
```json
{
  "entry_id": "journal_entries/doc_id_123",
  "uid": "firebase_auth_uid",
  "embedding": [0.12, -0.34, 0.56, ... (768 dimensions)],
  "model_version": "all-mpnet-base-v2",
  "created_at": Timestamp("2026-03-29 10:30:00 IST")
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `entry_id` | string | Yes | Reference to journal_entries doc ID |
| `uid` | string | Yes | User UID (for filtering by user) |
| `embedding` | array[float] | Yes | 768-dimensional vector (sentence-transformers) |
| `model_version` | string | Yes | Model used (e.g., "all-mpnet-base-v2") |
| `created_at` | timestamp | Yes | Embedding generation time |

**Vector Specification**:
- **Dimensions**: 768
- **Model**: `sentence-transformers/all-mpnet-base-v2`
- **Normalization**: L2-normalized for cosine similarity

**Indexes**:
- Single: `uid` — Query user's embeddings
- Single: `entry_id` — Find embedding by entry

**Document ID**: Typically matches `entry_id` for efficiency

**Data Lifecycle**:
- Created: After entry creation (async, ~200-300ms)
- Deleted: Cascade delete when entry deleted
- Retention: Indefinite (tied to entry lifecycle)

**Usage**:
- Fetch latest embedding for user (max 1, for intent building)
- Query all embeddings for user (for taste profile aggregation)

---

## Collection: `user_vectors`

**Purpose**: Store aggregated user taste embeddings (for recommendation personalization)

**Document Structure**:
```json
{
  "uid": "firebase_auth_uid",
  "taste_vector": [0.15, -0.22, 0.41, ... (768 dimensions)],
  "entry_count": 150,
  "last_updated_at": Timestamp("2026-03-29 10:30:00 IST"),
  "blend_weights": {
    "journal_blend_weight": 0.05,
    "taste_blend_weight": 0.95
  }
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uid` | string | Yes | Firebase Auth UID (PK) |
| `taste_vector` | array[float] | Yes | Aggregated 768-dim preference vector |
| `entry_count` | int | Yes | Number of entries used in aggregate |
| `last_updated_at` | timestamp | Yes | Last recompute time |
| `blend_weights` | object | Yes | Weights for intent blending |

**Indexes**:
- None (UID is primary key)

**Document ID**: User UID (matches `uid` field)

**Data Lifecycle**:
- Created: First entry creation for new user
- Updated: Periodically (e.g., daily batch job) or on-demand
- Retention: Indefinite (one per user)

**Computation** (In Intent Builder):
```
Intent Vector = (Journal Embedding × journal_blend_weight) + (Taste Vector × taste_blend_weight)
Default Weights: Journal 5%, Taste 95%
```

---

## Collection: `insights`

**Purpose**: Store AI-generated reflections and summaries

**Document Structure**:
```json
{
  "uid": "firebase_auth_uid",
  "start_date": "2026-03-01",
  "end_date": "2026-03-29",
  "emotional_state": "Overall, you've been quite balanced with a lean towards positivity...",
  "goals": [
    "Maintain consistency in journaling",
    "Practice mindfulness daily"
  ],
  "progress": "You've logged 28 entries in the past month...",
  "negative_behaviors": "Tendency to ruminate on past events",
  "remedies": "Practice gratitude journaling, engage in physical activity",
  "appreciation": "You've shown great self-awareness and growth...",
  "conflicts": "Work-life balance remains a challenge",
  "raw_response": "Full LLM output (JSON or text)",
  "created_at": Timestamp("2026-03-29 12:00:00 IST")
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uid` | string | Yes | User UID (owner) |
| `start_date` | string | Yes | Insight period start (ISO format) |
| `end_date` | string | Yes | Insight period end (ISO format) |
| `emotional_state` | string | Yes | Parsed emotional summary |
| `goals` | array[string] | Yes | Recommended goals |
| `progress` | string | Yes | Progress summary |
| `negative_behaviors` | string | Yes | Identified patterns |
| `remedies` | string | Yes | Suggested improvements |
| `appreciation` | string | Yes | Positive reinforcement |
| `conflicts` | string | Yes | Identified tensions |
| `raw_response` | string | No | Full LLM output (for debugging) |
| `created_at` | timestamp | Yes | Insight generation time |

**Indexes**:
- Composite: `(uid, created_at DESC)` — User insight listing
- Single: `uid` — Query by user

**Document ID**: Auto-generated

**Data Lifecycle**:
- Created: On POST `/api/v1/generate_insights`
- Deleted: Manual deletion only (no automatic retention policy)
- Retention: Indefinite (valuable historical data)

**Example Query**:
```python
# Get recent insights for user
db.collection("insights").where("uid", "==", user_id).order_by("created_at", direction="DESCENDING").limit(10).stream()
```

---

## Collection: `insight_entry_mapping`

**Purpose**: Track which entries contributed to each insight (for traceability)

**Document Structure**:
```json
{
  "insight_id": "insights/insight_doc_id",
  "entry_ids": [
    "journal_entries/doc_id_1",
    "journal_entries/doc_id_2",
    "journal_entries/doc_id_3"
  ],
  "entry_count": 3,
  "created_at": Timestamp("2026-03-29 12:00:00 IST")
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `insight_id` | string | Yes | Reference to insights doc |
| `entry_ids` | array[string] | Yes | List of contributing entry IDs |
| `entry_count` | int | Yes | Count for quick reference |
| `created_at` | timestamp | Yes | Mapping creation time |

**Indexes**:
- Single: `insight_id` — Find entries for insight
- Single: `entry_ids` (array) — Find insights for entry

**Document ID**: Auto-generated or `{insight_id}` for uniqueness

**Data Lifecycle**:
- Created: When insight is generated
- Deleted: Manual deletion only
- Retention: Indefinite

---

## Collection: `users`

**Purpose**: Store user profile and account metadata

**Document Structure**:
```json
{
  "uid": "firebase_auth_uid",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": Timestamp("2025-12-01 10:30:00 IST"),
  "last_login_at": Timestamp("2026-03-29 09:15:00 IST"),
  "entry_count": 150,
  "preferences": {
    "mood_tracking_enabled": true,
    "insights_enabled": true,
    "recommendations_language": "english"
  }
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `uid` | string | Yes | Firebase Auth UID (PK) |
| `email` | string | Yes | User email (from Firebase Auth) |
| `name` | string | Yes | Display name |
| `created_at` | timestamp | Yes | Account creation time |
| `last_login_at` | timestamp | No | Last authentication time |
| `entry_count` | int | Yes | Total entries (cached) |
| `preferences` | object | No | User settings |

**Indexes**:
- None (UID is primary key)

**Document ID**: User UID

**Data Lifecycle**:
- Created: On user registration (POST `/api/v1/auth/create-user`)
- Updated: On profile changes or periodic sync
- Retention: Indefinite (tied to Firebase Auth account)

---

## Collection: `media_cache`

**Purpose**: Cache media recommendations from external providers (TMDb, Spotify, Google Books)

**Document Structure**:
```json
{
  "media_type": "movies",
  "language": "neutral",
  "provider": "tmdb",
  "media_items": [
    {
      "title": "Inception",
      "release_date": "2010-07-16",
      "overview": "A skilled thief who steals corporate secrets...",
      "poster": "https://image.tmdb.org/t/p/w500/...",
      "popularity": 85.5,
      "id": "27205"
    },
    ...
  ],
  "item_count": 50,
  "fetched_at": Timestamp("2026-03-29 10:30:00 IST"),
  "expires_at": Timestamp("2026-03-30 10:30:00 IST"),
  "schema_version": "v1"
}
```

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `media_type` | string | Yes | `movies`, `songs`, `books`, `podcasts` |
| `language` | string | Yes | For songs/podcasts: `hindi`, `english`, `neutral` |
| `provider` | string | Yes | Source: `tmdb`, `spotify`, `google_books` |
| `media_items` | array[object] | Yes | Cached media (standardized schema) |
| `item_count` | int | Yes | Number of items |
| `fetched_at` | timestamp | Yes | When cache was populated |
| `expires_at` | timestamp | Yes | TTL expiration (24h from fetched_at) |
| `schema_version` | string | Yes | Schema version (for migrations) |

**Standardized Media Item Schema**:
```json
{
  "title": "string",
  "release_date": "string (YYYY-MM-DD)",
  "overview": "string",
  "poster": "string (URL)",
  "popularity": "float",
  "id": "string (provider-specific ID)"
}
```

**Indexes**:
- Composite: `(media_type, language, expires_at)` — Cache invalidation queries
- Single: `media_type` — Type-based lookup
- Single: `expires_at` — TTL cleanup

**Document ID**: Auto-generated or `{media_type}_{language}_{provider}`

**Data Lifecycle**:
- Created: On first media recommendation request
- Updated: On provider fetch (new items, refreshed timestamps)
- Expired: Firestore TTL auto-delete (expires_at)
- Manual Cleanup: Background job queries `expires_at < NOW()` and deletes

**TTL Configuration**:
- `MEDIA_CACHE_MAX_AGE_HOURS`: 24 (configurable in config.yml)
- Firestore TTL Policy: Soft delete (expires_at field) + background cleanup

**Query Examples**:
```python
# Get fresh cache for movie recommendations
db.collection("media_cache").where("media_type", "==", "movies").where("expires_at", ">", datetime.now()).limit(1).stream()

# Cleanup expired cache (manual or batch job)
db.collection("media_cache").where("expires_at", "<", datetime.now()).stream()
```

---

## Firestore Security Rules

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // User owns their entries, analysis, embeddings
    match /journal_entries/{document=**} {
      allow read, write: if request.auth.uid == resource.data.uid;
    }
    match /entry_analysis/{document=**} {
      allow read: if request.auth.uid != null;  // Cross-user queries for insights
      allow write: if request.auth.token.iss == "..."  // Backend service only
    }
    match /journal_embeddings/{document=**} {
      allow read, write: if request.auth.uid == resource.data.uid;
    }
    match /insights/{document=**} {
      allow read: if request.auth.uid == resource.data.uid;
      allow write: if request.auth.token.iss == "..."  // Backend service only
    }
    match /media_cache/{document=**} {
      allow read: if request.auth.uid != null;  // Shared cache (all users can read)
      allow write: if request.auth.token.iss == "..."  // Backend service only
    }
    // ... etc for other collections
  }
}
```

---

## Indexing Strategy

### Composite Indexes (Critical for Performance)

| Collection | Fields | Order | Use Case |
|------------|--------|-------|----------|
| `journal_entries` | (uid, created_at) | uid ASC, created_at DESC | User entry listing |
| `entry_analysis` | (uid, created_at) | uid ASC, created_at DESC | User analysis history |
| `insights` | (uid, created_at) | uid ASC, created_at DESC | User insight listing |
| `media_cache` | (media_type, language, expires_at) | ASC, ASC, ASC | Cache freshness checks |

### Single Field Indexes

- All `uid` fields for user-scoped queries
- All `created_at` fields for time-based sorting
- `entry_id` for cross-collection references

---

## Data Relationships (Logical)

```
User (Firebase Auth)
  ├── journal_entries (1:N)
  │   ├── entry_analysis (1:1)
  │   ├── journal_embeddings (1:1)
  │   └── insight_entry_mapping → insights (1:N)
  ├── insights (1:N)
  │   └── insight_entry_mapping (1:N entry refs)
  ├── user_vectors (1:1)
  └── users profile (1:1)

External
  └── media_cache (Shared by all users)
```

---

## Data Migration Strategy

**Versioning**: Schema version in config (`media_cache.schema_version`)

**Migration Example** (Hypothetical):
```python
# If schema_version changes from "v1" to "v2"
# Background job migrates: media_cache.v1 → media_cache.v2

def migrate_media_cache_v1_to_v2():
    """Add new field 'rating' to media_items"""
    for cache_doc in db.collection("media_cache").where("schema_version", "==", "v1").stream():
        items = cache_doc.get("media_items")
        for item in items:
            if "rating" not in item:
                item["rating"] = 0  # Default
        cache_doc.reference.update({
            "media_items": items,
            "schema_version": "v2"
        })
```

---

## Query Performance Targets

| Query | Target Latency |
|-------|-----------------|
| Get entries for user (limit 10) | 50ms |
| Get single entry | 20ms |
| Get entry analysis | 30ms |
| Query insights (limit 10) | 60ms |
| Get fresh media cache | 40ms |
| Fetch embeddings for user | 100ms |


