# Pocket Journal API Reference

## Introduction

This document describes all API endpoints available in the Pocket Journal backend. The API is designed for frontend developers and third-party integrations.

### Base URL
```
https://api.pocketjournal.app
```

All endpoints are prefixed with `/api/v1` unless otherwise noted.

### Authentication

Most endpoints require authentication via Bearer token. Include the token in the `Authorization` header:
```
Authorization: Bearer <id_token>
```

Tokens are obtained from the `/api/v1/auth/login` endpoint. Tokens expire typically within 1 hour; use the refresh token to obtain a new one.

### Common Error Response

All error responses follow this shape:
```json
{
  "error": "error_code",
  "details": "Optional detailed message"
}
```

### Date/Time Format

- **Timestamps**: ISO 8601 with UTC timezone, e.g., `2024-05-25T14:30:45Z`
- **Dates**: YYYY-MM-DD format when specified in query parameters
- **Server times**: Firestore server timestamps used internally; returned as ISO 8601 strings

---

## Authentication

### POST /api/v1/auth/create-user

Creates a new user account in Firebase Auth and initializes the user profile.

**Authentication required:** No

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |
| password | string | Yes | Password (minimum 6 characters recommended) |
| name | string | Yes | User's display name |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | Unique user ID assigned by Firebase |
| email | string | Yes | User's email |
| name | string | Yes | User's display name |
| message | string | Yes | Confirmation message |

