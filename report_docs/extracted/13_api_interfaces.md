# 🔌 API Interfaces

## Authentication Mechanism

All protected endpoints require Firebase JWT token in Authorization header:
```
Authorization: Bearer <JWT_TOKEN>
```

Token must be valid Firebase ID token with `uid` and `email` claims.
Health and home endpoints are public (no auth required).

## Journal Management Endpoints

### POST /api/v1/journal
**Create new journal entry**

**Request**:
```json
{
  "entry_text": "Today was wonderful. I felt happy about the achievement.",
  "title": "Great Day"  // Optional
}
```

**Response** (200 OK):
```json
{
  "entry_id": "doc123",
  "created_at": "2025-01-18T10:30:00Z",
  "mood": {
    "anger": 0.05,
    "disgust": 0.02,
    "fear": 0.01,
    "happy": 0.8,
    "neutral": 0.1,
    "sad": 0.01,
    "surprise": 0.01
  },
  "summary": "Had a great day with a meaningful achievement.",
  "analysis_id": "analysis456"
}
```

**Error Responses**:
- 400: Missing entry_text
- 401: Invalid token
- 500: Processing error

---

### GET /api/v1/journal
**List all journal entries with filtering**

**Query Parameters**:
- `start_date`: YYYY-MM-DD (optional)
- `end_date`: YYYY-MM-DD (optional)
- `mood`: Mood filter - one of [anger, disgust, fear, happy, neutral, sad, surprise] (optional)
- `search`: Text search filter (optional)
- `limit`: 1-100, default 50
- `offset`: ≥0, default 0

**Response** (200 OK):
```json
{
  "entries": [
    {
      "entry_id": "doc123",
      "entry_text": "Today was wonderful...",
      "title": "Great Day",
      "created_at": "2025-01-18T10:30:00Z",
      "mood": { ... },
      "summary": "Had a great day..."
    }
  ],
  "total_count": 15,
  "returned_count": 10,
  "limit": 10,
  "offset": 0
}
```

---

### GET /api/v1/journal/search
**Search journal entries by text and date range**

**Query Parameters**:
- `query`: Search string (required)
- `start_date`: YYYY-MM-DD (optional)
- `end_date`: YYYY-MM-DD (optional)
- `limit`: 1-50, default 20

**Response** (200 OK):
```json
{
  "results": [
    {
      "entry_id": "doc123",
      "entry_text": "...",
      "summary": "...",
      "created_at": "2025-01-18T10:30:00Z",
      "entry_id": "doc123"
    }
  ],
  "total_count": 3,
  "query": "vacation",
  "filters": {
    "start_date": "2025-01-01",
    "end_date": "2025-01-31"
  }
}
```

---

### GET /api/v1/journal/{entry_id}
**Get single journal entry**

**URL Parameters**:
- `entry_id`: Document ID

**Response** (200 OK):
```json
{
  "entry_id": "doc123",
  "entry_text": "Full entry text...",
  "title": "Great Day",
  "created_at": "2025-01-18T10:30:00Z",
  "updated_at": "2025-01-18T10:35:00Z",
  "mood": { ... },
  "summary": "..."
}
```

**Error Responses**:
- 403: Not owned by user
- 404: Entry not found

---

### PUT /api/v1/journal/{entry_id}
**Update journal entry content**

**Request**:
```json
{
  "entry_text": "Updated text here",
  "title": "Updated Title"  // Optional
}
```

**Response** (200 OK):
```json
{
  "entry_id": "doc123",
  "entry_text": "Updated text here",
  "updated_at": "2025-01-18T11:00:00Z",
  "mood": { ... },  // Re-analyzed
  "summary": "..."  // Re-summarized
}
```

---

### DELETE /api/v1/journal/{entry_id}
**Delete journal entry and associated data**

**Response** (200 OK):
```json
{
  "message": "Entry deleted successfully",
  "entry_id": "doc123"
}
```

---

## Insights Endpoints

### POST /api/v1/insights/generate
**Generate insights for date range**

