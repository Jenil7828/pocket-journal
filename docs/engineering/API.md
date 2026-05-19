# API SPECIFICATION DOCUMENT
## Pocket Journal — REST API Reference

**Document Version:** 1.0  
**Last Updated:** April 18, 2026  
**Base URL:** `http://localhost:5000` (or `/api` prefix)

---

## TABLE OF CONTENTS
1. [Authentication](#authentication)
2. [Journal Entries API](#journal-entries-api)
3. [Mood & Analysis API](#mood--analysis-api)
4. [Insights API](#insights-api)
5. [Media Recommendations API](#media-recommendations-api)
6. [Analytics & Statistics API](#analytics--statistics-api)
7. [Data Export API](#data-export-api)
8. [User Profile API](#user-profile-api)
9. [System Health API](#system-health-api)
10. [Error Codes](#error-codes)

---

## AUTHENTICATION

### Token-Based Authentication (Firebase JWT)

All protected endpoints require Bearer token in Authorization header:

```
Authorization: Bearer <firebase_id_token>
```

#### Request Header Format
```
GET /api/entries HTTP/1.1
Host: localhost:5000
Authorization: Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IkFCQzEyMzQ1Njc4OTAifQ...
Content-Type: application/json
```

#### 1.1 Register User
```
POST /api/auth/register
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "display_name": "John Doe"
}

Response (201 Created):
{
  "uid": "firebase_uid_string",
  "email": "user@example.com",
  "display_name": "John Doe",
  "created_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  409 Conflict: Email already registered
  400 Bad Request: Invalid email format or weak password
```

#### 1.2 Login User
```
POST /api/auth/login
Content-Type: application/json

Request Body:
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

Response (200 OK):
{
  "uid": "firebase_uid_string",
  "token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IkFCQzEyMzQ1Njc4OTAifQ...",
  "expires_in": 3600,
  "token_type": "Bearer"
}

Error Responses:
  401 Unauthorized: Invalid credentials
  404 Not Found: User not found
```

---

## JOURNAL ENTRIES API

### 2.1 Create Journal Entry

```
POST /api/entries
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "title": "My Wonderful Day",
  "content": "Today was fantastic. I achieved my goals and spent time with family. The weather was beautiful...",
  "tags": ["family", "achievement", "gratitude"]
}

Validation:
  - title: 1-500 characters (optional)
  - content: 1-5000 characters (required)
  - tags: Array of max 10 tags, each 1-50 characters

Response (201 Created):
{
  "entry_id": "entry_uuid_123456",
  "uid": "user_firebase_id",
  "title": "My Wonderful Day",
  "content": "Today was fantastic...",
  "tags": ["family", "achievement", "gratitude"],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  400 Bad Request: Content missing or exceeds limit
  401 Unauthorized: Invalid or missing token
  500 Internal Server Error: Database error
```

### 2.2 Retrieve All Entries (Paginated)

```
GET /api/entries?limit=10&offset=0&sort=DESC
Authorization: Bearer {token}

Query Parameters:
  - limit: Number of results (default=10, max=100)
  - offset: Pagination offset (default=0)
  - sort: Sort order (ASC|DESC, default=DESC by created_at)
  - start_date: Filter from date (YYYY-MM-DD, optional)
  - end_date: Filter to date (YYYY-MM-DD, optional)

Response (200 OK):
{
  "entries": [
    {
      "entry_id": "entry_uuid_1",
      "title": "My Day",
      "content": "Full content...",
      "tags": ["tag1"],
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z",
      "mood": {
        "primary": "happy",
        "confidence": 0.85
      },
      "summary": "Had a great day with family..."
    },
    ...
  ],
  "total": 25,
  "limit": 10,
  "offset": 0,
  "has_more": true
}

Error Responses:
  401 Unauthorized: Invalid token
  400 Bad Request: Invalid query parameters
```

### 2.3 Get Entry by ID

```
GET /api/entries/{entry_id}
Authorization: Bearer {token}

Path Parameters:
  - entry_id: UUID of the entry

Response (200 OK):
{
  "entry_id": "entry_uuid_123456",
  "uid": "user_firebase_id",
  "title": "My Wonderful Day",
  "content": "Today was fantastic...",
  "tags": ["family"],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "analysis": {
    "mood": {
      "anger": 0.05, "disgust": 0.02, "fear": 0.03,
      "happy": 0.75, "neutral": 0.08, "sad": 0.05, "surprise": 0.02
    },
    "primary_mood": "happy",
    "confidence": 0.75,
    "summary": "A great day with family...",
    "embedding": [0.12, 0.34, ..., 0.15]  # 384 dimensions
  }
}

Error Responses:
  404 Not Found: Entry not found
  403 Forbidden: Access denied (not entry owner)
  401 Unauthorized: Invalid token
```

### 2.4 Update Entry

```
PUT /api/entries/{entry_id}
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "title": "Updated Title",
  "content": "Updated content text...",
  "tags": ["tag1", "tag2"]
}

Note: Send only fields to update

Response (200 OK):
{
  "entry_id": "entry_uuid_123456",
  "title": "Updated Title",
  "content": "Updated content...",
  "tags": ["tag1", "tag2"],
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T11:45:00Z",
  "analysis": {
    "mood": {...},
    "primary_mood": "happy",
    "summary": "Updated summary..."
  }
}

Error Responses:
  400 Bad Request: Invalid input
  403 Forbidden: Not entry owner
  404 Not Found: Entry not found
  401 Unauthorized: Invalid token
```

### 2.5 Delete Entry

```
DELETE /api/entries/{entry_id}
Authorization: Bearer {token}

Response (204 No Content):
(Empty body on success)

Cascade Deletes:
  - Deletes from entry_analysis
  - Deletes from insight_entry_mapping
  - Removes from insights relationships

Error Responses:
  403 Forbidden: Not entry owner
  404 Not Found: Entry not found
  401 Unauthorized: Invalid token
```

### 2.6 Search Entries

```
GET /api/entries/search?q=happy&limit=20
Authorization: Bearer {token}

Query Parameters:
  - q: Search query (required, min 3 chars)
  - limit: Max results (default=20, max=100)

Response (200 OK):
{
  "query": "happy",
  "results": [
    {
      "entry_id": "...",
      "title": "...",
      "content": "...",
      "relevance_score": 0.95,
      "created_at": "..."
    },
    ...
  ],
  "total": 5,
  "limit": 20
}

Error Responses:
  400 Bad Request: Query too short
  401 Unauthorized: Invalid token
```

---

## MOOD & ANALYSIS API

### 3.1 Analyze Entry for Mood (Trigger Analysis)

```
POST /api/entries/{entry_id}/analyze
Authorization: Bearer {token}

Note: Automatically triggered on entry creation.
This endpoint can be called to re-analyze an existing entry.

Response (200 OK):
{
  "entry_id": "entry_uuid",
  "analysis": {
    "mood": {
      "anger": 0.05, "disgust": 0.02, "fear": 0.03,
      "happy": 0.75, "neutral": 0.08, "sad": 0.05, "surprise": 0.02
    },
    "primary_mood": "happy",
    "confidence": 0.75,
    "summary": "Had an amazing day with great achievements",
    "embedding": [0.12, 0.34, ..., 0.15]
  },
  "analyzed_at": "2025-01-15T10:32:00Z"
}

Error Responses:
  404 Not Found: Entry not found
  403 Forbidden: Not entry owner
  500 Internal Server Error: ML inference failed
  503 Service Unavailable: Models not loaded
```

### 3.2 Get Mood History

```
GET /api/mood/history?start_date=2025-01-01&end_date=2025-01-31&granularity=daily
Authorization: Bearer {token}

Query Parameters:
  - start_date: Start date (YYYY-MM-DD, required)
  - end_date: End date (YYYY-MM-DD, required)
  - granularity: daily|weekly|monthly (default=daily)
  - limit: Max results (default=100)

Response (200 OK):
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "granularity": "daily",
  "moods": [
    {
      "date": "2025-01-01",
      "primary_mood": "happy",
      "confidence": 0.85,
      "mood_scores": {
        "anger": 0.05, "disgust": 0.02, "fear": 0.03,
        "happy": 0.85, "neutral": 0.03, "sad": 0.01, "surprise": 0.01
      },
      "entries_count": 2,
      "avg_confidence": 0.82
    },
    ...
  ],
  "summary": {
    "most_frequent_mood": "happy",
    "avg_confidence": 0.78,
    "mood_distribution": {
      "happy": 15, "sad": 5, "angry": 2, ...
    }
  }
}

Error Responses:
  400 Bad Request: Invalid date format
  401 Unauthorized: Invalid token
```

---

## INSIGHTS API

### 4.1 Generate Insights

```
POST /api/insights/generate
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-07",
  "include_recommendations": true
}

Validation:
  - Date range: min 1 day, max 1 year
  - Requires: at least 2 entries in range

Response (200 OK):
{
  "insight_id": "insight_uuid_123456",
  "uid": "user_id",
  "start_date": "2025-01-01",
  "end_date": "2025-01-07",
  "goals": [
    {
      "title": "Exercise More",
      "description": "Increase daily physical activity"
    },
    {
      "title": "Better Work-Life Balance",
      "description": "Reduce work stress, more family time"
    }
  ],
  "progress": "Good progress on exercise with 5 out of 7 days active...",
  "negative_behaviors": "Tendency to stress-eat during work anxiety...",
  "remedies": "Try meditation sessions, take regular breaks...",
  "appreciation": "Strong commitment to family time, good resilience...",
  "conflicts": "None identified in this period",
  "recommendations": [
    {
      "type": "action",
      "description": "Continue morning exercise routine"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  400 Bad Request: Invalid date range or insufficient entries
  401 Unauthorized: Invalid token
  503 Service Unavailable: LLM backend down
  504 Gateway Timeout: LLM inference timed out
```

### 4.2 Retrieve Insights

```
GET /api/insights?start_date=2025-01-01&end_date=2025-01-31&limit=10
Authorization: Bearer {token}

Query Parameters:
  - start_date: Filter from date (YYYY-MM-DD, optional)
  - end_date: Filter to date (YYYY-MM-DD, optional)
  - limit: Max results (default=10, max=100)
  - offset: Pagination offset (default=0)

Response (200 OK):
{
  "insights": [
    {
      "insight_id": "insight_uuid_1",
      "start_date": "2025-01-01",
      "end_date": "2025-01-07",
      "goals": [...],
      "progress": "...",
      "created_at": "2025-01-15T10:30:00Z"
    },
    ...
  ],
  "total": 5,
  "limit": 10,
  "offset": 0
}

Error Responses:
  401 Unauthorized: Invalid token
  400 Bad Request: Invalid parameters
```

### 4.3 Get Insight Details

```
GET /api/insights/{insight_id}
Authorization: Bearer {token}

Response (200 OK):
{
  "insight_id": "insight_uuid",
  "start_date": "2025-01-01",
  "end_date": "2025-01-07",
  "goals": [...],
  "progress": "...",
  "negative_behaviors": "...",
  "remedies": "...",
  "appreciation": "...",
  "conflicts": "...",
  "mapped_entries": [
    {
      "entry_id": "...",
      "title": "...",
      "mood": "happy"
    }
  ],
  "created_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  404 Not Found: Insight not found
  403 Forbidden: Access denied
  401 Unauthorized: Invalid token
```

---

## MEDIA RECOMMENDATIONS API

### 5.1 Get Movie Recommendations

```
GET /api/media/movies?mood=happy&top_k=10
Authorization: Bearer {token}

Query Parameters:
  - mood: Mood label (happy|sad|angry|fear|neutral, optional)
  - top_k: Number of recommendations (default=10, max=50)
  - exclude_ids: Comma-separated IDs to exclude (optional)

Response (200 OK):
{
  "mood": "happy",
  "media_type": "movie",
  "recommendations": [
    {
      "id": "tmdb_movie_123456",
      "title": "The Pursuit of Happiness",
      "overview": "A story of perseverance and success...",
      "release_date": "2006-12-15",
      "popularity": 85.5,
      "vote_average": 8.3,
      "vote_count": 12540,
      "poster_path": "/path/to/poster.jpg",
      "genre_ids": [18, 36],  # Drama, History
      "score": 0.92,
      "reason": "Based on your positive mood"
    },
    ...
  ],
  "total_returned": 10,
  "generated_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  400 Bad Request: Invalid mood or top_k
  401 Unauthorized: Invalid token
  503 Service Unavailable: Provider unavailable
```

### 5.2 Get Music Recommendations

```
GET /api/media/songs?mood=happy&top_k=10
Authorization: Bearer {token}

Query Parameters:
  - mood: Mood label (optional)
  - top_k: Number of recommendations (default=10, max=50)
  - language: Language preference (hindi|english|neutral, optional)

Response (200 OK):
{
  "mood": "happy",
  "media_type": "song",
  "recommendations": [
    {
      "id": "spotify_track_123456",
      "title": "Walking on Sunshine",
      "artist": "Katrina and The Waves",
      "album": "Walking on Sunshine",
      "release_date": "1985-01-01",
      "popularity": 75,
      "preview_url": "https://p.scdn.co/mp3-preview/...",
      "external_urls": {
        "spotify": "https://open.spotify.com/track/..."
      },
      "duration_ms": 216000,
      "score": 0.89,
      "reason": "High energy, matches happy mood"
    },
    ...
  ],
  "total_returned": 10,
  "generated_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
  503 Service Unavailable: Spotify API down
```

### 5.3 Get Book Recommendations

```
GET /api/media/books?mood=sad&top_k=10
Authorization: Bearer {token}

Query Parameters:
  - mood: Mood label (optional)
  - top_k: Number of recommendations (default=10, max=50)

Response (200 OK):
{
  "mood": "sad",
  "media_type": "book",
  "recommendations": [
    {
      "id": "google_books_123456",
      "title": "The Fault in Our Stars",
      "author": "John Green",
      "description": "A novel about two teens dealing with cancer...",
      "publish_date": "2012-01-10",
      "average_rating": 4.3,
      "ratings_count": 5423,
      "thumbnail_url": "https://books.google.com/...",
      "preview_url": "https://books.google.com/books?id=...",
      "score": 0.87,
      "reason": "Emotional depth matches reflective mood"
    },
    ...
  ],
  "total_returned": 10
}

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
  503 Service Unavailable: Google Books API down
```

### 5.4 Get Podcast Recommendations

```
GET /api/media/podcasts?mood=neutral&top_k=10
Authorization: Bearer {token}

Query Parameters:
  - mood: Mood label (optional)
  - top_k: Number of recommendations (default=10, max=50)

Response (200 OK):
{
  "mood": "neutral",
  "media_type": "podcast",
  "recommendations": [
    {
      "id": "podcast_api_123456",
      "title": "The Daily",
      "description": "Daily news and analysis...",
      "author": "The New York Times",
      "image": "https://podcast-api.com/...",
      "episodes": 1234,
      "duration_average": 1200,  # seconds
      "rating": 4.5,
      "score": 0.85,
      "reason": "Informative content matches neutral mood"
    },
    ...
  ],
  "total_returned": 10
}

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
  503 Service Unavailable: Podcast API down
```

### 5.5 Log Media Interaction

```
POST /api/interactions
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "media_id": "tmdb_123456",
  "media_type": "movie",
  "signal": "click",  # click|save|skip
  "context": "recommendation",  # recommendation|search
  "timestamp": "2025-01-15T10:30:00Z"
}

Response (201 Created):
{
  "interaction_id": "interaction_uuid",
  "user_id": "...",
  "media_id": "tmdb_123456",
  "media_type": "movie",
  "signal": "click",
  "context": "recommendation",
  "recorded_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  400 Bad Request: Invalid signal or context
  401 Unauthorized: Invalid token
  429 Too Many Requests: Rate limit exceeded
```

---

## ANALYTICS & STATISTICS API

### 6.1 Get Overall Statistics

```
GET /api/stats/overview?period=month&start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer {token}

Query Parameters:
  - period: day|week|month|year (default=month)
  - start_date: Start date (YYYY-MM-DD, optional)
  - end_date: End date (YYYY-MM-DD, optional)

Response (200 OK):
{
  "period": "month",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "statistics": {
    "total_entries": 25,
    "avg_entry_length": 250,
    "entries_per_day": 0.8,
    "total_words": 6250,
    "mood_distribution": {
      "happy": 10,
      "sad": 5,
      "angry": 2,
      "neutral": 8,
      "fear": 0,
      "disgust": 0,
      "surprise": 0
    },
    "most_frequent_mood": "happy",
    "avg_mood_confidence": 0.78,
    "writing_patterns": {
      "peak_hours": [20, 21, 22],
      "peak_day": "Saturday",
      "avg_entry_time": "20:30"
    },
    "mood_trend": {
      "trend_direction": "improving",
      "trend_slope": 0.05,
      "trend_r_squared": 0.72
    },
    "current_streak": 5
  }
}

Error Responses:
  400 Bad Request: Invalid date range
  401 Unauthorized: Invalid token
```

### 6.2 Get Mood Distribution

```
GET /api/stats/mood-distribution?period=month&granularity=daily
Authorization: Bearer {token}

Query Parameters:
  - period: month|quarter|year
  - granularity: daily|weekly|monthly
  - start_date: Start date (optional)
  - end_date: End date (optional)

Response (200 OK):
{
  "period": "month",
  "granularity": "daily",
  "distribution": [
    {
      "date": "2025-01-01",
      "mood_counts": {
        "happy": 1,
        "sad": 0,
        "angry": 0,
        "neutral": 1,
        "fear": 0,
        "disgust": 0,
        "surprise": 0
      },
      "total_entries": 2,
      "primary_mood": "happy"
    },
    ...
  ]
}

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
```

### 6.3 Get Writing Patterns

```
GET /api/stats/writing-patterns?days=30
Authorization: Bearer {token}

Query Parameters:
  - days: Number of days to analyze (default=30, max=365)

Response (200 OK):
{
  "period_days": 30,
  "patterns": {
    "hourly": {
      "peak_hours": [20, 21, 22],
      "entries_by_hour": {
        "0": 0, "1": 0, ..., "20": 5, "21": 6, "22": 4, "23": 1
      },
      "most_active_hour": 21
    },
    "daily": {
      "entries_by_day": {
        "Monday": 3, "Tuesday": 4, "Wednesday": 2, ..., "Sunday": 5
      },
      "most_active_day": "Saturday"
    },
    "frequency": {
      "entries_per_day": 0.8,
      "days_with_entries": 24,
      "days_without_entries": 6
    },
    "timing": {
      "avg_entry_time": "20:30",
      "earliest_entry": "06:15",
      "latest_entry": "23:45"
    }
  }
}

Error Responses:
  401 Unauthorized: Invalid token
  400 Bad Request: Invalid days parameter
```

### 6.4 Get Mood Trends

```
GET /api/stats/mood-trends?period=90
Authorization: Bearer {token}

Query Parameters:
  - period: 7|30|90|365 (days, default=30)

Response (200 OK):
{
  "period_days": 90,
  "metrics": {
    "trend": {
      "direction": "improving",  # improving|declining|stable
      "slope": 0.05,  # mood score change per day
      "r_squared": 0.72,  # statistical significance
      "confidence": "high"  # high|medium|low
    },
    "mood_progression": [
      {
        "date": "2024-12-17",
        "avg_mood_score": 0.65,
        "primary_mood": "neutral"
      },
      ...
    ],
    "anomalies": [
      {
        "date": "2024-12-25",
        "mood_score": 0.95,
        "type": "positive_spike",
        "reason": "Christmas day"
      }
    ]
  }
}

Error Responses:
  401 Unauthorized: Invalid token
  400 Bad Request: Invalid period
```

---

## DATA EXPORT API

### 7.1 Export as CSV

```
POST /api/export/csv
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "include_analysis": true
}

Response (200 OK):
Content-Type: text/csv
Content-Disposition: attachment; filename="pocket-journal-export-2025-01-15.csv"

date,title,mood,confidence,content,summary,tags
2025-01-01,My Day,happy,0.85,"Entry text...","Summary...",tag1;tag2
...

Error Responses:
  400 Bad Request: Invalid date range
  401 Unauthorized: Invalid token
```

### 7.2 Export as JSON

```
POST /api/export/json
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "include_analysis": true
}

Response (200 OK):
Content-Type: application/json
Content-Disposition: attachment; filename="pocket-journal-export-2025-01-15.json"

{
  "export_metadata": {
    "exported_at": "2025-01-15T10:30:00Z",
    "version": "1.0",
    "entry_count": 25
  },
  "entries": [
    {
      "entry_id": "...",
      "title": "...",
      "content": "...",
      "tags": [...],
      "created_at": "...",
      "analysis": {
        "mood": {...},
        "summary": "..."
      }
    },
    ...
  ]
}

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
```

### 7.3 Export as PDF

```
POST /api/export/pdf
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "include_analytics": true
}

Response (200 OK):
Content-Type: application/pdf
Content-Disposition: attachment; filename="pocket-journal-export-2025-01-15.pdf"

[PDF Binary Content]

Included Sections:
  - Cover page (user name, export date, date range)
  - Table of contents
  - Entries (formatted with dates, moods, summaries)
  - Analytics section (if requested)
    * Mood distribution charts
    * Trends analysis
    * Writing patterns
  - Notes page (blank for user)

Error Responses:
  400 Bad Request: Invalid parameters
  401 Unauthorized: Invalid token
  503 Service Unavailable: PDF generation failed
```

---

## USER PROFILE API

### 8.1 Get User Profile

```
GET /api/users/profile
Authorization: Bearer {token}

Response (200 OK):
{
  "uid": "firebase_uid",
  "email": "user@example.com",
  "display_name": "John Doe",
  "preferences": {
    "theme": "dark",
    "notifications": true,
    "language": "en"
  },
  "stats": {
    "total_entries": 125,
    "total_insights": 4,
    "account_age_days": 180,
    "last_entry_date": "2025-01-15"
  },
  "created_at": "2024-07-18T10:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}

Error Responses:
  401 Unauthorized: Invalid token
  404 Not Found: User not found
```

### 8.2 Update User Profile

```
PUT /api/users/profile
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "display_name": "Jane Doe",
  "preferences": {
    "theme": "light",
    "notifications": false,
    "language": "es"
  }
}

Response (200 OK):
{
  "uid": "firebase_uid",
  "email": "user@example.com",
  "display_name": "Jane Doe",
  "preferences": {...},
  "updated_at": "2025-01-15T11:00:00Z"
}

Error Responses:
  400 Bad Request: Invalid input
  401 Unauthorized: Invalid token
```

---

## SYSTEM HEALTH API

### 9.1 Health Check

```
GET /api/health
No authentication required

Response (200 OK):
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": {
      "status": "ok",
      "response_time_ms": 45
    },
    "models": {
      "status": "ok",
      "mood_detection": "loaded",
      "summarization": "loaded",
      "insights": "loaded"
    },
    "external_apis": {
      "firebase": "ok",
      "tmdb": "ok",
      "spotify": "ok",
      "gemini": "ok"
    }
  },
  "uptime_seconds": 86400
}

Error Responses:
  503 Service Unavailable: Service degraded or down
```

### 9.2 Background Jobs Status

```
GET /api/jobs/{job_id}
Authorization: Bearer {token}

Response (200 OK):
{
  "job_id": "job_uuid",
  "status": "in_progress",  # queued|in_progress|completed|failed
  "progress": 65,  # percentage
  "steps": [
    {"name": "Fetching entries", "status": "completed"},
    {"name": "Analyzing moods", "status": "in_progress"},
    {"name": "Generating insights", "status": "queued"}
  ],
  "estimatedCompletion": "2025-01-15T10:35:00Z",
  "result": null  # Populated when completed
}

Error Responses:
  404 Not Found: Job not found
  401 Unauthorized: Invalid token
```

---

## ERROR CODES

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| **200** | OK | Request successful |
| **201** | Created | Resource created |
| **204** | No Content | Deletion successful |
| **400** | Bad Request | Invalid input, validation failed |
| **401** | Unauthorized | Invalid or missing token |
| **403** | Forbidden | Access denied, not owner |
| **404** | Not Found | Resource not found |
| **409** | Conflict | Duplicate resource |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server error |
| **503** | Service Unavailable | Service down, models not loaded |
| **504** | Gateway Timeout | LLM inference timeout |

### Error Response Format

All error responses follow this format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "details": {
    "field": "Form field that failed validation (if applicable)",
    "value": "The invalid value provided"
  },
  "timestamp": "2025-01-15T10:30:00Z",
  "request_id": "unique-request-identifier"
}
```

### Common Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| VALIDATION_ERROR | 400 | Input validation failed |
| UNAUTHORIZED | 401 | Invalid or missing authentication |
| PERMISSION_DENIED | 403 | User lacks permission |
| NOT_FOUND | 404 | Resource not found |
| DUPLICATE_ENTRY | 409 | Resource already exists |
| DATABASE_ERROR | 500 | Database operation failed |
| MODEL_ERROR | 503 | ML model not available |
| TIMEOUT | 504 | Operation timed out |

---

**END OF API SPECIFICATION**

