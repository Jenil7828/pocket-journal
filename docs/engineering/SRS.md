# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)
## Pocket Journal — AI-Powered Digital Journaling Platform

**Document Version:** 1.0  
**Last Updated:** April 18, 2026  
**Project Name:** Pocket Journal  
**Domain:** Digital Journaling, AI/ML, Analytics  
**Tech Stack:** Python, Flask, Firebase, RoBERTa, BART, Gemini, Qwen2, Sentence-Transformers

---

## TABLE OF CONTENTS
1. [Executive Summary](#executive-summary)
2. [Functional Requirements](#functional-requirements)
3. [Non-Functional Requirements](#non-functional-requirements)
4. [User Roles & Personas](#user-roles--personas)
5. [Use Cases](#use-cases)
6. [Acceptance Criteria](#acceptance-criteria)

---

## EXECUTIVE SUMMARY

Pocket Journal is a comprehensive AI-powered digital journaling application designed to help users reflect, analyze, and understand their emotional patterns through intelligent natural language processing. The system integrates multiple transformer-based machine learning models to provide mood detection, content summarization, personalized insights, and contextual media recommendations.

### Core Features
- **Mood Detection**: Multi-class emotion classification using RoBERTa
- **Automated Summarization**: Abstractive text summarization using BART
- **AI Insights Generation**: Personalized reflections using Gemini or Qwen2
- **Media Recommendations**: Contextual recommendations for movies, songs, books, podcasts
- **Analytics Dashboard**: Mood patterns, entry frequency, writing patterns
- **Data Export**: CSV, JSON, PDF formats
- **Secure Authentication**: Firebase-backed user management
- **Scalable Architecture**: Docker deployment with GPU support

---

## FUNCTIONAL REQUIREMENTS

### MODULE 1: AUTHENTICATION & USER MANAGEMENT

#### FR1.1 User Registration
| Requirement | Details |
|-------------|---------|
| **ID** | FR1.1 |
| **Title** | User Registration |
| **Description** | Users must register with email, password, and display name |
| **Inputs** | Email, Password, Display Name |
| **Outputs** | Firebase UID, Authentication Token |
| **Module** | `routes/auth.py`, `services/` |
| **Business Logic** | Validate email format, hash password, create Firestore user document |
| **Error Handling** | Duplicate email → HTTP 409; Invalid format → HTTP 400 |

#### FR1.2 User Login
| Requirement | Details |
|-------------|---------|
| **ID** | FR1.2 |
| **Title** | User Login |
| **Description** | Users authenticate with email and password to obtain auth token |
| **Inputs** | Email, Password |
| **Outputs** | JWT Token (Firebase ID Token) |
| **Module** | `routes/auth.py` |
| **Business Logic** | Firebase authentication, token generation |
| **Error Handling** | Invalid credentials → HTTP 401 |

#### FR1.3 Token Verification
| Requirement | Details |
|-------------|---------|
| **ID** | FR1.3 |
| **Title** | Token Verification |
| **Description** | Verify JWT token validity and user permissions |
| **Inputs** | Authorization Header with Bearer Token |
| **Outputs** | User UID, Email (if valid) |
| **Module** | `app.py` (login_required decorator) |
| **Business Logic** | Firebase token verification |
| **Error Handling** | Expired/Invalid → HTTP 401 |

#### FR1.4 User Profile Management
| Requirement | Details |
|-------------|---------|
| **ID** | FR1.4 |
| **Title** | User Profile Management |
| **Description** | Users can view, update profile information and preferences |
| **Inputs** | Display Name, Preferences (theme, notifications, language) |
| **Outputs** | Updated User Document |
| **Module** | `routes/user.py`, `services/` |
| **CRUD** | GET, PUT |

---

### MODULE 2: JOURNAL ENTRIES

#### FR2.1 Create Journal Entry
| Requirement | Details |
|-------------|---------|
| **ID** | FR2.1 |
| **Title** | Create Journal Entry |
| **Description** | Users create new journal entries with title and content |
| **Inputs** | Title, Content, Tags (optional) |
| **Outputs** | Entry ID, Created Timestamp |
| **Module** | `routes/journal_domain.py`, `services/journal_entries/` |
| **Business Logic** | Validate content length (1-5000 chars), store in Firestore |
| **Database** | `journal_entries` collection |
| **Error Handling** | Empty content → HTTP 400; Auth failure → HTTP 401 |

#### FR2.2 Retrieve Journal Entries
| Requirement | Details |
|-------------|---------|
| **ID** | FR2.2 |
| **Title** | Retrieve Journal Entries |
| **Description** | Fetch user's journal entries with pagination |
| **Inputs** | User UID, Limit (default=10, max=100), Offset |
| **Outputs** | Array of Entry Objects, Total Count |
| **Module** | `routes/journal_domain.py`, `services/journal_entries/` |
| **Business Logic** | Paginate from Firestore, order by created_at DESC |
| **Database** | `journal_entries` collection with UID filter |

#### FR2.3 Update Journal Entry
| Requirement | Details |
|-------------|---------|
| **ID** | FR2.3 |
| **Title** | Update Journal Entry |
| **Description** | Users modify existing journal entries |
| **Inputs** | Entry ID, Updated Title/Content/Tags |
| **Outputs** | Updated Entry, Updated Timestamp |
| **Module** | `routes/journal_domain.py`, `services/journal_entries/` |
| **Validation** | Only entry owner can update |
| **Database** | Update `journal_entries` and related analysis docs |

#### FR2.4 Delete Journal Entry
| Requirement | Details |
|-------------|---------|
| **ID** | FR2.4 |
| **Title** | Delete Journal Entry |
| **Description** | Users delete journal entries and related data |
| **Inputs** | Entry ID |
| **Outputs** | Success/Failure Status |
| **Module** | `routes/journal_domain.py`, `services/journal_entries/` |
| **Cascade** | Delete from `entry_analysis`, `insights`, mappings |

#### FR2.5 Search Journal Entries
| Requirement | Details |
|-------------|---------|
| **ID** | FR2.5 |
| **Title** | Search Journal Entries |
| **Description** | Full-text search across user's entries |
| **Inputs** | Query String, User UID |
| **Outputs** | Matching Entries, Relevance Score |
| **Module** | `services/search_service/` |
| **Business Logic** | Fuzzy matching, case-insensitive, typo tolerance |

---

### MODULE 3: MOOD DETECTION & ENTRY ANALYSIS

#### FR3.1 Analyze Entry for Mood
| Requirement | Details |
|-------------|---------|
| **ID** | FR3.1 |
| **Title** | Analyze Entry for Mood |
| **Description** | Detect emotions from journal entry text using RoBERTa |
| **Inputs** | Entry Content (max 5000 chars) |
| **Outputs** | Mood Probabilities (7 classes), Primary Mood, Confidence |
| **Module** | `routes/journal_domain.py`, `ml/inference/mood_detection/roberta/` |
| **ML Model** | RoBERTa-base fine-tuned on emotion classification |
| **Labels** | anger, disgust, fear, happy, neutral, sad, surprise |
| **Threshold** | 0.35 minimum confidence |
| **Performance** | Inference < 500ms per entry |

#### FR3.2 Generate Entry Summary
| Requirement | Details |
|-------------|---------|
| **ID** | FR3.2 |
| **Title** | Generate Entry Summary |
| **Description** | Create abstractive summary of journal entry using BART |
| **Inputs** | Entry Content |
| **Outputs** | Summary (20-128 tokens) |
| **Module** | `ml/inference/summarization/bart/` |
| **ML Model** | BART (facebook/bart-large-cnn) |
| **Config** | Max input=1024, Max summary=128, Min=20 tokens |
| **Fallback** | Character-based truncation if BART fails |
| **Performance** | Inference < 1000ms per entry |

#### FR3.3 Store Entry Analysis
| Requirement | Details |
|-------------|---------|
| **ID** | FR3.3 |
| **Title** | Store Entry Analysis |
| **Description** | Persist mood and summary to database |
| **Inputs** | Entry ID, Mood Data, Summary |
| **Outputs** | Analysis ID, Timestamp |
| **Module** | `services/`, `persistence/db_manager.py` |
| **Database** | `entry_analysis` collection |
| **Schema** | entry_id, summary, mood (7-class dict), created_at |

#### FR3.4 Retrieve Mood History
| Requirement | Details |
|-------------|---------|
| **ID** | FR3.4 |
| **Title** | Retrieve Mood History |
| **Description** | Get user's mood progression over time |
| **Inputs** | User UID, Date Range (optional), Limit |
| **Outputs** | Array of {date, mood, confidence, entry_text, summary} |
| **Module** | `routes/stats.py`, `services/stats_service/` |
| **Database** | Join `journal_entries` + `entry_analysis` |

---

### MODULE 4: INSIGHTS GENERATION

#### FR4.1 Generate AI Insights
| Requirement | Details |
|-------------|---------|
| **ID** | FR4.1 |
| **Title** | Generate AI Insights |
| **Description** | Create personalized insights from entries in date range |
| **Inputs** | User UID, Start Date, End Date |
| **Outputs** | Insight object with goals, progress, patterns, remedies |
| **Module** | `routes/insights_domain.py`, `services/insights_service/` |
| **ML Model** | Gemini-2.0-flash (cloud) OR Qwen2-1.5B (local) |
| **Config** | use_gemini flag in config.yml |
| **Processing** | Aggregate entries, generate prompts, call LLM |
| **Performance** | Response < 30 seconds |

#### FR4.2 Insight Structure
| Requirement | Details |
|-------------|---------|
| **ID** | FR4.2 |
| **Title** | Insight Structure |
| **Description** | Define insight output format |
| **Fields** | goals[], progress, negative_behaviors, remedies, appreciation, conflicts, raw_response |
| **Module** | `persistence/database_schema.py` |
| **Validation** | All required fields present |

#### FR4.3 Retrieve Insights
| Requirement | Details |
|-------------|---------|
| **ID** | FR4.3 |
| **Title** | Retrieve Insights |
| **Description** | Fetch generated insights for user |
| **Inputs** | User UID, Date Range (optional), Limit |
| **Outputs** | Array of Insight Objects |
| **Module** | `routes/insights_domain.py`, `services/insights_service/` |

---

### MODULE 5: MEDIA RECOMMENDATIONS

#### FR5.1 Get Movie Recommendations
| Requirement | Details |
|-------------|---------|
| **ID** | FR5.1 |
| **Title** | Get Movie Recommendations |
| **Description** | Suggest movies based on detected mood or entry content |
| **Inputs** | Mood (optional), User UID, Top K (default=10) |
| **Outputs** | Array of Movie Objects {title, overview, rating, poster_url, ...} |
| **Module** | `routes/media_domain.py`, `services/media_recommender/` |
| **Provider** | TMDb API |
| **Algorithm** | Similarity ranking + popularity weighting |
| **Performance** | Response < 2 seconds |
| **Caching** | Media cache (Firestore), 24-hour TTL |

#### FR5.2 Get Music Recommendations
| Requirement | Details |
|-------------|---------|
| **ID** | FR5.2 |
| **Title** | Get Music Recommendations |
| **Description** | Suggest songs based on mood and user taste |
| **Inputs** | Mood (optional), User UID, Top K (default=10) |
| **Outputs** | Array of Song Objects {title, artist, album, preview_url, ...} |
| **Module** | `routes/media_domain.py`, `services/media_recommender/` |
| **Provider** | Spotify API |
| **Algorithm** | Embedding-based matching + interaction history |
| **Performance** | Response < 2 seconds |

#### FR5.3 Get Book Recommendations
| Requirement | Details |
|-------------|---------|
| **ID** | FR5.3 |
| **Title** | Get Book Recommendations |
| **Description** | Suggest books based on user preferences |
| **Inputs** | Mood (optional), User UID, Top K (default=10) |
| **Outputs** | Array of Book Objects {title, author, description, thumbnail_url, ...} |
| **Module** | `routes/media_domain.py`, `services/media_recommender/` |
| **Provider** | Google Books API |
| **Algorithm** | Similarity-based ranking |

#### FR5.4 Get Podcast Recommendations
| Requirement | Details |
|-------------|---------|
| **ID** | FR5.4 |
| **Title** | Get Podcast Recommendations |
| **Description** | Suggest podcast episodes based on mood and interests |
| **Inputs** | Mood (optional), User UID, Top K (default=10) |
| **Outputs** | Array of Podcast Objects {title, description, audio_url, ...} |
| **Module** | `routes/media_domain.py`, `services/media_recommender/` |
| **Provider** | Podcast API |

#### FR5.5 Track Media Interactions
| Requirement | Details |
|-------------|---------|
| **ID** | FR5.5 |
| **Title** | Track Media Interactions |
| **Description** | Log user click, save, skip actions for recommendations feedback |
| **Inputs** | Media Type, Media ID, Signal (click/save/skip), Context |
| **Outputs** | Interaction ID, Timestamp |
| **Module** | `services/interaction_service/` |
| **Database** | `user_interactions` collection |
| **Signals** | Click=0.02, Save=0.05, Skip=-0.01 weight |

---

### MODULE 6: ANALYTICS & STATISTICS

#### FR6.1 Get User Statistics Overview
| Requirement | Details |
|-------------|---------|
| **ID** | FR6.1 |
| **Title** | Get User Statistics Overview |
| **Description** | Dashboard summary of user's journaling activity |
| **Inputs** | User UID, Period (day/week/month/year) |
| **Outputs** | {total_entries, avg_entry_length, mood_distribution, streak_days, ...} |
| **Module** | `routes/stats.py`, `services/stats_service/` |
| **Calculations** | Aggregations on entry and analysis collections |

#### FR6.2 Get Mood Distribution
| Requirement | Details |
|-------------|---------|
| **ID** | FR6.2 |
| **Title** | Get Mood Distribution |
| **Description** | Chart data for mood frequency over time |
| **Inputs** | User UID, Date Range, Granularity (daily/weekly/monthly) |
| **Outputs** | Array of {date, mood_counts} |
| **Module** | `services/stats_service/` |
| **Database** | Aggregated from `entry_analysis` |

#### FR6.3 Get Writing Patterns
| Requirement | Details |
|-------------|---------|
| **ID** | FR6.3 |
| **Title** | Get Writing Patterns |
| **Description** | Analysis of user's writing behavior (frequency, length, time) |
| **Inputs** | User UID, Date Range |
| **Outputs** | {entries_per_day, avg_length, peak_hours, day_of_week_distribution} |
| **Module** | `services/stats_service/` |

#### FR6.4 Get Mood Trends
| Requirement | Details |
|-------------|---------|
| **ID** | FR6.4 |
| **Title** | Get Mood Trends |
| **Description** | Identify positive/negative mood trends |
| **Inputs** | User UID, Period (7/30/90 days) |
| **Outputs** | Trend direction, Trend slope, Anomalies |
| **Module** | `services/stats_service/` |
| **Algorithm** | Linear regression on mood scores |

---

### MODULE 7: DATA EXPORT

#### FR7.1 Export Entries as CSV
| Requirement | Details |
|-------------|---------|
| **ID** | FR7.1 |
| **Title** | Export Entries as CSV |
| **Description** | Download all entries in CSV format |
| **Inputs** | User UID, Date Range (optional) |
| **Outputs** | CSV File (columns: date, title, content, mood, summary) |
| **Module** | `routes/export_route.py`, `services/export_service/` |
| **Format** | UTF-8, RFC 4180 compliant |

#### FR7.2 Export Entries as JSON
| Requirement | Details |
|-------------|---------|
| **ID** | FR7.2 |
| **Title** | Export Entries as JSON |
| **Description** | Download all entries in JSON format |
| **Inputs** | User UID, Date Range (optional) |
| **Outputs** | JSON File (structured array of entries) |
| **Module** | `routes/export_route.py`, `services/export_service/` |

#### FR7.3 Export Entries as PDF
| Requirement | Details |
|-------------|---------|
| **ID** | FR7.3 |
| **Title** | Export Entries as PDF |
| **Description** | Download formatted PDF with entries and analytics |
| **Inputs** | User UID, Date Range (optional), Include Analytics |
| **Outputs** | PDF File with formatted content |
| **Module** | `routes/export_route.py`, `services/export_service/` |

---

### MODULE 8: MEDIA CACHE & PROVIDER INTEGRATION

#### FR8.1 Cache Media Results
| Requirement | Details |
|-------------|---------|
| **ID** | FR8.1 |
| **Title** | Cache Media Results |
| **Description** | Store media recommendations in Firestore cache |
| **Inputs** | Media Type, Media Data |
| **Outputs** | Cache ID, TTL |
| **Module** | `services/media_recommender/cache_store.py` |
| **TTL** | 24 hours |
| **Collections** | media_cache_movies, media_cache_songs, media_cache_books, media_cache_podcasts |

#### FR8.2 Search Media Cache
| Requirement | Details |
|-------------|---------|
| **ID** | FR8.2 |
| **Title** | Search Media Cache |
| **Description** | Query cached media before hitting live providers |
| **Inputs** | Query, Media Type, Limit |
| **Outputs** | Cached results or empty |
| **Module** | `services/search_service/` |
| **Fallback** | Hit live provider if cache miss |

#### FR8.3 Cold Start Handling
| Requirement | Details |
|-------------|---------|
| **ID** | FR8.3 |
| **Title** | Cold Start Handling |
| **Description** | Recommendations for new users with no history |
| **Inputs** | New User UID, Default Mood |
| **Outputs** | Generic popular recommendations |
| **Module** | `services/personalization/cold_start_handler.py` |
| **Strategy** | Popular items + default mood-based items |

---

### MODULE 9: SYSTEM HEALTH & MONITORING

#### FR9.1 Health Check Endpoint
| Requirement | Details |
|-------------|---------|
| **ID** | FR9.1 |
| **Title** | Health Check Endpoint |
| **Description** | Check application and dependencies health |
| **Inputs** | None |
| **Outputs** | {status, services, models_loaded, timestamp} |
| **Module** | `routes/health.py`, `services/health_service.py` |
| **Checks** | Firebase, Models, Database |

#### FR9.2 Background Job Status
| Requirement | Details |
|-------------|---------|
| **ID** | FR9.2 |
| **Title** | Background Job Status |
| **Description** | Monitor long-running operations |
| **Inputs** | Job ID (optional) |
| **Outputs** | Job status, progress, result |
| **Module** | `routes/jobs.py` |

---

## NON-FUNCTIONAL REQUIREMENTS

### NFR1: Performance

| Requirement | Target |
|-------------|--------|
| **API Response Time** | < 2 seconds for 95th percentile |
| **Mood Detection Inference** | < 500ms |
| **Summarization Inference** | < 1000ms |
| **Media Recommendation** | < 2000ms |
| **Insight Generation** | < 30 seconds |
| **Database Query** | < 100ms |
| **Pagination Requests** | < 500ms |

### NFR2: Scalability

| Requirement | Details |
|-------------|---------|
| **Concurrent Users** | Support 1000+ concurrent API calls |
| **Concurrent Requests** | 50 concurrent requests per instance |
| **Database Throughput** | 100,000+ documents per day |
| **Model Inference** | GPU-accelerated with batch processing |
| **Horizontal Scaling** | Docker containerization for multi-instance deployment |

### NFR3: Reliability

| Requirement | Details |
|-------------|---------|
| **Availability** | 99.5% uptime SLA |
| **Data Redundancy** | Multi-region Firestore replication |
| **Backup Strategy** | Daily cloud backups, 30-day retention |
| **Error Recovery** | Graceful degradation, fallback models |
| **Retry Policy** | Max 2 retries with exponential backoff |

### NFR4: Security

| Requirement | Details |
|-------------|---------|
| **Authentication** | Firebase Authentication (JWT) |
| **Authorization** | Role-based access control per user |
| **Data Encryption** | TLS 1.3 in transit, Firestore encryption at rest |
| **API Key Management** | Environment variables, no hardcoded secrets |
| **SQL Injection Prevention** | ORM/Query parameterization |
| **CORS** | Whitelist allowed origins |
| **Rate Limiting** | 100 requests per minute per IP |

### NFR5: Maintainability

| Requirement | Details |
|-------------|---------|
| **Code Documentation** | 80%+ code coverage with docstrings |
| **Version Control** | Git with branching strategy |
| **Configuration Management** | config.yml centralized settings |
| **Logging** | Structured logging with log levels |
| **Monitoring** | Health checks, error tracking |

### NFR6: Compatibility

| Requirement | Details |
|-------------|---------|
| **Python Version** | 3.10+ |
| **Database** | Firestore (GCP) |
| **Deployment** | Docker, Docker Compose |
| **API Format** | REST + JSON |
| **Browser Support** | Modern browsers (Chrome, Firefox, Safari) |

---

## USER ROLES & PERSONAS

### Role 1: Regular User
- **Description**: Individual journaling daily, seeking mood insights
- **Permissions**: Create/read/update/delete own entries, access recommendations, export data
- **Use Cases**: FC1.1, FC2.1-2.5, FC3.1-3.4, FC4.1, FC5.1-5.5, FC7.1-7.3

### Role 2: Premium User
- **Description**: Heavy user, advanced analytics, priority processing
- **Permissions**: All Regular User + Advanced analytics, custom insights frequency
- **Use Cases**: FC6.1-6.4, scheduled exports

### Role 3: Administrator
- **Description**: System management, monitoring, user support
- **Permissions**: All + system health, job monitoring, user management
- **Use Cases**: FC9.1-9.2

---

## USE CASES

### UC1: User Registration & Onboarding
```
Actor: New User
Precondition: User accesses application
Main Flow:
  1. User provides email, password, display name
  2. System validates input (email format, password strength)
  3. Firebase creates user account
  4. System creates user document in Firestore
  5. User receives verification email
  6. User logs in with credentials
Postcondition: User authenticated, ready to create entries
```

### UC2: Create and Process Journal Entry
```
Actor: Authenticated User
Precondition: User is logged in
Main Flow:
  1. User writes journal entry with title and content
  2. User saves entry to backend
  3. System stores entry in Firestore
  4. System triggers analysis pipeline:
     - Mood detection (RoBERTa inference)
     - Summarization (BART inference)
     - Embedding generation
  5. Results stored in entry_analysis collection
  6. System returns analyzed entry to user
Alternate Flow (Analysis Failure):
  6a. If mood detection fails, return default mood
  6b. If summarization fails, use fallback truncation
Postcondition: Entry stored with analysis metadata
```

### UC3: Get Media Recommendations
```
Actor: Authenticated User
Precondition: User has created entries with mood analysis
Main Flow:
  1. User requests movie/song recommendations
  2. System extracts user's mood preference
  3. System queries media cache (Firestore)
  4. If cache miss:
     - Queries TMDb/Spotify/Google Books API
     - Applies similarity ranking
     - Caches results (24h TTL)
  5. System ranks results by similarity + popularity
  6. Returns top K recommendations
  7. User clicks/saves/skips recommendation
  8. System logs interaction for feedback loop
Postcondition: User receives personalized recommendations, interaction logged
```

### UC4: Generate Weekly Insights
```
Actor: Authenticated User
Precondition: User has multiple entries in past week
Main Flow:
  1. User requests insights for date range
  2. System retrieves entries + analysis
  3. System aggregates mood patterns, identifies themes
  4. System calls Insights LLM (Gemini or Qwen2):
     - Extracts goals from text
     - Identifies progress
     - Notes negative behaviors
     - Suggests remedies
  5. System stores insight in insights collection
  6. System maps entries to insight
  7. Returns insight to user
Postcondition: Structured insight stored, user informed
```

### UC5: Export Data
```
Actor: Authenticated User
Precondition: User has journal entries
Main Flow:
  1. User selects export format (CSV/JSON/PDF)
  2. User optionally selects date range
  3. System retrieves entries + analysis
  4. System formats data per selected format
  5. System generates file
  6. System initiates download
Postcondition: User receives downloadable file
```

### UC6: View Analytics Dashboard
```
Actor: Authenticated User
Precondition: User has journaled for multiple days
Main Flow:
  1. User navigates to analytics view
  2. System retrieves user's mood history
  3. System calculates statistics:
     - Total entries, average length
     - Mood distribution (pie chart data)
     - Mood trends (line chart data)
     - Writing patterns (frequency, peak hours)
  4. System returns dashboard data
Postcondition: User sees comprehensive analytics visualization
```

---

## ACCEPTANCE CRITERIA

### Acceptance Criteria for FR3.1 (Mood Detection)
- [ ] System correctly classifies emotions for 7 mood classes
- [ ] Confidence score ≥ 0.35 for all predictions
- [ ] Inference time < 500ms per entry
- [ ] Handles edge cases: empty text, very long text
- [ ] Returns structured JSON with all mood probabilities

### Acceptance Criteria for FR5.1 (Movie Recommendations)
- [ ] System returns ≥ 5 recommendations per request
- [ ] Each movie includes title, overview, rating, poster URL
- [ ] Response time < 2 seconds
- [ ] Cache hit rate > 80% (after first week)
- [ ] Recommendations vary by mood

### Acceptance Criteria for FR6.1 (Statistics)
- [ ] Calculations accurate to ±1% for aggregations
- [ ] Response time < 500ms
- [ ] Dashboard includes all required fields
- [ ] Period filtering works correctly

### Acceptance Criteria for FR4.1 (Insights)
- [ ] Generated insights include all required fields
- [ ] Insights are coherent and contextually relevant
- [ ] Response time < 30 seconds
- [ ] Fallback to generic insights on LLM failure
- [ ] Proper error messages on timeout

---

## REQUIREMENTS TRACEABILITY MATRIX

| Requirement ID | Module | Test Case | Priority |
|---|---|---|---|
| FR1.1 | auth | TC_AUTH_001 | HIGH |
| FR1.2 | auth | TC_AUTH_002 | HIGH |
| FR2.1 | journal_entries | TC_JE_001 | HIGH |
| FR2.2 | journal_entries | TC_JE_002 | HIGH |
| FR3.1 | mood_detection | TC_MD_001 | HIGH |
| FR4.1 | insights | TC_INS_001 | HIGH |
| FR5.1 | media_rec | TC_MR_001 | MEDIUM |
| FR6.1 | stats | TC_STATS_001 | MEDIUM |
| FR7.1 | export | TC_EXP_001 | MEDIUM |
| FR9.1 | health | TC_HEALTH_001 | LOW |

---

**END OF SRS DOCUMENT**