**Request**:
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-07"
}
```

**Response** (200 OK):
```json
{
  "goals": [
    {
      "title": "Exercise",
      "description": "Daily morning runs"
    }
  ],
  "progress": "Good progress on fitness routine",
  "negative_behaviors": "Late night scrolling affecting sleep",
  "remedies": "Set phone curfew at 10 PM, establish evening routine",
  "appreciation": "Consistent waking times are improving mood",
  "conflicts": "Work deadlines conflicting with personal time"
}
```

**Error Responses**:
- 400: Invalid date format
- 500: LLM generation failed

---

### GET /api/v1/insights
**List all insights for user**

**Query Parameters**:
- `limit`: 1-50, default 50
- `offset`: ≥0, default 0

**Response** (200 OK):
```json
{
  "insights": [
    {
      "insight_id": "insight123",
      "goals": [...],
      "progress": "...",
      "created_at": "2025-01-08T12:00:00Z"
    }
  ],
  "count": 5,
  "limit": 50,
  "offset": 0
}
```

---

### GET /api/v1/insights/{insight_id}
**Get single insight**

**URL Parameters**:
- `insight_id`: Document ID

**Response** (200 OK):
```json
{
  "insight": {
    "insight_id": "insight123",
    "goals": [...],
    "progress": "...",
    "negative_behaviors": "...",
    "remedies": "...",
    "appreciation": "...",
    "conflicts": "...",
    "created_at": "2025-01-08T12:00:00Z"
  }
}
```

---

### DELETE /api/v1/insights/{insight_id}
**Delete insight and associated mappings**

**Response** (200 OK):
```json
{
  "message": "Insight deleted successfully",
  "insight_id": "insight123",
  "mappings_deleted": 5
}
```

---

## Media Recommendation Endpoints

### GET /api/v1/movies/recommend
**Get movie recommendations**

**Query Parameters**:
- `genre`: Genre filter (optional)
- `mood`: Mood filter (optional)
- `search`: Search query (optional)
- `sort`: default | rating | trending | recent (default: default)
- `limit`: 1-100, default 10
- `offset`: ≥0, default 0

**Response** (200 OK):
```json
{
  "media_type": "movies",
  "recommendations": [
    {
      "id": "550",
      "title": "Fight Club",
      "description": "An insomniac office worker and a devil-may-care soapmaker...",
      "genre": ["Drama", "Thriller"],
      "rating": 8.8,
      "popularity": 45.5,
      "image_url": "https://...",
      "year": 1999
    }
  ],
  "total_count": 42,
  "returned_count": 10,
  "offset": 0,
  "limit": 10,
  "filters": {
    "genre": null,
    "mood": null,
    "search": null,
    "sort": "default"
  }
}
```

---

### GET /api/v1/songs/recommend
**Get song recommendations**

**Query Parameters**: Same as movies + `language` (hindi | english | neutral)

**Response** (200 OK):
```json
{
  "media_type": "songs",
  "recommendations": [
    {
      "id": "spotify:123",
      "title": "Bohemian Rhapsody",
      "artist": "Queen",
      "album": "A Night at the Opera",
      "duration_ms": 354000,
      "popularity": 85,
      "preview_url": "https://...",
      "external_urls": { "spotify": "https://..." }
    }
  ],
  "total_count": 120,
  "returned_count": 10,
  "offset": 0,
  "limit": 10,
  "filters": {
    "language": "english"
  }
}
```

---

### GET /api/v1/books/recommend
**Get book recommendations**

**Query Parameters**: Same as movies

**Response** (200 OK):
```json
{
  "media_type": "books",
  "recommendations": [
    {
      "id": "google:123",
      "title": "The Great Gatsby",
      "author": "F. Scott Fitzgerald",
      "description": "A classic of American literature...",
      "genre": ["Fiction", "Classics"],
      "rating": 4.5,
      "image_url": "https://...",
      "publish_year": 1925
    }
  ],
  "total_count": 85,
  "returned_count": 10,
  "offset": 0,
  "limit": 10
}
```

---

### GET /api/v1/podcasts/recommend
**Get podcast recommendations**

**Query Parameters**: Same as songs

**Response** (200 OK):
```json
{
  "media_type": "podcasts",
  "recommendations": [
    {
      "id": "spotify:podcast123",
      "title": "The Joe Rogan Experience",
      "description": "Long-form conversational podcast...",
      "publisher": "Joe Rogan",
      "language": "english",
      "episode_count": 1500,
      "popularity": 95,
      "image_url": "https://..."
    }
  ],
  "total_count": 200,
  "returned_count": 10
}
```

---

### GET /api/v1/{media_type}/search
**Search media across cache and providers**

**URL Parameters**:
- `media_type`: movies | songs | books | podcasts

**Query Parameters**:
- `query`: Search string (required)
- `limit`: 1-100, default 20

**Response** (200 OK):
```json
{
  "media_type": "movies",
  "query": "inception",
  "results": [
    {
      "id": "27205",
      "title": "Inception",
      "description": "...",
      "rating": 8.8,
      "year": 2010
    }
  ],
  "total_count": 12,
  "returned_count": 10,
  "source": "cache"  // or "provider" if fallback used
}
```

---

### POST /api/v1/media/interaction
**Track user interaction with media**

**Request**:
```json
{
  "media_type": "movies",
  "media_id": "550",
  "signal": "save",
  "context": "recommendation"
}
```

**Valid Values**:
- `signal`: click | save | skip
- `context`: recommendation | search
- `media_type`: movies | songs | books | podcasts

**Response** (200 OK):
```json
{
  "message": "Interaction recorded successfully",
  "media_type": "movies",
  "media_id": "550",
  "signal": "save",
  "timestamp": "2025-01-18T10:30:00Z"
}
```

**Error Responses**:
- 400: Invalid signal, context, or media_type
- 429: Rate limit exceeded (>10 per hour for media_type)

---

## User and System Endpoints

### GET /api/v1/user/settings
**Get user settings**

**Response** (200 OK):
```json
{
  "uid": "user123",
  "settings": {
    "mood_tracking_enabled": true,
    "theme": "dark",
    "language": "en"
  }
}
```

---

### PUT /api/v1/user/settings
**Update user settings**

**Request**:
```json
{
  "mood_tracking_enabled": false,
  "theme": "light"
}
```

**Response** (200 OK): Updated settings object

---

### GET /api/v1/health
**Health check (no auth required)**

**Response** (200 OK):
```json
{
  "status": "ok",
  "timestamp": "2025-01-18T10:30:00Z",
  "services": {
    "database": "connected",
    "models": {
      "mood_detection": "loaded",
      "summarization": "loaded",
      "embeddings": "loaded",
      "insights": "loaded" // or "gemini" if using cloud
    }
  }
}
```

**Response** (503 Service Unavailable) if system unavailable

---

### GET /api/v1/export/data
**Export user data**

**Query Parameters**:
- `format`: json | csv | pdf (default: json)

**Response** (200 OK):
- Content-Type: application/json (or text/csv, application/pdf)
- Body: Complete user data in requested format

**Response Body** (JSON):
```json
{
  "user_id": "user123",
  "export_date": "2025-01-18T10:30:00Z",
  "entries": [...],
  "insights": [...],
  "interactions": [...]
}
```

---

## Error Response Format

All error responses follow this format:

```json
{
  "error": "Human-readable error message",
  "details": "Technical details (optional)",
  "status": 400,
  "timestamp": "2025-01-18T10:30:00Z"
}
```

**Common Status Codes**:
- 200: Success
- 400: Bad request (invalid parameters)
- 401: Unauthorized (missing/invalid token)
- 403: Forbidden (insufficient permissions)
- 404: Not found
- 429: Rate limit exceeded
- 500: Internal server error
- 503: Service unavailable

---

## Rate Limiting

- **Interactions**: Max 10 per media type per hour
- **General**: No global rate limit (implement via API gateway if needed)
- **Response Header**: `X-RateLimit-Remaining` included in interaction responses

---

## Pagination

All list endpoints support pagination with:
- `limit`: Items per page (1-100, default varies)
- `offset`: Starting index (0-based)
- **Response includes**: `total_count`, `returned_count`, `limit`, `offset`

---

## Date Format

All dates use ISO 8601 format:
- Timestamps: `2025-01-18T10:30:00Z` (UTC)
- Date-only: `2025-01-18` (YYYY-MM-DD, local timezone)

