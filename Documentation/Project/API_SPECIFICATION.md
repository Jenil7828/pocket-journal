# API Specification: Pocket Journal Backend

## Overview

All endpoints require **Firebase JWT authentication** (except `/api/v1/auth/create-user` and `/api/v1/home`).

**Base URL**: `http://localhost:5000` (development) or `https://your-domain.com` (production)

**Authentication Header**:
```
Authorization: Bearer <firebase_id_token>
```

**Response Format**: JSON

---

## Authentication Endpoints

### Create User
**Endpoint**: `POST /api/v1/auth/create-user`

**Authentication**: None (public)

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "secure_password",
  "name": "John Doe"
}
```

**Response** (201):
```json
{
  "uid": "firebase_uid",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2026-03-29T10:30:00Z"
}
```

**Error Responses**:
- **400**: Missing email, password, or name
- **400**: Email already exists
- **500**: Firebase auth service error

---

## Journal Entries Endpoints

### Create Journal Entry
**Endpoint**: `POST /api/v1/entries`

**Authentication**: Required (Firebase JWT)

**Request Body**:
```json
{
  "entry_text": "Today was a great day. I felt happy and energized..."
}
```

**Response** (201):
```json
{
  "entry_id": "doc_id_123",
  "entry_text": "Today was a great day...",
  "created_at": "2026-03-29T10:30:00Z",
  "analysis": {
    "mood": "happy",
    "mood_probabilities": {
      "anger": 0.01,
      "disgust": 0.02,
      "fear": 0.01,
      "happy": 0.85,
      "neutral": 0.05,
      "sad": 0.03,
      "surprise": 0.03
    },
    "summary": "User felt happy and energized today."
  }
}
```

**Error Responses**:
- **400**: Missing or empty entry_text
- **401**: Invalid authentication token
- **500**: ML inference error (mood/summarization failed)

---

### Get User's Entries
**Endpoint**: `GET /api/v1/entries`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Results per page (max 100) |
| `offset` | int | 0 | Results offset (pagination) |
| `start_date` | string (ISO) | - | Filter: created_at >= start_date |
| `end_date` | string (ISO) | - | Filter: created_at <= end_date |
| `mood` | string | - | Filter by mood (exact match) |
| `sort` | string | "desc" | Sort by created_at: "asc" or "desc" |

**Response** (200):
```json
{
  "entries": [
    {
      "entry_id": "doc_id_123",
      "entry_text": "...",
      "created_at": "2026-03-29T10:30:00Z",
      "updated_at": "2026-03-29T10:30:00Z"
    },
    ...
  ],
  "total_count": 150,
  "limit": 10,
  "offset": 0
}
```

**Error Responses**:
- **400**: Invalid limit, offset, or date format
- **401**: Invalid authentication token
- **500**: Database error

---

### Get Single Entry
**Endpoint**: `GET /api/v1/entries/<entry_id>`

**Authentication**: Required

**Response** (200):
```json
{
  "entry_id": "doc_id_123",
  "entry_text": "Today was a great day...",
  "created_at": "2026-03-29T10:30:00Z",
  "updated_at": "2026-03-29T10:30:00Z",
  "uid": "user_uid"
}
```

**Error Responses**:
- **401**: Invalid authentication token
- **403**: Entry belongs to different user
- **404**: Entry not found
- **500**: Database error

---

### Get Entry Analysis
**Endpoint**: `GET /api/v1/entries/<entry_id>/analysis`

**Authentication**: Required

**Response** (200):
```json
{
  "entry_id": "doc_id_123",
  "mood": "happy",
  "mood_probabilities": {
    "anger": 0.01,
    "disgust": 0.02,
    "fear": 0.01,
    "happy": 0.85,
    "neutral": 0.05,
    "sad": 0.03,
    "surprise": 0.03
  },
  "summary": "User felt happy and energized today.",
  "created_at": "2026-03-29T10:30:00Z"
}
```

**Error Responses**:
- **401**: Invalid authentication token
- **403**: Entry belongs to different user
- **404**: Entry or analysis not found
- **500**: Database error

---

### Update Entry
**Endpoint**: `PUT /api/v1/entries/<entry_id>`

**Authentication**: Required

**Request Body**:
```json
{
  "entry_text": "Updated entry text..."
}
```

**Response** (200):
```json
{
  "entry_id": "doc_id_123",
  "entry_text": "Updated entry text...",
  "updated_at": "2026-03-29T11:45:00Z",
  "analysis": {
    "mood": "happy",
    "summary": "..."
  }
}
```

**Note**: Update triggers re-analysis (mood + summary)

---

### Delete Entry
**Endpoint**: `DELETE /api/v1/entries/<entry_id>`

**Authentication**: Required

**Response** (200):
```json
{
  "message": "Entry deleted successfully",
  "entry_id": "doc_id_123"
}
```

**Error Responses**:
- **401**: Invalid authentication token
- **403**: Entry belongs to different user
- **404**: Entry not found
- **500**: Database error

---

### Delete Entries (Batch)
**Endpoint**: `DELETE /api/v1/entries/batch`

**Authentication**: Required

**Request Body**:
```json
{
  "entry_ids": ["doc_id_1", "doc_id_2", "doc_id_3"]
}
```

**Response** (200):
```json
{
  "deleted_count": 3,
  "failed_ids": []
}
```

**Error Responses**:
- **400**: Missing or empty entry_ids array
- **401**: Invalid authentication token
- **500**: Database error

---

### Reanalyze Entry
**Endpoint**: `POST /api/v1/entries/<entry_id>/reanalyze`

**Authentication**: Required

**Response** (200):
```json
{
  "entry_id": "doc_id_123",
  "analysis": {
    "mood": "happy",
    "mood_probabilities": {...},
    "summary": "..."
  }
}
```

**Use Case**: Re-run mood detection and summarization (useful if ML models updated)

---

## Media Endpoints

### Get Media Recommendations
**Endpoint**: `GET /api/v1/<media_type>/recommend`

**Authentication**: Required

**Path Parameter**:
- `media_type`: `songs` | `movies` | `books` | `podcasts`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Number of results (max 50) |
| `language` | string | "neutral" | For songs/podcasts: `hindi`, `english`, `neutral` |

**Response** (200):
```json
{
  "mood": "happy",
  "recommendations": [
    {
      "title": "Inception",
      "release_date": "2010-07-16",
      "overview": "A skilled thief who steals corporate secrets...",
      "poster": "https://image.tmdb.org/t/p/w500/...",
      "popularity": 85.5,
      "media_type": "movies"
    },
    ...
  ],
  "source": "cache",
  "total_count": 10
}
```

**Error Responses**:
- **400**: Invalid media_type or limit
- **401**: Invalid authentication token
- **404**: No mood data available for today
- **500**: ML or provider error

---

### Search Media
**Endpoint**: `GET /api/v1/<media_type>/search`

**Authentication**: Required

**Path Parameter**:
- `media_type`: `songs` | `movies` | `books` | `podcasts`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Search string (artist, title, author, etc.) |
| `language` | string | No | For songs/podcasts: `hindi`, `english`, `neutral` |
| `limit` | int | No | Results count (default 20, max 50) |

**Response** (200):
```json
{
  "searched": "Inception",
  "results": [
    {
      "title": "Inception",
      "release_date": "2010-07-16",
      "overview": "A skilled thief...",
      "poster": "https://image.tmdb.org/t/p/w500/...",
      "popularity": 85.5,
      "match_score": 98.5
    },
    ...
  ],
  "metrics": {
    "cache_hit_count": 5,
    "fallback_triggered": false,
    "cache_latency_ms": 45.2,
    "provider_latency_ms": 0,
    "final_result_count": 10,
    "deduplication_count": 2
  }
}
```

**Note**: Uses cache-first strategy (Firestore) with fallback to live providers

---

### Bulk Media Search (Per Type)
**Endpoint**: `GET /api/v1/songs/search`, `GET /api/v1/movies/search`, etc.

Same as search above, but path-parameterized media type.

---

## Insights Endpoints

### Generate Insights
**Endpoint**: `POST /api/v1/generate_insights`

**Authentication**: Required

**Request Body**:
```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-29",
  "use_gemini": false
}
```

**Response** (200):
```json
{
  "insight_id": "insight_doc_id",
  "uid": "user_uid",
  "start_date": "2026-03-01",
  "end_date": "2026-03-29",
  "emotional_state": "Overall, you've been quite balanced with a lean towards positivity...",
  "goals": ["Maintain consistency in journaling", "Practice mindfulness daily"],
  "progress": "You've logged 28 entries in the past month with increasing frequency...",
  "negative_behaviors": "Tendency to ruminate on past events",
  "remedies": "Practice gratitude journaling, engage in physical activity",
  "appreciation": "You've shown great self-awareness and growth...",
  "conflicts": "Work-life balance remains a challenge",
  "created_at": "2026-03-29T12:00:00Z"
}
```

**Error Responses**:
- **400**: Invalid date range or format
- **401**: Invalid authentication token
- **404**: No entries in date range
- **500**: LLM unavailable (Qwen2 + Gemini both failed)

---

### Get User's Insights
**Endpoint**: `GET /api/v1/insights`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Results per page (max 100) |
| `offset` | int | 0 | Results offset (pagination) |

**Response** (200):
```json
{
  "insights": [
    {
      "insight_id": "insight_doc_id",
      "start_date": "2026-03-01",
      "end_date": "2026-03-29",
      "emotional_state": "...",
      "created_at": "2026-03-29T12:00:00Z"
    },
    ...
  ],
  "total_count": 12,
  "limit": 50,
  "offset": 0
}
```

---

### Get Single Insight
**Endpoint**: `GET /api/v1/insights/<insight_id>`

**Authentication**: Required

**Response** (200):
```json
{
  "insight_id": "insight_doc_id",
  "uid": "user_uid",
  "start_date": "2026-03-01",
  "end_date": "2026-03-29",
  "emotional_state": "...",
  "goals": [...],
  "progress": "...",
  "negative_behaviors": "...",
  "remedies": "...",
  "appreciation": "...",
  "conflicts": "...",
  "created_at": "2026-03-29T12:00:00Z"
}
```

---

## Statistics Endpoints

### Get Today's Mood Summary
**Endpoint**: `GET /api/v1/stats/mood_summary`

**Authentication**: Required

**Response** (200):
```json
{
  "date": "2026-03-29",
  "dominant_mood": "happy",
  "mood_distribution": {
    "anger": 0.01,
    "disgust": 0.02,
    "fear": 0.01,
    "happy": 0.75,
    "neutral": 0.12,
    "sad": 0.05,
    "surprise": 0.04
  },
  "entry_count": 2,
  "average_entry_length": 145
}
```

---

### Get Mood Timeline
**Endpoint**: `GET /api/v1/stats/mood_timeline`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 30 | Number of days to look back |

**Response** (200):
```json
{
  "timeline": [
    {
      "date": "2026-03-29",
      "dominant_mood": "happy",
      "entry_count": 2,
      "mood_distribution": {...}
    },
    {
      "date": "2026-03-28",
      "dominant_mood": "neutral",
      "entry_count": 1,
      "mood_distribution": {...}
    },
    ...
  ],
  "days": 30
}
```

---

### Get Entry Frequency Stats
**Endpoint**: `GET /api/v1/stats/frequency`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `period` | string | "month" | `week`, `month`, `year` |

**Response** (200):
```json
{
  "period": "month",
  "total_entries": 28,
  "average_per_day": 0.93,
  "average_per_week": 6.5,
  "most_active_hour": 22,
  "most_active_day": "Wednesday",
  "streak_current": 5,
  "streak_longest": 12
}
```

---

## Export Endpoints

### Export Entries to CSV
**Endpoint**: `GET /api/v1/export/csv`

**Authentication**: Required

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | string (ISO) | - | Include entries from this date |
| `end_date` | string (ISO) | - | Include entries until this date |
| `include_analysis` | bool | false | Include mood + summary columns |

**Response** (200):
- Content-Type: `text/csv`
- File download: `pocket_journal_export.csv`

**CSV Columns**:
```
Date,Title,EntryText,Mood,Summary
```

---

### Export Entries to JSON
**Endpoint**: `GET /api/v1/export/json`

**Authentication**: Required

**Query Parameters**: Same as CSV

**Response** (200):
```json
{
  "export_date": "2026-03-29T12:00:00Z",
  "total_entries": 150,
  "entries": [
    {
      "entry_id": "...",
      "entry_text": "...",
      "created_at": "...",
      "analysis": {
        "mood": "...",
        "summary": "..."
      }
    },
    ...
  ]
}
```

---

## User Profile Endpoints

### Get User Profile
**Endpoint**: `GET /api/v1/user/profile`

**Authentication**: Required

**Response** (200):
```json
{
  "uid": "firebase_uid",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2025-12-01T10:30:00Z",
  "entry_count": 150,
  "last_entry_at": "2026-03-29T10:30:00Z"
}
```

---

## Health/Status Endpoints

### Health Check
**Endpoint**: `GET /api/v1/health`

**Authentication**: None

**Response** (200):
```json
{
  "status": "ok",
  "services": {
    "firebase": "ok",
    "models": "ready",
    "cache": "ok"
  },
  "timestamp": "2026-03-29T12:00:00Z"
}
```

---

## Error Handling

### Standard Error Response
All errors return JSON:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "timestamp": "2026-03-29T12:00:00Z"
}
```

