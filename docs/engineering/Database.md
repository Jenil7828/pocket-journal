# DATABASE SPECIFICATION DOCUMENT
## Pocket Journal — Firestore Schema & Data Model

**Document Version:** 1.0  
**Last Updated:** April 18, 2026  
**Database:** Google Firestore (Cloud Firestore)

---

## TABLE OF CONTENTS
1. [Database Overview](#database-overview)
2. [Collections & Documents](#collections--documents)
3. [Data Types & Validation](#data-types--validation)
4. [Indexing Strategy](#indexing-strategy)
5. [Query Patterns](#query-patterns)
6. [Security Rules](#security-rules)
7. [Data Retention & Cleanup](#data-retention--cleanup)

---

## DATABASE OVERVIEW

### Technology Stack
- **Database**: Google Cloud Firestore (NoSQL)
- **Client Library**: firebase-admin (Python SDK)
- **Authentication**: Firebase Authentication (JWT tokens)
- **Region**: Multi-region replication
- **Backup**: Automatic daily backups, 30-day retention

### Design Principles
1. **Document-Centric**: Data organized in collections of documents
2. **Denormalization**: Some data duplication for performance
3. **Scalability**: Automated scaling, handles millions of documents
4. **Real-Time**: Built-in real-time listeners (for frontend)
5. **Security**: Row-level security via Firestore security rules

### Collections Overview

```
Database (Pocket Journal)
├── journal_entries/          # User journal entries
├── entry_analysis/           # Analysis results (mood, summary)
├── insights/                 # Generated insights
├── insight_entry_mapping/    # Insight-to-entry relationships
├── users/                    # User profiles & preferences
├── journal_embeddings/       # Entry embeddings for similarity
├── user_vectors/             # User taste vectors (Phase 4)
├── user_interactions/        # Media interaction logs
├── media_cache_movies/       # Cached movie recommendations
├── media_cache_songs/        # Cached song/music
├── media_cache_books/        # Cached book recommendations
└── media_cache_podcasts/     # Cached podcast episodes
```

---

## COLLECTIONS & DOCUMENTS

### 1. COLLECTION: journal_entries

**Purpose**: Store user's journal entries  
**Document ID**: Auto-generated UUID (document_id)  
**Indexing**: Yes  

#### Schema

```json
{
  "uid": "string (Firebase UID)",
  "title": "string (1-500 chars, optional)",
  "content": "string (1-5000 chars, required)",
  "tags": ["array of strings (0-10 items)"],
  "created_at": "timestamp (auto-set)",
  "updated_at": "timestamp (auto-set)"
}
```

#### Field Specifications

| Field | Type | Size | Validation | Indexed |
|-------|------|------|----------|---------|
| uid | String | ≤ 128 | Firebase UID format | YES |
| title | String | 1-500 | Optional, alphanumeric | NO |
| content | String | 1-5000 | Required, any text | YES |
| tags | Array | 0-10 items | Each tag 1-50 chars | NO |
| created_at | Timestamp | N/A | Server-set, immutable | YES |
| updated_at | Timestamp | N/A | Auto-updated on modify | YES |

#### Example Document

```json
{
  "document_id": "entry_550e8400_e29b_41d4_a716_446655440000",
  "uid": "firebase_uid_abc123",
  "title": "Amazing Day with Family",
  "content": "Today was wonderful. We spent time together and made lasting memories. The weather was perfect and we laughed a lot. Looking forward to more days like this.",
  "tags": ["family", "gratitude", "weekend"],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

#### Queries

```python
# Get user's entries (paginated)
query = db.collection('journal_entries')\
    .where('uid', '==', uid)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)\
    .limit(10)

# Get entries in date range
query = db.collection('journal_entries')\
    .where('uid', '==', uid)\
    .where('created_at', '>=', start_date)\
    .where('created_at', '<=', end_date)\
    .order_by('created_at', direction=firestore.Query.DESCENDING)

# Search by content (note: requires Firestore search or tokenization)
# Firestore doesn't support full-text search; implement via Python
query = db.collection('journal_entries')\
    .where('uid', '==', uid)
# Then filter in application layer
```

#### Indexes Required

```
Collection: journal_entries
1. (uid, created_at) - Composite index for pagination
2. (uid, updated_at) - For recent entries
3. (uid, title) - For title-based queries (if needed)
```

---

### 2. COLLECTION: entry_analysis

**Purpose**: Store analysis metadata (mood, summary) for entries  
**Document ID**: Auto-generated UUID  
**Parent**: related to journal_entries (no strict FK, denormalized)  

#### Schema

```json
{
  "entry_id": "string (FK to journal_entries)",
  "summary": "string (generated summary, max 500 chars)",
  "mood": {
    "anger": "number (0-1 probability)",
    "disgust": "number (0-1 probability)",
    "fear": "number (0-1 probability)",
    "happy": "number (0-1 probability)",
    "neutral": "number (0-1 probability)",
    "sad": "number (0-1 probability)",
    "surprise": "number (0-1 probability)"
  },
  "primary_mood": "string (mood label with highest score)",
  "confidence": "number (0-1, probability of primary mood)",
  "created_at": "timestamp"
}
```

#### Field Specifications

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| entry_id | String | Required, unique per entry | References journal_entries |
| summary | String | Max 500 chars | Generated by BART |
| mood | Map | Required | Contains 7 emotion probabilities |
| mood.* | Float | 0.0 ≤ value ≤ 1.0 | Sum should equal 1.0 |
| primary_mood | String | Required | Enum: [anger, disgust, fear, happy, neutral, sad, surprise] |
| confidence | Float | 0.0 ≤ value ≤ 1.0 | Probability of primary mood |
| created_at | Timestamp | Server-set | When analysis was completed |

#### Example Document

```json
{
  "document_id": "analysis_550e8400_e29b_41d4_a716_446655441111",
  "entry_id": "entry_550e8400_e29b_41d4_a716_446655440000",
  "summary": "Had a wonderful day with family. Made lasting memories together.",
  "mood": {
    "anger": 0.05,
    "disgust": 0.02,
    "fear": 0.03,
    "happy": 0.80,
    "neutral": 0.05,
    "sad": 0.03,
    "surprise": 0.02
  },
  "primary_mood": "happy",
  "confidence": 0.80,
  "created_at": "2025-01-15T10:31:00Z"
}
```

#### Indexes

```
Collection: entry_analysis
1. (entry_id) - Lookup by entry ID
2. (primary_mood, created_at) - Mood statistics queries
3. (created_at) - Time-based queries
```

---

### 3. COLLECTION: insights

**Purpose**: Store AI-generated insights from entries  
**Document ID**: Auto-generated UUID  
**Indexed**: Yes  

#### Schema

```json
{
  "uid": "string (Firebase UID)",
  "start_date": "string (YYYY-MM-DD)",
  "end_date": "string (YYYY-MM-DD)",
  "goals": [
    {
      "title": "string",
      "description": "string"
    }
  ],
  "progress": "string (description of progress)",
  "negative_behaviors": "string (identified patterns)",
  "remedies": "string (suggested improvements)",
  "appreciation": "string (positive aspects)",
  "conflicts": "string (identified conflicts)",
  "raw_response": "string (raw LLM output)",
  "created_at": "timestamp"
}
```

#### Field Specifications

| Field | Type | Constraint | Notes |
|-------|------|-----------|-------|
| uid | String | Required | Firebase UID |
| start_date | String | Required, YYYY-MM-DD format | Start of insight period |
| end_date | String | Required, YYYY-MM-DD format | End of insight period |
| goals | Array | 0-N items | Goal objects with title + description |
| progress | String | Max 1000 chars | Generated by LLM |
| negative_behaviors | String | Max 1000 chars | Pattern identification |
| remedies | String | Max 1000 chars | Suggested actions |
| appreciation | String | Max 1000 chars | Positive observations |
| conflicts | String | Max 1000 chars | Identified issues |
| raw_response | String | Unlimited | Raw LLM response for debugging |
| created_at | Timestamp | Server-set | When insight was generated |

#### Example Document

```json
{
  "document_id": "insight_550e8400_e29b_41d4_a716_446655442222",
  "uid": "firebase_uid_abc123",
  "start_date": "2025-01-01",
  "end_date": "2025-01-07",
  "goals": [
    {
      "title": "Exercise More",
      "description": "Increase daily physical activity to 30 minutes"
    },
    {
      "title": "Work-Life Balance",
      "description": "Reduce evening work stress, more family time"
    }
  ],
  "progress": "Good progress! 5 out of 7 days had exercise. Family time increased by 40%.",
  "negative_behaviors": "Tendency to stress-eat during high-pressure work days. Late-night work binges observed.",
  "remedies": "Try meditation for 10 minutes before meals. Set work end-time at 6 PM.",
  "appreciation": "Strong commitment to family goals. Resilience during challenges. Good self-awareness.",
  "conflicts": "Work deadlines conflict with family time on some evenings.",
  "raw_response": "{\"goals\": [...], ...}",
  "created_at": "2025-01-15T10:30:00Z"
}
```

#### Indexes

```
Collection: insights
1. (uid, created_at) - Get insights per user
2. (uid, start_date, end_date) - Query by date range
```

---

### 4. COLLECTION: insight_entry_mapping

**Purpose**: Map insights to source entries (many-to-many relationship)  
**Document ID**: Auto-generated  

#### Schema

```json
{
  "insight_id": "string (FK to insights)",
  "entry_id": "string (FK to journal_entries)"
}
```

#### Example Document

```json
{
  "document_id": "mapping_550e8400",
  "insight_id": "insight_550e8400_e29b_41d4_a716_446655442222",
  "entry_id": "entry_550e8400_e29b_41d4_a716_446655440000"
}
```

#### Indexes

```
Collection: insight_entry_mapping
1. (insight_id) - Get entries for an insight
2. (entry_id) - Get insights for an entry
```

---

### 5. COLLECTION: users

**Purpose**: User profiles and preferences  
**Document ID**: Firebase UID (no auto-generation)  

#### Schema

```json
{
  "uid": "string (document ID = Firebase UID)",
  "email": "string (unique, immutable)",
  "display_name": "string",
  "preferences": {
    "theme": "string (light|dark)",
    "notifications": "boolean",
    "language": "string (en|es|hi|...)"
  },
  "created_at": "timestamp (immutable)",
  "updated_at": "timestamp"
}
```

#### Example Document

```json
{
  "uid": "firebase_uid_abc123",
  "email": "user@example.com",
  "display_name": "John Doe",
  "preferences": {
    "theme": "dark",
    "notifications": true,
    "language": "en"
  },
  "created_at": "2024-07-18T10:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

### 6. COLLECTION: journal_embeddings

**Purpose**: Store embeddings of journal entries for similarity search  
**Document ID**: Auto-generated or entry_id-based  

#### Schema

```json
{
  "entry_id": "string (FK to journal_entries)",
  "uid": "string (FK to users)",
  "embedding": "array of numbers (384 dimensions)",
  "created_at": "timestamp",
  "version": "string (model version)"
}
```

#### Field Specifications

| Field | Type | Size | Notes |
|-------|------|------|-------|
| entry_id | String | ≤ 255 | Reference to journal entry |
| uid | String | ≤ 128 | User ID |
| embedding | Array | 384 floats | Sentence-Transformers output |
| created_at | Timestamp | N/A | Server-set |
| version | String | e.g., "all-mpnet-base-v2" | Model version used |

#### Indexes

```
Collection: journal_embeddings
1. (uid, created_at) - Get user's embeddings
2. (entry_id) - Lookup by entry
```

---

### 7. COLLECTION: user_vectors

**Purpose**: Store user taste vectors (Phase 4 personalization)  
**Document ID**: Auto-generated  

#### Schema

```json
{
  "uid": "string (FK to users)",
  "media_type": "string (movie|song|book|podcast)",
  "taste_vector": "array of numbers (384 dimensions)",
  "count_interactions": "number",
  "updated_at": "timestamp"
}
```

#### Notes
- Aggregated from user interactions
- Updated periodically (not real-time)
- Used for cold-start recommendations

---

### 8. COLLECTION: user_interactions

**Purpose**: Log user's interactions with recommendations (click, save, skip)  
**Document ID**: Auto-generated UUID  

#### Schema

```json
{
  "uid": "string (FK to users)",
  "media_id": "string (TMDb ID, Spotify ID, etc.)",
  "media_type": "string (movie|song|book|podcast)",
  "signal": "string (click|save|skip)",
  "context": "string (recommendation|search)",
  "timestamp": "timestamp",
  "recommendation_context": {
    "mood": "string (if from mood-based recommendation)"
  }
}
```

#### Example Document

```json
{
  "document_id": "interaction_550e8400",
  "uid": "firebase_uid_abc123",
  "media_id": "tmdb_movie_11",
  "media_type": "movie",
  "signal": "click",
  "context": "recommendation",
  "timestamp": "2025-01-15T10:30:00Z",
  "recommendation_context": {
    "mood": "happy"
  }
}
```

#### Indexes

```
Collection: user_interactions
1. (uid, timestamp) - Get user's recent interactions
2. (uid, media_type, signal) - Interaction stats
3. (media_id) - Global popularity tracking
```

#### Rate Limiting

- Max 10 interactions per media type per user per hour
- Enforced in application layer before insertions

---

### 9-12. COLLECTIONS: media_cache_*

**Purpose**: Cache media recommendations from external APIs  
**Collections**: 
- `media_cache_movies` (TMDb)
- `media_cache_songs` (Spotify)
- `media_cache_books` (Google Books)
- `media_cache_podcasts` (Podcast API)

#### Schema

```json
{
  "cache_key": "string (mood+query hash)",
  "media_id": "string (external provider ID)",
  "title": "string",
  "description": "string",
  "metadata": {
    "popularity": "number",
    "rating": "number",
    "genre": "string or array"
  },
  "embedding": "array (optional, for similarity)",
  "cached_at": "timestamp",
  "expires_at": "timestamp (24h from cached_at)"
}
```

#### Example Document (Movie)

```json
{
  "document_id": "cache_movie_550e8400",
  "cache_key": "happy_trending_movies",
  "media_id": "11",  # TMDb ID
  "title": "The Pursuit of Happiness",
  "description": "A story of perseverance...",
  "metadata": {
    "popularity": 85.5,
    "rating": 8.3,
    "genre": ["Drama", "Biography"]
  },
  "embedding": [0.12, 0.34, ..., 0.15],
  "cached_at": "2025-01-15T08:00:00Z",
  "expires_at": "2025-01-16T08:00:00Z"
}
```

#### TTL (Time-To-Live)

All media cache documents expire after 24 hours. Cleanup runs daily to remove expired entries.

---

## DATA TYPES & VALIDATION

### Standard Data Types

| Type | Format | Example | Validation |
|------|--------|---------|----------|
| String | UTF-8 | "hello" | Max 1MB per field |
| Number | Int64 or Float64 | 42 or 3.14 | Range depends on field |
| Boolean | true/false | true | N/A |
| Timestamp | Unix timestamp | 2025-01-15T10:30:00Z | ISO 8601 format |
| Array | [item1, item2, ...] | [1, 2, 3] | Max 20,000 elements |
| Map | {key: value} | {"name": "John"} | Nested depth ≤ 20 |
| Reference | DocumentReference | uid='user123' | Points to valid doc |

### Custom Validation Rules

#### Email
```
Pattern: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
```

#### Mood Labels
```
Enum: ['anger', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
```

#### Confidence Scores
```
Range: 0.0 ≤ value ≤ 1.0
Sum of all mood probabilities: ~1.0 (±0.01 due to floating point)
```

#### Date Format
```
Format: YYYY-MM-DD
Example: 2025-01-15
```

---

## INDEXING STRATEGY

### Automatic Indexes

Firestore automatically creates indexes for:
- Single-field queries (automatically indexed)
- Document IDs

### Composite Indexes (Must Be Created)

```
Collection: journal_entries
1. (uid, created_at DESC)
   - Usage: Get user's entries paginated by date
   - Query size: ~25MB/month (100 entries/user/month)

2. (uid, updated_at DESC)
   - Usage: Get recently modified entries
   - Query size: ~10MB/month

Collection: entry_analysis
1. (primary_mood, created_at DESC)
   - Usage: Mood statistics grouped by date
   - Query size: ~5MB/month

Collection: insights
1. (uid, created_at DESC)
   - Usage: Get user's insights chronologically
   - Query size: ~100KB/month (few insights/user)

Collection: user_interactions
1. (uid, timestamp DESC)
   - Usage: Get user's recent interactions
   - Query size: ~50MB/month (if active user)

2. (uid, media_type, signal)
   - Usage: Count interactions per media type per user
   - Query size: ~10MB/month
```

### Index Sizes & Costs

- **Estimated monthly index storage**: ~50MB
- **Index write cost**: $0.18 per 100K writes
- **Index query cost**: $0.06 per 100K reads

---

## QUERY PATTERNS

### Query 1: Get User's Entries (Paginated)

```python
def get_user_entries(uid: str, limit: int = 10, offset: int = 0):
    """Get user's entries with pagination"""
    query = db.collection('journal_entries')\
        .where('uid', '==', uid)\
        .order_by('created_at', direction=firestore.Query.DESCENDING)\
        .offset(offset)\
        .limit(limit)
    
    docs = query.stream()
    return [doc.to_dict() for doc in docs]

# Index required: (uid, created_at DESC)
# Complexity: O(limit) documents scanned
# Time: ~50-100ms
```

### Query 2: Get Entry Analysis by Entry ID

```python
def get_entry_analysis(entry_id: str):
    """Get mood analysis for an entry"""
    query = db.collection('entry_analysis')\
        .where('entry_id', '==', entry_id)\
        .limit(1)
    
    doc = query.stream()  # Should return single doc
    return next(doc, None).to_dict() if next(doc, None) else None

# No index required (single-field query)
# Time: ~10-20ms
```

### Query 3: Get Mood Statistics for Date Range

```python
def get_mood_stats(uid: str, start_date: str, end_date: str):
    """Get mood distribution for date range"""
    from datetime import datetime
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    query = db.collection('entry_analysis')\
        .where('created_at', '>=', start)\
        .where('created_at', '<=', end)
    
    # Join with journal_entries to filter by uid
    # (Two queries in app logic)
    
    docs = query.stream()
    moods = [doc.to_dict()['primary_mood'] for doc in docs]
    
    # Count occurrences
    from collections import Counter
    return dict(Counter(moods))

# Index required: (created_at) or (created_at, primary_mood)
# Time: ~100-200ms
```

### Query 4: Get User's Interactions for Media Ranking

```python
def get_user_interactions(uid: str, media_type: str):
    """Get all interactions for a user and media type"""
    query = db.collection('user_interactions')\
        .where('uid', '==', uid)\
        .where('media_type', '==', media_type)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)
    
    docs = query.stream()
    return [doc.to_dict() for doc in docs]

# Index required: (uid, media_type, timestamp DESC)
# Time: ~50-100ms
```

### Query 5: Bulk Insert (Batch Write)

```python
def cache_media_batch(items: list):
    """Cache multiple media items in batch"""
    batch = db.batch()
    
    for i, item in enumerate(items):
        doc_ref = db.collection('media_cache_movies').document()
        batch.set(doc_ref, item)
        
        if (i + 1) % 500 == 0:  # Firestore batch limit
            batch.commit()
            batch = db.batch()
    
    if items:
        batch.commit()

# Time: ~500ms for 500 items
```

---

## SECURITY RULES

### Firestore Security Rules

```firestore
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // --- journal_entries ---
    match /journal_entries/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
    }
    
    // --- entry_analysis ---
    match /entry_analysis/{document=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;  // Service backend writes
    }
    
    // --- insights ---
    match /insights/{document=**} {
      allow read, write: if request.auth != null && request.auth.uid == resource.data.uid;
      allow create: if request.auth != null && request.auth.uid == request.resource.data.uid;
    }
    
    // --- insight_entry_mapping ---
    match /insight_entry_mapping/{document=**} {
      allow read: if request.auth != null;
      allow write: if request.auth != null;  // Service backend manages
    }
    
    // --- users ---
    match /users/{uid} {
      allow read, write: if request.auth != null && request.auth.uid == uid;
    }
    
    // --- user_interactions ---
    match /user_interactions/{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // --- media_cache_* (public reads, backend writes) ---
    match /media_cache_movies/{document=**} {
      allow read: if request.auth != null;
      allow write: if false;  // Backend service writes only
    }
    
    match /media_cache_songs/{document=**} {
      allow read: if request.auth != null;
      allow write: if false;
    }
    
    match /media_cache_books/{document=**} {
      allow read: if request.auth != null;
      allow write: if false;
    }
    
    match /media_cache_podcasts/{document=**} {
      allow read: if request.auth != null;
      allow write: if false;
    }
  }
}
```

### Security Principles

1. **Authentication-First**: All writes require valid Firebase token
2. **Ownership**: Users can only access their own data (journal_entries, insights)
3. **Read-Only Cache**: Media caches are read-only from frontend
4. **Backend Service**: Backend service has expanded permissions via service account

---

## DATA RETENTION & CLEANUP

### Retention Policy

| Collection | Retention | Cleanup Frequency |
|-----------|-----------|-------------------|
| journal_entries | Indefinite | Never (user-initiated delete) |
| entry_analysis | Indefinite | Never (with entry) |
| insights | Indefinite | Never (user-initiated delete) |
| user_interactions | 90 days | Daily |
| media_cache_* | 24 hours | Daily |

### Cleanup Scripts

#### Remove Expired Media Cache

```python
def cleanup_expired_cache():
    """Remove media cache entries older than 24 hours"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now(tz=pytz.UTC) - timedelta(hours=24)
    
    collections = [
        'media_cache_movies',
        'media_cache_songs',
        'media_cache_books',
        'media_cache_podcasts'
    ]
    
    for coll_name in collections:
        query = db.collection(coll_name)\
            .where('cached_at', '<', cutoff_time)
        
        docs = query.stream()
        count = 0
        
        for doc in docs:
            doc.reference.delete()
            count += 1
        
        print(f"Deleted {count} expired entries from {coll_name}")

# Run daily at 2 AM UTC
```

#### Archive Old Interactions

```python
def archive_old_interactions():
    """Delete interactions older than 90 days"""
    from datetime import datetime, timedelta
    
    cutoff_time = datetime.now(tz=pytz.UTC) - timedelta(days=90)
    
    query = db.collection('user_interactions')\
        .where('timestamp', '<', cutoff_time)
    
    docs = query.stream()
    count = 0
    
    for doc in docs:
        doc.reference.delete()
        count += 1
    
    print(f"Deleted {count} old interactions")

# Run daily at 3 AM UTC
```

---

## BACKUP & RECOVERY

### Automated Backups
- **Frequency**: Daily
- **Retention**: 30 days
- **Location**: Multi-region (GCP managed)
- **Cost**: Included in Firestore pricing

### Export Strategy
- **Frequency**: Weekly manual export to Cloud Storage
- **Format**: Firestore backup format
- **Retention**: 90 days in Cloud Storage
- **Location**: `gs://pocket-journal-backups/`

### Disaster Recovery
- **RTO** (Recovery Time Objective): < 1 hour
- **RPO** (Recovery Point Objective): < 24 hours
- **Process**: Restore from automated backup or manual export

---

**END OF DATABASE SPECIFICATION**

