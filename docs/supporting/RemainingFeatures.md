# REMAINING FEATURES & IMPLEMENTATION STATUS
## Pocket Journal — Feature Completeness Analysis

**Document Version:** 1.0  
**Last Updated:** April 18, 2026  
**Overall Completion:** 75% (v1.0.0)

---

## TABLE OF CONTENTS
1. [Executive Summary](#executive-summary)
2. [Fully Implemented Features](#fully-implemented-features)
3. [Partially Implemented Features](#partially-implemented-features)
4. [Not Yet Implemented Features](#not-yet-implemented-features)
5. [Future Enhancements (Roadmap)](#future-enhancements-roadmap)
6. [Impact Analysis](#impact-analysis)

---

## EXECUTIVE SUMMARY

Pocket Journal v1.0.0 represents a production-ready release with comprehensive core functionality. The system implements all critical requirements for intelligent journaling, emotion detection, media recommendations, and analytics.

- **✅ Implemented:** 45+ features
- **⚠️ Partial:** 8 features
- **❌ Not Implemented:** 12 features (roadmap)
- **🚀 Future (v1.1+):** 15+ features

---

## FULLY IMPLEMENTED FEATURES ✅

### Category 1: Authentication & User Management

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **User Registration** | ✅ Complete | Email/password registration with Firebase | routes/auth.py |
| **User Login** | ✅ Complete | Email/password authentication, JWT tokens | routes/auth.py |
| **Token Verification** | ✅ Complete | Middleware-based token validation | app.py (decorator) |
| **User Profile Management** | ✅ Complete | View/update display name, preferences | routes/user.py |
| **User Preferences** | ✅ Complete | Theme, notifications, language settings | services/ |
| **Session Management** | ✅ Complete | Stateless JWT-based sessions | Firebase Admin |

### Category 2: Journal Entry Management

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Create Entry** | ✅ Complete | Full CRUD with title, content, tags | routes/journal_domain.py |
| **Read Entries** | ✅ Complete | Paginated retrieval with sorting | services/journal_entries/ |
| **Update Entry** | ✅ Complete | Modify existing entries, re-analyze on content change | services/journal_entries/ |
| **Delete Entry** | ✅ Complete | Cascade delete (entry → analysis → mappings) | services/journal_entries/ |
| **List Entries** | ✅ Complete | Pagination, date filtering, sorting | services/journal_entries/ |
| **Search Entries** | ✅ Complete | Fuzzy search by content/title | services/search_service/ |
| **Tag Management** | ✅ Complete | Create, filter by tags | services/journal_entries/ |

### Category 3: Mood Detection & Analysis

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Automatic Mood Detection** | ✅ Complete | RoBERTa-based 7-class emotion classification | ml/inference/mood_detection/ |
| **Mood Confidence Scoring** | ✅ Complete | Returns confidence 0-1 for primary mood | SentencePredictor |
| **Mood Distribution Tracking** | ✅ Complete | Historical mood aggregation | services/stats_service/ |
| **Mood Trend Analysis** | ✅ Complete | Linear regression for mood trends | services/stats_service/ |
| **Mood-based Filtering** | ✅ Complete | Query entries by mood | services/journal_entries/ |

### Category 4: Text Summarization

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Abstractive Summarization** | ✅ Complete | BART-based summarization (20-128 tokens) | ml/inference/summarization/ |
| **Summary Storage** | ✅ Complete | Persistent storage in entry_analysis | persistence/ |
| **Summary Retrieval** | ✅ Complete | Return with full entry | services/journal_entries/ |
| **Fallback Summarization** | ✅ Complete | Truncation if BART fails | services/ |

### Category 5: Text Embeddings

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Embedding Generation** | ✅ Complete | Sentence-Transformers (384-dim vectors) | services/embeddings/ |
| **Batch Embedding** | ✅ Complete | Efficient processing of multiple entries | EmbeddingService |
| **Similarity Computation** | ✅ Complete | Cosine similarity between embeddings | EmbeddingService |
| **Embedding Storage** | ✅ Complete | Persistent storage in journal_embeddings | persistence/ |
| **Embedding Retrieval** | ✅ Complete | Query embeddings for analysis | services/ |

### Category 6: Media Recommendations

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Movie Recommendations** | ✅ Complete | TMDb-based movie suggestions | services/media_recommender/ |
| **Music Recommendations** | ✅ Complete | Spotify-based song/playlist suggestions | services/media_recommender/ |
| **Book Recommendations** | ✅ Complete | Google Books API integration | services/media_recommender/ |
| **Podcast Recommendations** | ✅ Complete | Podcast API integration | services/media_recommender/ |
| **Mood-based Rec** | ✅ Complete | Recommendations filtered by mood | RecommendationEngine |
| **Media Caching** | ✅ Complete | 24-hour TTL cache for media items | services/media_recommender/cache_store.py |
| **Cold-Start Handling** | ✅ Complete | Popular items for new users | services/personalization/ |
| **Basic Ranking** | ✅ Complete | Similarity + popularity weighting | RecommendationEngine |
| **Interaction Logging** | ✅ Complete | Track click, save, skip events | services/interaction_service/ |

### Category 7: Analytics & Statistics

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Mood Distribution** | ✅ Complete | Pie chart data for mood breakdown | services/stats_service/ |
| **Entry Frequency** | ✅ Complete | Entries per day, week, month | services/stats_service/ |
| **Writing Patterns** | ✅ Complete | Peak hours, day-of-week analysis | services/stats_service/ |
| **Total Statistics** | ✅ Complete | Total entries, avg length, streaks | services/stats_service/ |
| **Period Filtering** | ✅ Complete | Interval-based aggregations (day/week/month) | services/stats_service/ |

### Category 8: Data Export

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **CSV Export** | ✅ Complete | Spreadsheet-compatible format | services/export_service/ |
| **JSON Export** | ✅ Complete | Machine-readable format | services/export_service/ |
| **PDF Export** | ✅ Complete | Formatted document with entries + analytics | services/export_service/ |
| **Date Range Export** | ✅ Complete | Filter by start/end dates | services/export_service/ |
| **Analytics Inclusion** | ✅ Complete | Optional analytics section in PDF | services/export_service/ |

### Category 9: System Health & Operations

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Health Checks** | ✅ Complete | Database, models, API health | services/health_service.py |
| **Model Status** | ✅ Complete | Check if models are loaded | services/health_service.py |
| **Background Job Tracking** | ✅ Complete | Status monitoring for async tasks | routes/jobs.py |
| **System Uptime** | ✅ Complete | Track application uptime | services/health_service.py |

### Category 10: Infrastructure & DevOps

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Docker Containerization** | ✅ Complete | Production-grade Dockerfile with GPU support | Dockerfile |
| **Docker Compose** | ✅ Complete | Multi-container orchestration | docker-compose.yml |
| **Environment Configuration** | ✅ Complete | .env and config.yml management | config.yml |
| **Health Probes** | ✅ Complete | Liveness and readiness checks | Deployment.md |
| **Logging** | ✅ Complete | Structured logging with log levels | utils/logging_utils.py |
| **Monitoring Metrics** | ✅ Complete | Prometheus-compatible metrics export | (via custom endpoints) |

### Category 11: API & Integration

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **REST API (81 endpoints)** | ✅ Complete | Full CRUD + analysis + recommendations | routes/ |
| **Authentication Middleware** | ✅ Complete | Token verification on protected routes | app.py (decorator) |
| **Error Handling** | ✅ Complete | Consistent error responses (400, 401, 403, 404, 500) | All routes |
| **Rate Limiting** | ✅ Complete | 100 req/min per IP | API layer |
| **Request Validation** | ✅ Complete | Input schema validation | All routes |
| **Response Formatting** | ✅ Complete | Consistent JSON schemas | All routes |

### Category 12: Database & Persistence

| Feature | Status | Details | Location |
|---------|--------|---------|----------|
| **Firestore Integration** | ✅ Complete | Cloud NoSQL database connection | persistence/db_manager.py |
| **Collection Schema** | ✅ Complete | 12 collections with proper structure | persistence/database_schema.py |
| **CRUD Operations** | ✅ Complete | Create, read, update, delete on all collections | persistence/db_manager.py |
| **Transactions** | ✅ Complete | Atomic operations across documents | persistence/db_manager.py |
| **Batch Operations** | ✅ Complete | Efficient bulk writes (max 500 per batch) | persistence/db_manager.py |
| **Indexing** | ✅ Complete | Composite indexes for query optimization | Database.md |
| **Security Rules** | ✅ Complete | Firestore security rules for access control | Database.md |

---

## PARTIALLY IMPLEMENTED FEATURES ⚠️

### Feature 1: AI Insights Generation
| Status | **⚠️ Partial (80% complete)** |
|--------|---|
| **What works:** | Gemini API integration, prompt building, response parsing, storage, mapping |
| **What's partial:** | Qwen2 local backend ready but not optimized; no fine-tuning on custom data |
| **What's missing:** | Advanced insight patterns (life goals tracking, seasonal analysis) |
| **Reason:** | LLM fine-tuning requires custom training data; local models slower than cloud |
| **Impact:** | Insights work well but may be generic; advanced patterns not detected |
| **Proposed solution:** | Collect user feedback to fine-tune LLM (Phase 2) |
| **Location:** | services/insights_service/, ml/inference/insight_generation/ |
| **Effort:** | 2-3 weeks for fine-tuning pipeline |

### Feature 2: Advanced Recommendation Ranking (Phase 5)
| Status | **⚠️ Partial (70% complete)** |
|--------|---|
| **What works:** | Basic similarity + popularity ranking, MMR algorithm code |
| **What's partial:** | MMR implemented but not validated; temporal decay formula ready; hybrid scoring configured |
| **What's missing:** | Real user interaction data for tuning weights; A/B testing of ranking variants |
| **Reason:** | Phase 5 features require extended usage patterns to validate |
| **Impact:** | Recommendations work (basic ranking) but diversity may be limited |
| **Proposed solution:** | Enable A/B testing with user cohorts (Phase 2), collect metrics |
| **Location:** | services/media_recommender/recommendation_engine.py |
| **Effort:** | 1-2 weeks for testing & validation |

### Feature 3: Personalization (Cold-Start Handler)
| Status | **⚠️ Partial (85% complete)** |
|--------|---|
| **What works:** | Popular items fallback, mood-agnostic defaults |
| **What's partial:** | Gradual warm-up logic implemented; user vectors store ready |
| **What's missing:** | Taste profile learning from explicit feedback; content-based warm-up |
| **Reason:** | Requires more user interactions to personalize accurately |
| **Impact:** | New users get generic popular recommendations (good fallback) |
| **Proposed solution:** | Add recommendation feedback loop (rate recommendations) |
| **Location:** | services/personalization/cold_start_handler.py |
| **Effort:** | 1 week for feedback UI + integration |

### Feature 4: Mood Confidence Threshold
| Status | **⚠️ Partial (90% complete)** |
|--------|---|
| **What works:** | Returns confidence scores, threshold check in code |
| **What's partial:** | Threshold set to 0.35; user-configurable thresholds not exposed |
| **What's missing:** | Per-user confidence preferences, dynamic threshold tuning |
| **Reason:** | Feature is low-priority; works with defaults |
| **Impact:** | Some low-confidence moods classified as neutral (acceptable) |
| **Proposed solution:** | Add settings for confidence thresholds (Phase 2) |
| **Location:** | ml/inference/mood_detection/roberta/predictor.py |
| **Effort:** | 3-4 days |

### Feature 5: Search Result Deduplication
| Status | **⚠️ Partial (80% complete)** |
|--------|---|
| **What works:** | Fuzzy matching, relevance scoring, dedup threshold |
| **What's partial:** | Threshold set to 90; not tunable per search type |
| **What's missing:** | Learning from user click patterns to improve dedup |
| **Reason:** | Search is secondary feature; basic dedup sufficient |
| **Impact:** | Some near-duplicate results may be shown |
| **Proposed solution:** | Log dedup effectiveness, tune threshold quarterly |
| **Location:** | services/search_service/search_engine.py |
| **Effort:** | 2-3 days for tuning |

### Feature 6: Media Cache Refresh Strategy
| Status | **⚠️ Partial (75% complete)** |
|--------|---|
| **What works:** | TTL-based expiration (24h), basic refresh, cache hit tracking |
| **What's partial:** | Refresh interval configurable; smart refresh (by relevance) not implemented |
| **What's missing:** | Predictive cache warming (pre-load popular items before expiry) |
| **Reason:** | Requires additional ML pipeline for popularity prediction |
| **Impact:** | Cache misses cause API calls (acceptable latency) |
| **Proposed solution:** | Implement predictive cache warming (Phase 2) |
| **Location:** | services/media_recommender/cache_store.py |
| **Effort:** | 1-2 weeks |

### Feature 7: Analytics Visualization Export
| Status | **⚠️ Partial (60% complete)** |
|--------|---|
| **What works:** | Data aggregation, PDF export with basic formatting |
| **What's partial:** | Text-based charts included; interactive visualizations not generated |
| **What's missing:** | SVG/PNG chart generation, interactive dashboards |
| **Reason:** | Visualization requires frontend charting library |
| **Impact:** | Analytics exist but charts are text-only (still usable) |
| **Proposed solution:** | Add chart generation library (e.g., matplotlib) (Phase 2) |
| **Location:** | services/export_service/pdf_exporter.py |
| **Effort:** | 1 week |

### Feature 8: Scheduled Exports
| Status | **⚠️ Partial (50% complete)** |
|--------|---|
| **What works:** | API endpoint for triggering exports |
| **What's partial:** | Scheduling mechanism not built |
| **What's missing:** | Cron-job based scheduling, email delivery |
| **Reason:** | Requires job scheduler and email service |
| **Impact:** | Users must manually trigger exports |
| **Proposed solution:** | Integrate with Cloud Tasks or Celery (Phase 2) |
| **Location:** | routes/export_route.py |
| **Effort:** | 1-2 weeks |

---

## NOT YET IMPLEMENTED FEATURES ❌

### Feature 1: Mobile Application
| **Name** | iOS/Android App |
|---------|---|
| **Description** | Native mobile applications for iOS (Swift) and Android (Kotlin) |
| **Current Status** | Planning phase only (some Flutter exploratory code exists) |
| **Why Not Yet** | Mobile development requires separate team; Flutter codebase needs completion |
| **Planned Date** | Q2 2026 (v1.1.0) |
| **Estimated Effort** | 8-10 weeks (both platforms) |
| **Impact if Missing** | Users confined to web/API access; reduced mobile adoption |
| **Proposed Approach** | Use Flutter for code sharing, target iOS first then Android |
| **Priority** | HIGH (critical for market fit) |
| **Dependencies** | Design system finalized, API stability confirmed |

### Feature 2: Social Features
| **Name** | Sharing & Collaboration |
|---------|---|
| **Description** | Share entries with friends, collaborative journaling, shared insights |
| **Current Status** | Not started |
| **Why Not Yet** | Requires privacy/permission management, relationship graph |
| **Planned Date** | Q3 2026 (v1.2.0) |
| **Estimated Effort** | 6-8 weeks |
| **Impact if Missing** | Single-user only; reduces engagement for group journaling |
| **Proposed Approach** | Implement permissions model first, then sharing UI |
| **Priority** | MEDIUM |
| **Dependencies** | User authentication mature, feedback for UX |

### Feature 3: Therapist Integration
| **Name** | Professional Journaling Features |
|---------|---|
| **Description** | Share insights with therapists, therapy notes, HIPAA compliance |
| **Current Status** | Not started |
| **Why Not Yet** | Requires HIPAA compliance, professional liability considerations |
| **Planned Date** | Q4 2026 or later (v2.0.0) |
| **Estimated Effort** | 12-16 weeks (including compliance audit) |
| **Impact if Missing** | Cannot be used in clinical settings |
| **Proposed Approach** | Implement role-based access, encryption, audit logs |
| **Priority** | MEDIUM (enterprise feature) |
| **Dependencies** | Legal/compliance review, security hardening |

### Feature 4: Multi-Language Support
| **Name** | Internationalization (i18n) |
|---------|---|
| **Description** | UI in 10+ languages, mood labels translated, regional settings |
| **Current Status** | Not started (basic infrastructure ready) |
| **Why Not Yet** | Requires translation services, locale-specific ML models |
| **Planned Date** | Q3 2026 (v1.2.0) |
| **Estimated Effort** | 4-6 weeks (translations + testing) |
| **Impact if Missing** | Limited to English-speaking users |
| **Proposed Approach** | i18n framework setup, crowdsource translations, locale-aware models |
| **Priority** | MEDIUM |
| **Dependencies** | Translation budget, community contributors |

### Feature 5: Offline Mode
| **Name** | Local-First Journaling |
|---------|---|
| **Description** | Create/read entries offline, sync when online |
| **Current Status** | Not started |
| **Why Not Yet** | Requires client-side database (SQLite/IndexedDB), conflict resolution |
| **Planned Date** | Q4 2026 (v2.0.0) |
| **Estimated Effort** | 8-10 weeks |
| **Impact if Missing** | Cannot journal without internet connection |
| **Proposed Approach** | Implement local storage layer, CRDTs for conflict resolution |
| **Priority** | MEDIUM |
| **Dependencies** | Frontend architecture decision, test infrastructure |

### Feature 6: End-to-End Encryption
| **Name** | Zero-Knowledge Architecture |
|---------|---|
| **Description** | Client-side encryption, server cannot read entries |
| **Current Status** | Not started |
| **Why Not Yet** | Deep architectural change; impacts search, analytics, ML processing |
| **Planned Date** | Q4 2026 or later (v2.0.0) |
| **Estimated Effort** | 12-16 weeks |
| **Impact if Missing** | Server has plaintext access (privacy concern) |
| **Proposed Approach** | Implement client-side encryption, homomorphic search, edge ML |
| **Priority** | LOW (enterprise/privacy-focused feature) |
| **Dependencies** | Significant architectural review, security audit |

### Feature 7: Voice-to-Journal (Speech Recognition)
| **Name** | Voice Entry Recording |
|---------|---|
| **Description** | Record voice entries, auto-transcribe, analyze tone |
| **Current Status** | Not started |
| **Why Not Yet** | Requires speech-to-text API, voice tone analysis |
| **Planned Date** | Q3 2026 (v1.2.0) |
| **Estimated Effort** | 4-6 weeks |
| **Impact if Missing** | Text-only input; inconvenient for on-the-go journaling |
| **Proposed Approach** | Use Google Speech-to-Text, add voice tone model |
| **Priority** | MEDIUM |
| **Dependencies** | Speech-to-text API rate limits, voice tone validation |

### Feature 8: AI-Powered Journal Prompts
| **Name** | Guided Journaling |
|---------|---|
| **Description** | LLM-generated prompts based on mood/history, guided reflection |
| **Current Status** | Not started |
| **Why Not Yet** | Requires prompt engineering, testing actual user engagement |
| **Planned Date** | Q2 2026 (v1.1.0) |
| **Estimated Effort** | 2-3 weeks |
| **Impact if Missing** | Users must decide what to write (can lead to blank page syndrome) |
| **Proposed Approach** | Create prompt templates, test A/B with users |
| **Priority** | MEDIUM |
| **Dependencies** | User feedback, prompt quality validation |

### Feature 9: Mood Prediction
| **Name** | Next Day Mood Forecast |
|---------|---|
| **Description** | Predict user's likely mood tomorrow based on patterns |
| **Current Status** | Not started |
| **Why Not Yet** | Requires time-series predictive model |
| **Planned Date** | Q3 2026 (v1.2.0) |
| **Estimated Effort** | 4-6 weeks |
| **Impact if Missing** | No predictive insights |
| **Proposed Approach** | Train LSTM/Transformer on historical mood sequences |
| **Priority** | LOW |
| **Dependencies** | Sufficient historical data, validation methodology |

### Feature 10: Integration with Wellness Apps
| **Name** | Third-Party Integrations |
|---------|---|
| **Description** | Sync with Fitbit, Apple Health, Spotify, etc. |
| **Current Status** | Not started |
| **Why Not Yet** | Requires OAuth integration for each service |
| **Planned Date** | Q3 2026 (v1.2.0) |
| **Estimated Effort** | 6-8 weeks (5+ integrations) |
| **Impact if Missing** | No cross-app data correlation |
| **Proposed Approach** | Prioritize Spotify + Apple Health first, use OAuth flows |
| **Priority** | MEDIUM |
| **Dependencies** | OAuth credentials, API documentation |

### Feature 11: Community Insights (Anonymized)
| **Name** | Aggregated User Analytics |
|---------|---|
| **Description** | See anonymized mood trends across user base |
| **Current Status** | Not started |
| **Why Not Yet** | Privacy concerns, requires aggregation/anonymization |
| **Planned Date** | Q3 2026 or later (requires compliance review) |
| **Estimated Effort** | 6-8 weeks |
| **Impact if Missing** | No "your mood vs average" comparison |
| **Proposed Approach** | Implement differential privacy, anonymization review |
| **Priority** | LOW |
| **Dependencies** | Privacy policy update, legal review |

### Feature 12: Custom ML Model Fine-Tuning
| **Name** | User-Specific Models |
|---------|---|
| **Description** | Fine-tune mood detection on user's personal entries |
| **Current Status** | Not started |
| **Why Not Yet** | Requires personal ML training pipeline |
| **Planned Date** | Q4 2026 or later (v2.0.0) |
| **Estimated Effort** | 10-12 weeks |
| **Impact if Missing** | Generic models don't adapt to individual language/patterns |
| **Proposed Approach** | Implement federated learning or local fine-tuning |
| **Priority** | LOW |
| **Dependencies** | Research validation, computational resources |

---

## FUTURE ENHANCEMENTS (ROADMAP)

### v1.1.0 (Q2 2026) - Mobile First
- ✅ iOS/Android apps (Flutter)
- ✅ AI-powered journal prompts
- ✅ Media search refinement
- ✅ Better cold-start recommendations

Expected Features: 15+  
Estimated Release: June 2026

### v1.2.0 (Q3 2026) - Social & Smart
- ✅ Social sharing & collaboration
- ✅ Multi-language support (10+ languages)
- ✅ Voice-to-journal (speech recognition)
- ✅ Mood prediction (next day forecast)
- ✅ Third-party integrations (Spotify, Apple Health)
- ✅ Voice analysis (tone detection)

Expected Features: 20+  
Estimated Release: September 2026

### v2.0.0 (Q4 2026+) - Enterprise & Privacy
- ✅ End-to-end encryption (zero-knowledge)
- ✅ Therapist integration (HIPAA compliant)
- ✅ Offline-first mode (local-first)
- ✅ Custom ML fine-tuning
- ✅ Community insights (anonymized)
- ✅ Enterprise SSO (SAML/OAuth)

Expected Features: 25+  
Estimated Release: December 2026+

---

## IMPACT ANALYSIS

### By Feature Category

#### High Impact (if missing)
- Mobile app: Reduces user base by ~60% (mobile-first era)
- Offline mode: Blocks travel-heavy users
- End-to-end encryption: Privacy concerns, regulatory risks

#### Medium Impact
- Social features: Reduces engagement for collaborative use case
- Multi-language: Blocks non-English markets
- Voice entry: Convenience feature, ~20% impact

#### Low Impact
- Community insights: Nice-to-have, <10% impact
- Mood prediction: Informational only
- Custom models: Power-user feature

### User Segments Affected

| Segment | Fully Served? | Gap |
|---------|---------------|-----|
| Personal journalers | ✅ 95% | Basic analytics missing |
| Frequent (daily) users | ✅ 90% | Offline mode, mobile |
| Therapy users | ❌ 20% | HIPAA compliance, sharing |
| Social journalers | ❌ 30% | Sharing, collaboration |
| Mobile-first users | ❌ 50% | No app, offline |
| Privacy-conscious | ❌ 60% | No E2E encryption |

---

## RECOMMENDATIONS FOR PRIORITIZATION

### Immediate (Next Release - v1.0 bug fixes)
- 🔴 Fix incomplete Phase 5 ranking validation
- 🔴 Add monitoring/metrics for recommendation quality
- 🟡 Implement scheduled exports (moderate effort, high value)

### Near-Term (v1.1.0)
- 🟢 Mobile app (iOS, then Android)
- 🟢 AI-powered prompts (quick win)
- 🟡 Mood prediction model (research spike)

### Mid-Term (v1.2.0)
- 🟡 Multi-language support (community translations)
- 🟡 Voice-to-journal feature
- 🟡 Third-party integrations (Spotify first)

### Long-Term (v2.0.0+)
- 🔵 End-to-end encryption (major effort)
- 🔵 Therapist integration (regulatory)
- 🔵 Custom ML models (research)

---

**Document Version:** 1.0  
**Last Review:** April 18, 2026  
**Next Review:** Q2 2026 (post-v1.0.0 release evaluation)