**Example response:**
```json
{
  "uid": "user123abc",
  "email": "user@example.com",
  "name": "Alice",
  "message": "user_created"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing required fields (email, password, name) |
| 500 | Firebase authentication or database creation failed |

---

### POST /api/v1/auth/login

Authenticates a user and returns access and refresh tokens.

**Authentication required:** No

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | User's email address |
| password | string | Yes | User's password |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| id_token | string | Yes | JWT access token; use in Authorization header |
| refresh_token | string | Yes | Token to refresh expired id_token |
| expires_in | string | Yes | Seconds until id_token expires (typically 3600) |

**Example response:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "AEwA6CXgB1234567890...",
  "expires_in": "3600"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing email or password |
| 401 | Invalid credentials |
| 500 | Firebase API error |

---

### POST /api/v1/auth/logout

Revokes all refresh tokens for the authenticated user, invalidating all sessions.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| message | string | Yes | Confirmation message |

**Example response:**
```json
{
  "message": "logout_successful"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Firebase revocation failed |

---

### POST /api/v1/auth/change-password

Changes the authenticated user's password after verifying the current password.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| current_password | string | Yes | User's current password |
| new_password | string | Yes | New password to set |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| message | string | Yes | Confirmation message |

**Example response:**
```json
{
  "message": "password_changed"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing required fields |
| 401 | Current password is incorrect or user not authenticated |
| 500 | Firebase operation failed |

---

## Journal

### POST /api/v1/journal

Creates a new journal entry with optional title. The entry text is analyzed for mood and summarized.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| entry_text | string | Yes | The journal entry text (up to 10,000 characters recommended) |
| title | string | No | Optional title for the entry |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| entry_id | string | Yes | Unique identifier for the entry |
| mood | object | Yes | Mood probabilities as a dict mapping mood labels to confidence scores (0.0-1.0) |
| summary | string | Yes | AI-generated summary of the entry |
| created_at | string | Yes | ISO 8601 timestamp of creation |

**Example response:**
```json
{
  "entry_id": "entry_abc123",
  "mood": {
    "happy": 0.45,
    "neutral": 0.35,
    "sad": 0.15,
    "anger": 0.03,
    "fear": 0.02,
    "disgust": 0.0,
    "surprise": 0.0
  },
  "summary": "A good day with positive moments.",
  "created_at": "2024-05-25T14:30:45Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing entry_text field |
| 401 | User not authenticated |
| 500 | Analysis or database insertion failed |

---

### GET /api/v1/journal

Lists the authenticated user's journal entries with optional filtering.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | No | Filter entries created on or after this date (YYYY-MM-DD) |
| end_date | string | No | Filter entries created on or before this date (YYYY-MM-DD) |
| mood | string | No | Filter by mood label (e.g., "happy", "sad") |
| search | string | No | Search entries by text match |
| limit | integer | No | Number of entries to return (default: 50, max: 1000) |
| offset | integer | No | Pagination offset (default: 0) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| entries | array | Yes | List of journal entries |
| entries[].entry_id | string | Yes | Entry identifier |
| entries[].title | string | No — when entry has no title | Entry title |
| entries[].entry_text | string | Yes | Full entry text |
| entries[].mood | object | Yes | Mood probabilities (if mood tracking enabled) |
| entries[].summary | string | Yes | Entry summary |
| entries[].created_at | string | Yes | ISO 8601 creation timestamp |
| count | integer | Yes | Number of entries returned |
| total_count | integer | Yes | Total entries matching filters |

**Example response:**
```json
{
  "entries": [
    {
      "entry_id": "entry_abc123",
      "title": "Great Day",
      "entry_text": "Today was fantastic...",
      "mood": {
        "happy": 0.7,
        "neutral": 0.2,
        "sad": 0.1,
        "anger": 0.0,
        "fear": 0.0,
        "disgust": 0.0,
        "surprise": 0.0
      },
      "summary": "A great day full of positive events.",
      "created_at": "2024-05-25T09:15:00Z"
    }
  ],
  "count": 1,
  "total_count": 42
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Database query failed |

---

### GET /api/v1/journal/search

Searches journal entries by text query with optional date range filtering.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Search string to match against entry text |
| start_date | string | No | Filter entries from this date (YYYY-MM-DD) |
| end_date | string | No | Filter entries until this date (YYYY-MM-DD) |
| limit | integer | No | Number of results to return (default: 20, max: 50) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Matching journal entries |
| results[].entry_id | string | Yes | Entry identifier |
| results[].title | string | No — when entry has no title | Entry title |
| results[].entry_text | string | Yes | Full entry text |
| results[].summary | string | Yes | Entry summary |
| results[].created_at | string | Yes | Creation timestamp |
| count | integer | Yes | Number of results returned |
| total_count | integer | Yes | Total matching results (before limit) |
| filters | object | Yes | Applied filters |
| filters.query | string | Yes | Search query used |
| filters.start_date | string | No — when not provided | Start date filter |
| filters.end_date | string | No — when not provided | End date filter |

**Example response:**
```json
{
  "results": [
    {
      "entry_id": "entry_xyz789",
      "title": "Reflections",
      "entry_text": "Thinking about the future...",
      "summary": "Contemplative entry about future plans.",
      "created_at": "2024-05-20T18:45:00Z"
    }
  ],
  "count": 1,
  "total_count": 1,
  "filters": {
    "query": "future",
    "start_date": "2024-05-01",
    "end_date": "2024-05-31",
    "limit": 20
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid limit value (must be 1-50) or invalid date format |
| 401 | User not authenticated |
| 500 | Search operation failed |

---

### GET /api/v1/journal/{id}

Retrieves a single journal entry by ID.

**Authentication required:** Yes

**Request:** None (ID in path)

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| entry_id | string | Yes | Entry identifier |
| title | string | No — when entry has no title | Entry title |
| entry_text | string | Yes | Full entry text |
| mood | object | Yes | Mood probabilities (if available) |
| summary | string | Yes | Entry summary |
| created_at | string | Yes | Creation timestamp |

**Example response:**
```json
{
  "entry_id": "entry_abc123",
  "title": "Great Day",
  "entry_text": "Today was fantastic because...",
  "mood": {
    "happy": 0.7,
    "neutral": 0.2,
    "sad": 0.1,
    "anger": 0.0,
    "fear": 0.0,
    "disgust": 0.0,
    "surprise": 0.0
  },
  "summary": "A great day full of positive events.",
  "created_at": "2024-05-25T09:15:00Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | Entry not found or user not authorized |
| 500 | Database query failed |

---

### PUT /api/v1/journal/{id}

Updates an existing journal entry's content and title.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| entry_text | string | No | New entry text |
| title | string | No | New title |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| entry_id | string | Yes | Entry identifier |
| message | string | Yes | Confirmation message |

**Example response:**
```json
{
  "entry_id": "entry_abc123",
  "message": "entry_updated"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Both entry_text and title are missing |
| 401 | User not authenticated |
| 404 | Entry not found or user not authorized |
| 500 | Update operation failed |

---

### DELETE /api/v1/journal/{id}

Deletes a journal entry permanently.

**Authentication required:** Yes

**Request:** None (ID in path)

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| message | string | Yes | Confirmation message |
| entry_id | string | Yes | ID of deleted entry |

**Example response:**
```json
{
  "message": "entry_deleted",
  "entry_id": "entry_abc123"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | Entry not found or user not authorized |
| 500 | Deletion failed |

---

### GET /api/v1/journal/all

Retrieves all journal entries for the user in reverse chronological order (no filtering).

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| entries | array | Yes | All user journal entries sorted newest first |
| entries[].entry_id | string | Yes | Entry identifier |
| entries[].title | string | No — when entry has no title | Entry title |
| entries[].entry_text | string | Yes | Full entry text |
| entries[].summary | string | Yes | Entry summary |
| entries[].created_at | string | Yes | Creation timestamp |
| count | integer | Yes | Total entries returned |

**Example response:**
```json
{
  "entries": [
    {
      "entry_id": "entry_xyz789",
      "title": "Recent Entry",
      "entry_text": "Latest thoughts...",
      "summary": "Today's reflection.",
      "created_at": "2024-05-25T18:00:00Z"
    }
  ],
  "count": 42
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Query failed |

---

## Dashboard

### GET /api/v1/dashboard

Home screen endpoint returning greeting, summary stats, motivation line, and recent activity.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| greeting | string | Yes | Personalized greeting with user's name and time of day |
| summary | object | Yes | Summary statistics object |
| summary.current_streak | integer | Yes | Current consecutive journaling days |
| summary.longest_streak | integer | Yes | Longest consecutive journaling streak |
| summary.total_entries | integer | Yes | Total journal entries written |
| summary.words_written | integer | Yes | Total words across all entries |
| motivation_line | string | Yes | Motivational message based on user progress |
| quick_activity | array | Yes | Recent mixed activity (journals and media) |
| quick_activity[].id | string | Yes | Item identifier |
| quick_activity[].type | string | Yes | Type: "journal", "song", "movie", "book", "podcast" |
| quick_activity[].title | string | Yes | Item title or description |
| quick_activity[].created_at | string | No — null for placeholder items | ISO 8601 timestamp |
| insight_preview | object | No — only present when user has insights | Latest insight preview |
| insight_preview.appreciation | string | Yes (if present) | Appreciation message from latest insight |
| insight_preview.goals | array | Yes (if present) | Array of goal strings |

**Example response:**
```json
{
  "greeting": "Good morning, Alice",
  "summary": {
    "current_streak": 12,
    "longest_streak": 25,
    "total_entries": 89,
    "words_written": 15420
  },
  "motivation_line": "Your consistency is powerful. Keep it going.",
  "quick_activity": [
    {
      "id": "entry_abc123",
      "type": "journal",
      "title": "Great Day",
      "created_at": "2024-05-25T14:30:45Z"
    },
    {
      "id": "song_xyz789",
      "type": "song",
      "title": "Saved song",
      "created_at": "2024-05-24T19:15:00Z"
    }
  ]
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Dashboard generation failed |

---

### GET /api/v1/journey

Journey screen endpoint returning AI insights, goals, mood trends, and behavioral patterns for a time period.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| period | string | No | Time period: "7d" or "30d" (default: "7d") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| period | string | Yes | Period analyzed (e.g., "7d") |
| ai_insight | string | Yes | AI-generated insight; fallback motivational message when no entries |
| stats | object | Yes | Statistics object |
| stats.top_mood | string | No — null when no entries | Most common mood in period |
| stats.entries | integer | Yes | Number of entries in period |
| stats.streak | integer | Yes | Consecutive days with entries in period |
| goal_progress | array | Yes | Array of goal progress objects |
| goal_progress[].goal | string | Yes | Goal text |
| goal_progress[].progress | integer | Yes | Percentage completion (0-100) |
| behavioral_pattern | string | Yes | Natural language pattern description; fallback when no entries |
| suggested_actions | array | Yes | Array of suggested action objects |
| suggested_actions[].title | string | Yes | Action title |
| suggested_actions[].subtitle | string | Yes | Action description |
| mood_trend | array | Yes | Daily dominant mood trend (empty when no entries) |
| mood_trend[].date | string | Yes | Date in YYYY-MM-DD format |
| mood_trend[].mood | string | Yes | Dominant mood for that date |
| mood_distribution | object | Yes | Flat dict mapping mood labels to count of occurrences |

**Example response:**
```json
{
  "period": "7d",
  "ai_insight": "You're developing resilience through consistent reflection.",
  "stats": {
    "top_mood": "happy",
    "entries": 6,
    "streak": 6
  },
  "goal_progress": [
    {
      "goal": "Sleep 8 hours daily",
      "progress": 75
    }
  ],
  "behavioral_pattern": "You respond to stress by engaging in creative activities.",
  "suggested_actions": [
    {
      "title": "Write today",
      "subtitle": "Capture your thoughts before they fade."
    }
  ],
  "mood_trend": [
    {
      "date": "2024-05-25",
      "mood": "happy"
    },
    {
      "date": "2024-05-24",
      "mood": "neutral"
    }
  ],
  "mood_distribution": {
    "happy": 4,
    "neutral": 2,
    "sad": 0,
    "anger": 0,
    "fear": 0,
    "disgust": 0,
    "surprise": 0
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Journey generation failed |

---

### GET /api/v1/activity

Recent activity endpoint returning latest merged activity from journals and media interactions.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Maximum items to return (default: 10, max: 50) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| [].id | string | Yes | Item identifier |
| [].type | string | Yes | Type: "journal", "song", "movie", "book", "podcast" |
| [].title | string | Yes | Item title |
| [].created_at | string | Yes | ISO 8601 timestamp |

**Example response:**
```json
[
  {
    "id": "entry_abc123",
    "type": "journal",
    "title": "Reflections",
    "created_at": "2024-05-25T14:30:45Z"
  },
  {
    "id": "song_xyz789",
    "type": "song",
    "title": "Saved song",
    "created_at": "2024-05-24T19:15:00Z"
  }
]
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Activity retrieval failed |

---

## Insights

### POST /api/v1/insights/generate

Generates new insights from journal entries in the specified date range. If no date range is provided, analyzes all entries.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | No | Start date for analysis (YYYY-MM-DD); omit to analyze all entries |
| end_date | string | No | End date for analysis (YYYY-MM-DD); omit to analyze all entries |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| goals | array | Yes | Array of extracted goals |
| progress | string | Yes | Progress description |
| negative_behaviors | array | Yes | Array of identified behaviors to work on |
| remedies | array | Yes | Array of suggested remedies |
| appreciation | string | Yes | Appreciation message noting user strengths |
| conflicts | array | Yes | Array of identified internal conflicts |

**Example response:**
```json
{
  "goals": [
    "Sleep 8 hours daily",
    "Exercise 30 minutes daily"
  ],
  "progress": "You're making steady progress on your goals.",
  "negative_behaviors": [
    "Procrastination when overwhelmed"
  ],
  "remedies": [
    "Break tasks into smaller steps",
    "Take short breaks between activities"
  ],
  "appreciation": "You show remarkable self-awareness.",
  "conflicts": [
    "Wanting rest vs. pressure to be productive"
  ]
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid date format |
| 401 | User not authenticated |
| 500 | AI generation failed |

---

### GET /api/v1/insights

Lists all insights for the authenticated user.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Number of insights to return (default: 50) |
| offset | integer | No | Pagination offset (default: 0) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| insights | array | Yes | Array of insight objects |
| insights[].insight_id | string | Yes | Unique insight identifier |
| insights[].goals | array | Yes | Goal strings |
| insights[].progress | string | Yes | Progress message |
| insights[].negative_behaviors | array | Yes | Behaviors array |
| insights[].remedies | array | Yes | Remedies array |
| insights[].appreciation | string | Yes | Appreciation message |
| insights[].conflicts | array | Yes | Conflicts array |
| insights[].created_at | string | Yes | ISO 8601 creation timestamp |
| count | integer | Yes | Number of insights returned |
| limit | integer | Yes | Limit used |
| offset | integer | Yes | Offset used |

**Example response:**
```json
{
  "insights": [
    {
      "insight_id": "insight_abc123",
      "goals": ["Sleep 8 hours daily"],
      "progress": "Steady progress.",
      "negative_behaviors": ["Procrastination"],
      "remedies": ["Break tasks into steps"],
      "appreciation": "You show self-awareness.",
      "conflicts": ["Rest vs. productivity"],
      "created_at": "2024-05-20T10:00:00Z"
    }
  ],
  "count": 1,
  "limit": 50,
  "offset": 0
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid limit or offset parameter |
| 401 | User not authenticated |
| 500 | Query failed |

---

### GET /api/v1/insights/{id}

Retrieves a single insight by ID.

**Authentication required:** Yes

**Request:** None (ID in path)

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| insight_id | string | Yes | Insight identifier |
| goals | array | Yes | Goal strings |
| progress | string | Yes | Progress message |
| negative_behaviors | array | Yes | Behaviors array |
| remedies | array | Yes | Remedies array |
| appreciation | string | Yes | Appreciation message |
| conflicts | array | Yes | Conflicts array |
| created_at | string | Yes | Creation timestamp |

**Example response:**
```json
{
  "insight_id": "insight_abc123",
  "goals": ["Sleep 8 hours daily"],
  "progress": "Steady progress.",
  "negative_behaviors": ["Procrastination"],
  "remedies": ["Break tasks into steps"],
  "appreciation": "You show self-awareness.",
  "conflicts": ["Rest vs. productivity"],
  "created_at": "2024-05-20T10:00:00Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 403 | Insight does not belong to user |
| 404 | Insight not found |
| 500 | Query failed |

---

### GET /api/v1/insights/date-range

Retrieves insights generated within a specific date range.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | Yes | Start date (YYYY-MM-DD) |
| end_date | string | Yes | End date (YYYY-MM-DD) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| insights | array | Yes | Insights created in the date range |
| insights[].insight_id | string | Yes | Insight identifier |
| insights[].goals | array | Yes | Goal strings |
| insights[].appreciation | string | Yes | Appreciation message |
| count | integer | Yes | Number of insights returned |

**Example response:**
```json
{
  "insights": [
    {
      "insight_id": "insight_abc123",
      "goals": ["Sleep 8 hours daily"],
      "appreciation": "You show self-awareness.",
      "created_at": "2024-05-20T10:00:00Z"
    }
  ],
  "count": 1
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing or invalid start_date/end_date |
| 401 | User not authenticated |
| 500 | Query failed |

---

### DELETE /api/v1/insights/{id}

Deletes an insight permanently.

**Authentication required:** Yes

**Request:** None (ID in path)

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| message | string | Yes | Confirmation message |
| insight_id | string | Yes | ID of deleted insight |
| mappings_deleted | integer | Yes | Number of related entry mappings deleted |

**Example response:**
```json
{
  "message": "Insight deleted successfully",
  "insight_id": "insight_abc123",
  "mappings_deleted": 0
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 403 | Insight does not belong to user |
| 404 | Insight not found |
| 500 | Deletion failed |

---

## Media — Movies

### GET /api/v1/movies/recommend

Retrieves personalized movie recommendations based on mood, genre, and user preferences.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Number of results (default: 20, max: 100) |
| offset | integer | No | Pagination offset (default: 0) |
| genre | string | No | Filter by genre (e.g., "Action", "Comedy") |
| mood | string | No | Filter by mood (e.g., "happy", "sad") |
| search | string | No | Search by title or keywords |
| sort | string | No | Sort order: "default", "popularity", "rating" (default: "default") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Array of movie objects |
| results[].id | string | Yes | Movie identifier |
| results[].title | string | Yes | Movie title |
| results[].description | string | Yes | Plot summary |
| results[].type | string | Yes | Always "movies" |
| results[].image_url | string | No — null if unavailable | URL to poster image |
| results[].release_date | string | No — null if unavailable | Release date or year |
| results[].rating | number | No — null if unavailable | IMDb or aggregated rating (0-10) |
| results[].duration | integer | No — null if unavailable | Duration in minutes |
| results[].genres | array | Yes | Array of genre strings |
| results[].contributors | array | Yes | Array of cast/crew names |
| results[].creator | string | No — null if unavailable | Director name |
| results[].external_url | string | No — null if unavailable | Link to external database |
| results[].language | string | Yes | Primary language |
| results[].popularity | number | No — null if unavailable | Popularity score |
| results[].added_at | string | No — null if unavailable | When added to cache |
| metrics | object | Yes | Response metadata |
| metrics.media_type | string | Yes | "movies" |
| metrics.total | integer | Yes | Total results matching filters |
| metrics.returned | integer | Yes | Number of results in this response |
| metrics.offset | integer | Yes | Offset used |
| metrics.limit | integer | Yes | Limit used |
| metrics.filters | object | Yes | Applied filters |

**Example response:**
```json
{
  "results": [
    {
      "id": "tt0111161",
      "title": "The Shawshank Redemption",
      "description": "Two imprisoned men bond over a number of years...",
      "type": "movies",
      "image_url": "https://images.example.com/poster.jpg",
      "release_date": "1994",
      "rating": 9.3,
      "duration": 142,
      "genres": ["Drama"],
      "contributors": ["Tim Robbins", "Morgan Freeman"],
      "creator": "Frank Darabont",
      "external_url": "https://imdb.com/title/tt0111161",
      "language": "english",
      "popularity": 98.5,
      "added_at": "2024-05-01T10:00:00Z"
    }
  ],
  "metrics": {
    "media_type": "movies",
    "total": 1245,
    "returned": 20,
    "offset": 0,
    "limit": 20,
    "filters": {
      "genre": "Drama",
      "search": null,
      "mood": "happy",
      "sort": "default"
    }
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Recommendation pipeline failed |

---

## Media — Songs

### GET /api/v1/songs/recommend

Retrieves personalized music recommendations based on mood, genre, language, and preferences.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Number of results (default: 20, max: 100) |
| offset | integer | No | Pagination offset (default: 0) |
| genre | string | No | Filter by genre (e.g., "Pop", "Rock", "Jazz") |
| mood | string | No | Filter by mood (e.g., "happy", "sad") |
| search | string | No | Search by artist or song name |
| language | string | No | Filter by language (e.g., "english", "hindi", "neutral") |
| sort | string | No | Sort order: "default", "popularity", "rating" (default: "default") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Array of song objects |
| results[].id | string | Yes | Song/track identifier |
| results[].title | string | Yes | Song or album title |
| results[].description | string | Yes | Song description or bio |
| results[].type | string | Yes | Always "songs" |
| results[].image_url | string | No — null if unavailable | URL to album art |
| results[].release_date | string | No — null if unavailable | Release date |
| results[].rating | number | No — null if unavailable | User or platform rating (0-10) |
| results[].duration | integer | No — null if unavailable | Duration in seconds |
| results[].genres | array | Yes | Array of genre strings |
| results[].contributors | array | Yes | Array of artist/contributor names |
| results[].creator | string | No — null if unavailable | Primary artist name |
| results[].external_url | string | No — null if unavailable | Link to Spotify or other platform |
| results[].language | string | Yes | Language code |
| results[].popularity | number | No — null if unavailable | Popularity score (0-100) |
| results[].added_at | string | No — null if unavailable | When added to cache |
| metrics | object | Yes | Response metadata |
| metrics.media_type | string | Yes | "songs" |
| metrics.total | integer | Yes | Total results matching filters |
| metrics.returned | integer | Yes | Number of results in this response |
| metrics.offset | integer | Yes | Offset used |
| metrics.limit | integer | Yes | Limit used |
| metrics.filters | object | Yes | Applied filters including language |

**Example response:**
```json
{
  "results": [
    {
      "id": "spotify:track:123abc",
      "title": "Bohemian Rhapsody",
      "description": "Epic rock opera by Queen",
      "type": "songs",
      "image_url": "https://images.example.com/album.jpg",
      "release_date": "1975",
      "rating": 9.1,
      "duration": 355,
      "genres": ["Rock", "Opera"],
      "contributors": ["Queen"],
      "creator": "Freddie Mercury",
      "external_url": "https://spotify.com/track/123abc",
      "language": "english",
      "popularity": 92,
      "added_at": "2024-05-01T10:00:00Z"
    }
  ],
  "metrics": {
    "media_type": "songs",
    "total": 5234,
    "returned": 20,
    "offset": 0,
    "limit": 20,
    "filters": {
      "genre": null,
      "search": null,
      "mood": "happy",
      "language": "english",
      "sort": "default"
    }
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Recommendation pipeline failed |

---

## Media — Books

### GET /api/v1/books/recommend

Retrieves personalized book recommendations based on mood, genre, and preferences.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Number of results (default: 20, max: 100) |
| offset | integer | No | Pagination offset (default: 0) |
| genre | string | No | Filter by genre (e.g., "Fiction", "Mystery", "Science Fiction") |
| mood | string | No | Filter by mood (e.g., "happy", "sad") |
| search | string | No | Search by title or author |
| sort | string | No | Sort order: "default", "popularity", "rating" (default: "default") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Array of book objects |
| results[].id | string | Yes | Book identifier |
| results[].title | string | Yes | Book title |
| results[].description | string | Yes | Book synopsis or description |
| results[].type | string | Yes | Always "books" |
| results[].image_url | string | No — null if unavailable | URL to book cover |
| results[].release_date | string | No — null if unavailable | Publication date or year |
| results[].rating | number | No — null if unavailable | Review rating (0-10) |
| results[].duration | integer | No — null if unavailable | Page count |
| results[].genres | array | Yes | Array of genre strings |
| results[].contributors | array | Yes | Array of author/contributor names |
| results[].creator | string | No — null if unavailable | Primary author name |
| results[].external_url | string | No — null if unavailable | Link to book database |
| results[].language | string | Yes | Language of the book |
| results[].popularity | number | No — null if unavailable | Popularity score |
| results[].added_at | string | No — null if unavailable | When added to cache |
| results[].page_count | integer | No — null if unavailable | Number of pages |
| metrics | object | Yes | Response metadata |
| metrics.media_type | string | Yes | "books" |
| metrics.total | integer | Yes | Total results matching filters |
| metrics.returned | integer | Yes | Number of results in this response |
| metrics.offset | integer | Yes | Offset used |
| metrics.limit | integer | Yes | Limit used |
| metrics.filters | object | Yes | Applied filters |

**Example response:**
```json
{
  "results": [
    {
      "id": "isbn:9780316769174",
      "title": "The Catcher in the Rye",
      "description": "A story about teenage rebellion and alienation...",
      "type": "books",
      "image_url": "https://images.example.com/cover.jpg",
      "release_date": "1951",
      "rating": 7.8,
      "duration": 214,
      "genres": ["Fiction", "Young Adult"],
      "contributors": ["J.D. Salinger"],
      "creator": "J.D. Salinger",
      "external_url": "https://goodreads.com/book/123",
      "language": "english",
      "popularity": 78.3,
      "added_at": "2024-05-01T10:00:00Z",
      "page_count": 277
    }
  ],
  "metrics": {
    "media_type": "books",
    "total": 3421,
    "returned": 20,
    "offset": 0,
    "limit": 20,
    "filters": {
      "genre": "Fiction",
      "search": null,
      "mood": "happy",
      "sort": "default"
    }
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Recommendation pipeline failed |

---

## Media — Podcasts

### GET /api/v1/podcasts/recommend

Retrieves personalized podcast recommendations based on mood, genre, language, and preferences.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Number of results (default: 20, max: 100) |
| offset | integer | No | Pagination offset (default: 0) |
| genre | string | No | Filter by genre (e.g., "True Crime", "Comedy", "True Crime" |
| mood | string | No | Filter by mood (e.g., "happy", "sad") |
| search | string | No | Search by podcast name or host |
| language | string | No | Filter by language (e.g., "english", "hindi") |
| sort | string | No | Sort order: "default", "popularity", "rating" (default: "default") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Array of podcast objects |
| results[].id | string | Yes | Podcast identifier |
| results[].title | string | Yes | Podcast name |
| results[].description | string | Yes | Podcast description or tagline |
| results[].type | string | Yes | Always "podcasts" |
| results[].image_url | string | No — null if unavailable | URL to podcast artwork |
| results[].release_date | string | No — null if unavailable | First episode date |
| results[].rating | number | No — null if unavailable | Average rating (0-10) |
| results[].duration | integer | No — null if unavailable | Average episode duration in seconds |
| results[].genres | array | Yes | Array of category strings |
| results[].contributors | array | Yes | Array of host/contributor names |
| results[].creator | string | No — null if unavailable | Primary host or creator name |
| results[].external_url | string | No — null if unavailable | Link to podcast on Spotify/Apple Podcasts |
| results[].language | string | Yes | Primary language |
| results[].popularity | number | No — null if unavailable | Popularity score |
| results[].added_at | string | No — null if unavailable | When added to cache |
| metrics | object | Yes | Response metadata |
| metrics.media_type | string | Yes | "podcasts" |
| metrics.total | integer | Yes | Total results matching filters |
| metrics.returned | integer | Yes | Number of results in this response |
| metrics.offset | integer | Yes | Offset used |
| metrics.limit | integer | Yes | Limit used |
| metrics.filters | object | Yes | Applied filters including language |

**Example response:**
```json
{
  "results": [
    {
      "id": "spotify:show:123abc",
      "title": "StarTalk",
      "description": "Science and comedy with Neil deGrasse Tyson",
      "type": "podcasts",
      "image_url": "https://images.example.com/artwork.jpg",
      "release_date": "2009",
      "rating": 8.5,
      "duration": 3600,
      "genres": ["Science", "Interview", "Comedy"],
      "contributors": ["Neil deGrasse Tyson"],
      "creator": "Neil deGrasse Tyson",
      "external_url": "https://spotify.com/show/123abc",
      "language": "english",
      "popularity": 85.2,
      "added_at": "2024-05-01T10:00:00Z"
    }
  ],
  "metrics": {
    "media_type": "podcasts",
    "total": 2156,
    "returned": 20,
    "offset": 0,
    "limit": 20,
    "filters": {
      "genre": null,
      "search": null,
      "mood": "happy",
      "language": "english",
      "sort": "default"
    }
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Recommendation pipeline failed |

---

## Media — Interactions

### POST /api/v1/media/interaction

Tracks a user interaction with a media item (click, save, or skip) to personalize future recommendations.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| media_type | string | Yes | One of: "movies", "songs", "books", "podcasts" |
| item_id | string | Yes | ID of the media item from recommendation or search results |
| signal | string | Yes | User interaction type: "click" (view/play), "save" (bookmark/like), "skip" (dismiss/dislike) |
| context | string | No | Where interaction occurred: "recommendation" or "search" (default: "recommendation") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| status | string | Yes | Always "ok" |
| updated | boolean | Yes | Whether taste model was updated (false if rate limited) |
| event_id | string | Yes | Unique event identifier |
| media_type | string | Yes | Media type from request |
| item_id | string | Yes | Item ID from request |
| signal | string | Yes | Signal type from request |
| weight | number | Yes | Weight applied to taste model (signal-dependent: click=0.02, save=0.05, skip=-0.01) |
| context | string | Yes | Context from request |
| reason | string | No — only when rate limited | "rate_limited" if event recorded but not processed |
| event_count | integer | No — only when rate limited | Number of events in last hour |
| limit | integer | No — only when rate limited | Rate limit threshold (typically 10/hour) |

**Example response:**
```json
{
  "status": "ok",
  "updated": true,
  "event_id": "evt_xyz123",
  "media_type": "songs",
  "item_id": "spotify:track:456",
  "signal": "save",
  "weight": 0.05,
  "context": "recommendation"
}
```

**Rate-limited response (still returns 200):**
```json
{
  "status": "ok",
  "updated": false,
  "reason": "rate_limited",
  "event_id": "evt_xyz123",
  "media_type": "songs",
  "item_id": "spotify:track:456",
  "signal": "save",
  "weight": 0.05,
  "context": "recommendation",
  "event_count": 11,
  "limit": 10
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid media_type, signal, context, or missing item_id; item not found in cache |
| 401 | User not authenticated |
| 500 | Service initialization failed or database error |

---

### GET /api/v1/{media_type}/search

Searches media items from cache by query string with optional language filter.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| query | string | Yes | Search string (title, artist, author, etc.) |
| language | string | No | Language filter: "english", "hindi", "neutral" (for songs/podcasts only) |
| limit | integer | No | Results to return (default: 20, max: 50) |

**Path parameter:**

| Field | Type | Valid values | Description |
|-------|------|--------------|-------------|
| media_type | string | "movies", "songs", "books", "podcasts" | Type of media to search |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Array of matching media items |
| results[].id | string | Yes | Item identifier |
| results[].title | string | Yes | Item title |
| results[].description | string | Yes | Description or synopsis |
| results[].type | string | Yes | Media type (matches path parameter) |
| results[].image_url | string | No — null if unavailable | URL to artwork/poster |
| results[].genres | array | Yes | Genre tags |
| results[].contributors | array | Yes | Artists/authors/cast |
| results[].rating | number | No — null if unavailable | Rating score |
| results[].popularity | number | No — null if unavailable | Popularity score |
| metrics | object | Yes | Response metadata |
| metrics.query | string | Yes | Search query used |
| metrics.media_type | string | Yes | Media type searched |
| metrics.limit | integer | Yes | Limit applied |
| metrics.returned | integer | Yes | Total results returned |

**Example response:**
```json
{
  "results": [
    {
      "id": "spotify:track:789",
      "title": "Imagine",
      "description": "Iconic peace anthem by John Lennon",
      "type": "songs",
      "image_url": "https://images.example.com/artwork.jpg",
      "genres": ["Rock", "Classic Rock"],
      "contributors": ["John Lennon"],
      "rating": 9.0,
      "popularity": 96.5
    }
  ],
  "metrics": {
    "query": "imagine",
    "media_type": "songs",
    "limit": 20,
    "returned": 1
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Missing query parameter; invalid media_type (not one of four valid types) |
| 401 | User not authenticated |
| 500 | Search service error |

---

### GET /api/v1/{media_type}/get/{item_id}

Retrieves a single media item by ID from cache.

**Authentication required:** Yes

**Request:** None (IDs in path)

**Path parameters:**

| Field | Type | Valid values | Description |
|-------|------|--------------|-------------|
| media_type | string | "movies", "songs", "books", "podcasts" | Type of media |
| item_id | string | Any string | Item identifier |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| results | array | Yes | Single-item array containing the media object |
| results[].id | string | Yes | Item identifier |
| results[].title | string | Yes | Title |
| results[].description | string | Yes | Description |
| results[].type | string | Yes | Media type |
| results[].image_url | string | No — null if unavailable | Artwork URL |
| results[].release_date | string | No — null if unavailable | Release date |
| results[].rating | number | No — null if unavailable | Rating |
| results[].duration | integer | No — null if unavailable | Duration (minutes or seconds) |
| results[].genres | array | Yes | Genre array |
| results[].contributors | array | Yes | Contributors array |
| results[].language | string | Yes | Language |
| results[].popularity | number | No — null if unavailable | Popularity score |
| metrics | object | Yes | Metadata object |
| metrics.media_type | string | Yes | Media type |
| metrics.item_id | string | Yes | Item ID requested |
| metrics.found | boolean | Yes | Always true on success |

**Example response:**
```json
{
  "results": [
    {
      "id": "tt0111161",
      "title": "The Shawshank Redemption",
      "description": "Two imprisoned men bond...",
      "type": "movies",
      "image_url": "https://images.example.com/poster.jpg",
      "release_date": "1994",
      "rating": 9.3,
      "duration": 142,
      "genres": ["Drama"],
      "contributors": ["Tim Robbins", "Morgan Freeman"],
      "language": "english",
      "popularity": 98.5
    }
  ],
  "metrics": {
    "media_type": "movies",
    "item_id": "tt0111161",
    "found": true
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid media_type or empty item_id |
| 401 | User not authenticated |
| 404 | Item not found in cache |
| 500 | Service error |

---

## User & Account

### GET /api/v1/me

Retrieves complete user profile including preferences, settings, and statistics.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | User ID |
| name | string | Yes | Display name |
| email | string | Yes | Email address |
| createdAt | string | Yes | Account creation timestamp |
| preferences | object | Yes | User media preferences object |
| preferences.preferred_media_types | array | Yes | List of preferred media types |
| preferences.genres | object | Yes | Genres per media type |
| preferences.filters | object | Yes | Additional filters (languages, intensity) |
| settings | object | Yes | User settings object |
| settings.mood_tracking_enabled | boolean | Yes | Whether mood detection is active |
| settings.daily_journal_reminders | boolean | Yes | Whether reminders are enabled |
| notification_settings | object | Yes | Notification configuration |
| stats | object | Yes | User statistics |
| stats.total_entries | integer | Yes | Total journal entries |
| stats.current_streak | integer | Yes | Current journaling streak |
| stats.longest_streak | integer | Yes | Longest journaling streak |

**Example response:**
```json
{
  "uid": "user123abc",
  "name": "Alice",
  "email": "alice@example.com",
  "createdAt": "2024-01-15T10:00:00Z",
  "preferences": {
    "preferred_media_types": ["movies", "songs"],
    "genres": {
      "movies": ["Action", "Drama"],
      "songs": ["Pop", "Rock"]
    },
    "filters": {
      "languages": ["english"],
      "content_intensity": "moderate"
    }
  },
  "settings": {
    "mood_tracking_enabled": true,
    "daily_journal_reminders": true
  },
  "notification_settings": {
    "insights_digest": "weekly"
  },
  "stats": {
    "total_entries": 89,
    "current_streak": 12,
    "longest_streak": 25
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | User profile not found |
| 500 | Profile retrieval failed |

---

### PUT /api/v1/me/profile

Updates user profile information (name and email).

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | No | New display name |
| email | string | No | New email address |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | User ID |
| name | string | Yes | Updated name |
| email | string | Yes | Updated email |

**Example response:**
```json
{
  "uid": "user123abc",
  "name": "Alice Smith",
  "email": "alice.smith@example.com"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid input or email already in use |
| 401 | User not authenticated |
| 500 | Update failed |

---

### GET /api/v1/me/preferences

Retrieves user media preferences.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| preferred_media_types | array | Yes | List of preferred media types |
| genres | object | Yes | Genres dict per media type |
| filters | object | Yes | Filter settings |
| filters.languages | array | Yes | Preferred languages |
| filters.content_intensity | string | Yes | "light", "moderate", or "heavy" |

**Example response:**
```json
{
  "preferred_media_types": ["movies", "songs"],
  "genres": {
    "movies": ["Action", "Drama"],
    "songs": ["Pop", "Rock"]
  },
  "filters": {
    "languages": ["english", "hindi"],
    "content_intensity": "moderate"
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | User not found |
| 500 | Retrieval failed |

---

### PUT /api/v1/me/preferences

Updates user media preferences. Accepts both legacy and new formats.

**Authentication required:** Yes

**Request — Modern format:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| preferred_media_types | array | No | List of media types |
| genres | object | No | Genres per media type |
| filters | object | No | Filter settings |
| filters.languages | array | No | Preferred languages |
| filters.content_intensity | string | No | "light", "moderate", or "heavy" |

**Request — Legacy format (automatically converted):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| music | array | No | Music genres (converted to "songs") |
| movies | array | No | Movie genres |
| books | array | No | Book genres |
| podcasts | array | No | Podcast genres |
| languages | array | No | Preferred languages |
| content_intensity | string | No | Content intensity preference |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | User ID |
| preferences | object | Yes | Updated preferences in normalized format |

**Example response (modern format):**
```json
{
  "uid": "user123abc",
  "preferences": {
    "preferred_media_types": ["movies", "songs"],
    "genres": {
      "movies": ["Action", "Drama"],
      "songs": ["Pop", "Rock"]
    },
    "filters": {
      "languages": ["english"],
      "content_intensity": "moderate"
    }
  }
}
```

**Example response (legacy format input):**
```json
{
  "uid": "user123abc",
  "preferences": {
    "preferred_media_types": ["music", "movies"],
    "genres": {
      "music": ["Pop", "Rock"],
      "movies": ["Action"]
    },
    "filters": {
      "languages": ["english"],
      "content_intensity": "moderate"
    }
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid preference format or values |
| 401 | User not authenticated |
| 500 | Update failed |

---

### GET /api/v1/me/settings

Retrieves user settings.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| mood_tracking_enabled | boolean | Yes | Whether mood detection is active |
| weekly_insights_enabled | boolean | Yes | Whether weekly insights are generated |
| daily_journal_reminders | boolean | Yes | Whether reminders are enabled |

**Example response:**
```json
{
  "mood_tracking_enabled": true,
  "weekly_insights_enabled": true,
  "daily_journal_reminders": false
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | User not found |
| 500 | Retrieval failed |

---

### PUT /api/v1/me/settings

Updates user settings.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| mood_tracking_enabled | boolean | No | Enable/disable mood detection |
| weekly_insights_enabled | boolean | No | Enable/disable weekly insights |
| daily_journal_reminders | boolean | No | Enable/disable daily reminders |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | User ID |
| settings | object | Yes | Updated settings |

**Example response:**
```json
{
  "uid": "user123abc",
  "settings": {
    "mood_tracking_enabled": true,
    "weekly_insights_enabled": true,
    "daily_journal_reminders": false
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid input |
| 401 | User not authenticated |
| 500 | Update failed |

---

### GET /api/v1/me/notifications

Retrieves user notification settings.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| notifications object | object | Varies | Notification preference keys and values |

**Example response:**
```json
{
  "insights_digest": "weekly",
  "suggestions": "daily"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 404 | User not found |
| 500 | Retrieval failed |

---

### PUT /api/v1/me/notifications

Updates user notification settings.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| insights_digest | string | No | "daily", "weekly", "never" |
| suggestions | string | No | "daily", "weekly", "never" |
| (other notification keys) | string | No | Additional notification preferences |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| uid | string | Yes | User ID |
| notification_settings | object | Yes | Updated notification settings |

**Example response:**
```json
{
  "uid": "user123abc",
  "notification_settings": {
    "insights_digest": "weekly",
    "suggestions": "daily"
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid input |
| 401 | User not authenticated |
| 500 | Update failed |

---

## Statistics

### GET /api/v1/stats

Retrieves user statistics (entry counts, moods, activities).

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| total_entries | integer | Yes | Total journal entries |
| total_words | integer | Yes | Total words written |
| current_streak | integer | Yes | Current consecutive journaling days |
| longest_streak | integer | Yes | Longest consecutive streak |
| favorite_mood | string | No — null if no entries | Most common mood |
| entries_this_week | integer | Yes | Entries in last 7 days |
| entries_this_month | integer | Yes | Entries in current month |

**Example response:**
```json
{
  "total_entries": 89,
  "total_words": 15420,
  "current_streak": 12,
  "longest_streak": 25,
  "favorite_mood": "happy",
  "entries_this_week": 6,
  "entries_this_month": 18
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Query failed |

---

### GET /api/v1/mood-trends

Retrieves mood trend data over a specified number of days.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| days | integer | No | Number of past days to analyze (default: 30, max: 365) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| trends | array | Yes | Array of daily mood objects |
| trends[].date | string | Yes | Date in YYYY-MM-DD format |
| trends[].mood | string | Yes | Dominant mood for that day |
| trends[].confidence | number | Yes | Confidence score (0.0-1.0) |
| analysis | object | Yes | Aggregate analysis |
| analysis.period_days | integer | Yes | Days analyzed |
| analysis.top_mood | string | Yes | Most common mood |
| analysis.mood_stability | number | Yes | Metric for mood consistency (0-1) |

**Example response:**
```json
{
  "trends": [
    {
      "date": "2024-05-25",
      "mood": "happy",
      "confidence": 0.68
    },
    {
      "date": "2024-05-24",
      "mood": "neutral",
      "confidence": 0.52
    }
  ],
  "analysis": {
    "period_days": 30,
    "top_mood": "happy",
    "mood_stability": 0.65
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid days parameter |
| 401 | User not authenticated |
| 500 | Query failed |

---

### GET /api/v1/stats/weekly

Retrieves statistics for the last 7 days.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| period | string | Yes | "weekly" |
| start_date | string | Yes | Start date (ISO 8601) |
| end_date | string | Yes | End date (ISO 8601) |
| total_entries | integer | Yes | Entries in this period |
| total_words | integer | Yes | Words written |
| mood_distribution | object | Yes | Count per mood |
| average_entry_length | number | Yes | Average words per entry |

**Example response:**
```json
{
  "period": "weekly",
  "start_date": "2024-05-18T00:00:00Z",
  "end_date": "2024-05-25T23:59:59Z",
  "total_entries": 6,
  "total_words": 2145,
  "mood_distribution": {
    "happy": 3,
    "neutral": 2,
    "sad": 1,
    "anger": 0,
    "fear": 0,
    "disgust": 0,
    "surprise": 0
  },
  "average_entry_length": 357
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Query failed |

---

### GET /api/v1/stats/monthly

Retrieves statistics for the current calendar month.

**Authentication required:** Yes

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| period | string | Yes | "monthly" |
| start_date | string | Yes | First day of month (ISO 8601) |
| end_date | string | Yes | Today's date (ISO 8601) |
| total_entries | integer | Yes | Entries in this month |
| total_words | integer | Yes | Words written |
| mood_distribution | object | Yes | Count per mood |
| average_entry_length | number | Yes | Average words per entry |
| days_with_entries | integer | Yes | Number of days with at least one entry |

**Example response:**
```json
{
  "period": "monthly",
  "start_date": "2024-05-01T00:00:00Z",
  "end_date": "2024-05-25T23:59:59Z",
  "total_entries": 18,
  "total_words": 6234,
  "mood_distribution": {
    "happy": 9,
    "neutral": 6,
    "sad": 3,
    "anger": 0,
    "fear": 0,
    "disgust": 0,
    "surprise": 0
  },
  "average_entry_length": 346,
  "days_with_entries": 18
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 401 | User not authenticated |
| 500 | Query failed |

---

## Export

### POST /api/v1/export

Exports journal entries and insights in JSON or CSV format.

**Authentication required:** Yes

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| start_date | string | No | Export from this date (YYYY-MM-DD); omit for all entries |
| end_date | string | No | Export until this date (YYYY-MM-DD); omit for all entries |
| format | string | No | Export format: "json" or "csv" (default: "json") |

**Response — JSON format:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| user_id | string | Yes | User ID |
| export_timestamp | string | Yes | ISO 8601 export time |
| date_range | object | Yes | Date range applied |
| date_range.start_date | string | Yes | Start date or null |
| date_range.end_date | string | Yes | End date or null |
| entries | array | Yes | Array of journal entries |
| entries[].entry_id | string | Yes | Entry ID |
| entries[].entry_text | string | Yes | Full text |
| entries[].title | string | No — when not set | Entry title |
| entries[].mood | object | Yes | Mood probabilities |
| entries[].created_at | string | Yes | Creation timestamp |
| insights | array | Yes | Array of insights |
| insights[].insight_id | string | Yes | Insight ID |
| insights[].goals | array | Yes | Goals |
| insights[].appreciation | string | Yes | Appreciation message |
| total_entries | integer | Yes | Count of entries exported |
| total_insights | integer | Yes | Count of insights exported |

**Example response — JSON format:**
```json
{
  "user_id": "user123abc",
  "export_timestamp": "2024-05-25T15:30:45Z",
  "date_range": {
    "start_date": "2024-05-01",
    "end_date": "2024-05-31"
  },
  "entries": [
    {
      "entry_id": "entry_abc123",
      "entry_text": "Today was great...",
      "title": "Great Day",
      "mood": {
        "happy": 0.7,
        "neutral": 0.2,
        "sad": 0.1
      },
      "created_at": "2024-05-25T09:15:00Z"
    }
  ],
  "insights": [
    {
      "insight_id": "insight_xyz789",
      "goals": ["Sleep 8 hours"],
      "appreciation": "You show self-awareness."
    }
  ],
  "total_entries": 18,
  "total_insights": 2
}
```

**Response — CSV format:**

Returns a CSV file with `Content-Type: text/csv`. First line is header; each row is an entry with columns: entry_id, date, title, text, mood_happy, mood_sad, etc.

**Example CSV:**
```
entry_id,date,title,text,mood_happy,mood_neutral,mood_sad
entry_abc123,2024-05-25,Great Day,Today was fantastic,0.7,0.2,0.1
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid date format or date range |
| 401 | User not authenticated |
| 500 | Export generation failed |

---

## Jobs

All job endpoints are admin-only and require protection at the infrastructure level (bearer token or IP allowlist) before production deployment. No user authentication is enforced by these endpoints.

### POST /job/v1/cache/refresh

Synchronously refreshes all media cache (movies, songs, books, podcasts).

**Authentication required:** No (protect at infrastructure level)

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| force | string/boolean | No | Force refresh even if not expired (e.g., "true", "1", "yes") |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| status | string | Yes | "completed" or "failed" |
| job | string | Yes | "cache_refresh_all" |
| force | boolean | Yes | Whether force flag was used |
| message | string | Yes | Status message |
| completed_at | string | Yes | ISO 8601 completion time |

**Example response:**
```json
{
  "status": "completed",
  "job": "cache_refresh_all",
  "force": false,
  "message": "Cache refresh completed successfully",
  "completed_at": "2024-05-25T16:45:30Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Cache refresh failed; error details in response |

---

### POST /job/v1/cache/refresh/{media_type}

Synchronously refreshes cache for a single media type.

**Authentication required:** No (protect at infrastructure level)

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| force | string/boolean | No | Force refresh |

**Path parameter:**

| Field | Type | Valid values | Description |
|-------|------|--------------|-------------|
| media_type | string | "movies", "songs", "books", "podcasts" | Media type to refresh |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| status | string | Yes | "completed" or "failed" |
| job | string | Yes | "cache_refresh" |
| media_type | string | Yes | Media type refreshed |
| force | boolean | Yes | Force flag used |
| message | string | Yes | Status message |
| completed_at | string | Yes | Completion timestamp |

**Example response:**
```json
{
  "status": "completed",
  "job": "cache_refresh",
  "media_type": "songs",
  "force": false,
  "message": "Cache refresh for songs completed successfully",
  "completed_at": "2024-05-25T16:45:30Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid media_type |
| 500 | Refresh failed |

---

### GET /job/v1/cache/status

Retrieves cache status for all media types.

**Authentication required:** No (protect at infrastructure level)

**Request:** None

**Response:**

Returns a dict with cache stats for each media type:

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| movies | object | Yes | Cache stats for movies |
| movies.count | integer | Yes | Number of items in cache |
| movies.last_updated | string | Yes | Last refresh timestamp |
| songs | object | Yes | Cache stats for songs |
| books | object | Yes | Cache stats for books |
| podcasts | object | Yes | Cache stats for podcasts |

**Example response:**
```json
{
  "movies": {
    "count": 2150,
    "last_updated": "2024-05-25T12:00:00Z"
  },
  "songs": {
    "count": 5234,
    "last_updated": "2024-05-25T12:15:00Z"
  },
  "books": {
    "count": 3421,
    "last_updated": "2024-05-25T12:30:00Z"
  },
  "podcasts": {
    "count": 2156,
    "last_updated": "2024-05-25T12:45:00Z"
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Cache status retrieval failed |

---

### GET /job/v1/cache/status/{media_type}

Retrieves cache status for a specific media type.

**Authentication required:** No (protect at infrastructure level)

**Request:** None (type in path)

**Path parameter:**

| Field | Type | Valid values | Description |
|-------|------|--------------|-------------|
| media_type | string | "movies", "songs", "books", "podcasts" | Media type |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| count | integer | Yes | Number of items in cache |
| last_updated | string | Yes | Last refresh timestamp |
| status | string | Yes | Cache status (e.g., "active", "stale") |

**Example response:**
```json
{
  "count": 5234,
  "last_updated": "2024-05-25T12:15:00Z",
  "status": "active"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 400 | Invalid media_type |
| 500 | Status retrieval failed |

---

### POST /job/v1/dashboard/cache/generate

Generates AI dashboard cache for eligible users (users with entries and insights).

**Authentication required:** No (protect at infrastructure level)

**Request:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| limit | integer | No | Maximum users to process (default: 500, max: 2000) |

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| status | string | Yes | "completed" or "failed" |
| job | string | Yes | "dashboard_cache_generate" |
| message | string | Yes | Status message |
| limit | integer | Yes | User limit applied |
| processed | integer | Yes | Number of users processed |
| failed | integer | Yes | Number of processing failures |
| completed_at | string | Yes | ISO 8601 completion time |

**Example response:**
```json
{
  "status": "completed",
  "job": "dashboard_cache_generate",
  "message": "Dashboard AI cache generated",
  "limit": 500,
  "processed": 487,
  "failed": 13,
  "completed_at": "2024-05-25T17:00:00Z"
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Cache generation job failed |

---

## System

### GET /api/v1/app/about

Retrieves application information, version, features, and mission.

**Authentication required:** No

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| app_name | string | Yes | "Pocket Journal" |
| version | string | Yes | Semantic version |
| mission | string | Yes | App mission statement |
| features | array | Yes | Array of feature descriptions |
| privacy_highlight | string | Yes | Privacy promise summary |
| contact | object | Yes | Contact information |
| contact.email | string | Yes | Support email |
| contact.website | string | Yes | Website URL |

**Example response:**
```json
{
  "app_name": "Pocket Journal",
  "version": "1.0.0",
  "mission": "Empower users to understand themselves better through AI-powered emotional insights and personalized media recommendations.",
  "features": [
    "AI-powered mood detection from journal entries",
    "Personalized insights and behavioral patterns",
    "Emotion-driven media recommendations"
  ],
  "privacy_highlight": "Your journal entries are encrypted and stored securely.",
  "contact": {
    "email": "support@pocketjournal.app",
    "website": "https://pocketjournal.app"
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Retrieval failed |

---

### GET /api/v1/app/privacy

Retrieves comprehensive privacy policy.

**Authentication required:** No

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| last_updated | string | Yes | Date policy was last updated |
| sections | array | Yes | Array of policy section objects |
| sections[].title | string | Yes | Section title |
| sections[].content | string | Yes | Section content |

**Example response:**
```json
{
  "last_updated": "2024-01-01",
  "sections": [
    {
      "title": "Data Collection",
      "content": "Pocket Journal collects journal entries, mood data, preferences..."
    },
    {
      "title": "Data Security",
      "content": "All journal entries are encrypted using AES-256..."
    }
  ]
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Retrieval failed |

---

### GET /api/v1/app/terms

Retrieves comprehensive terms of service.

**Authentication required:** No

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| last_updated | string | Yes | Date terms were last updated |
| sections | array | Yes | Array of terms section objects |
| sections[].title | string | Yes | Section title |
| sections[].content | string | Yes | Section text |

**Example response:**
```json
{
  "last_updated": "2024-01-01",
  "sections": [
    {
      "title": "Service Description",
      "content": "Pocket Journal is an AI-powered journaling platform..."
    },
    {
      "title": "User Responsibilities",
      "content": "You are responsible for maintaining confidentiality..."
    }
  ]
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 500 | Retrieval failed |

---

### GET /api/v1/health

Health check endpoint returning system status.

**Authentication required:** No

**Request:** None

**Response:**

| Field | Type | Always present | Description |
|-------|------|----------------|-------------|
| status | string | Yes | "healthy" or "degraded" |
| timestamp | string | Yes | ISO 8601 check time |
| services | object | Yes | Service status dict |
| services.database | string | Yes | "ok" or error message |
| services.auth | string | Yes | "ok" or error message |
| services.cache | string | Yes | "ok" or error message |

**Example response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-05-25T16:50:00Z",
  "services": {
    "database": "ok",
    "auth": "ok",
    "cache": "ok"
  }
}
```

**Error responses:**

| Status | Meaning |
|--------|---------|
| 503 | Service unavailable or degraded |

---

## Rate Limits & Quotas

- **Media interactions**: 10 per hour per user per media type (additional events recorded but not processed)
- **Journal entries**: No hard limit; practical limit ~100,000 entries per user
- **Export**: One at a time per user; export operations timeout after 30 seconds

---

## Changelog

### Version 1.0.0
- Initial API release
- Core authentication, journal, dashboard, insights endpoints
- Media recommendations (movies, songs, books, podcasts)
- User profile and preferences management
- Statistics and export functionality
- Admin job endpoints for cache management