### Error Codes
| Code | Status | Meaning |
|------|--------|---------|
| `invalid_input` | 400 | Request validation failed |
| `unauthorized` | 401 | Missing or invalid authentication |
| `forbidden` | 403 | User lacks permission |
| `not_found` | 404 | Resource not found |
| `rate_limited` | 429 | Too many requests |
| `server_error` | 500 | Internal server error |

---

## Rate Limiting

**Provider Rate Limits** (Built-in):
- **TMDb**: 40 requests/10 seconds (tier dependent)
- **Spotify**: Varies by tier; 429 backoff handled
- **Google Books**: 1000 requests/day (free tier)

**Recommended Client Rate Limiting**:
- Max 5 recommendations requests/minute per user
- Max 10 search requests/minute per user
- Max 3 insights generation/day per user

---

## Authentication

### Getting a Firebase ID Token

**In Client Application**:
```javascript
// Web (Firebase SDK)
const idToken = await firebase.auth().currentUser.getIdToken();

// Mobile (Firebase SDK for iOS/Android)
let idToken = try await Auth.auth().currentUser?.getIDToken()
```

### Using in API Requests
```bash
curl -H "Authorization: Bearer $ID_TOKEN" \
  https://api.example.com/api/v1/entries
```

---

## Pagination

All list endpoints support cursor-based pagination:

**Query Parameters**:
- `limit` (default 10, max 100): Results per page
- `offset` (default 0): Starting position

**Response**:
```json
{
  "items": [...],
  "total_count": 150,
  "limit": 10,
  "offset": 0
}
```

---

## Response Times (p99 targets)

| Endpoint | Latency Target |
|----------|-----------------|
| Create Entry (with mood/summary) | 2500ms |
| Get Entry | 100ms |
| Search Media | 1500ms (cache hit), 3000ms (provider) |
| Get Recommendations | 1500ms |
| Generate Insights | 5000ms |
| List Entries | 300ms |
| Get Stats | 500ms |


