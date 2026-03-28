# System Overview: Pocket Journal AI Backend

## Executive Summary

**Pocket Journal** is an AI-powered journaling platform that provides intelligent mood detection, automated entry summarization, personalized media recommendations, and AI-generated insights. The backend is built on Flask with Firebase Firestore persistence and integrates multiple transformer-based ML models and external media APIs.

**Target Users**: Individual journal keepers seeking AI-assisted reflection and mood-based media discovery.

---

## System Objectives

| Objective | Implementation |
|-----------|-----------------|
| **Mood Detection** | RoBERTa transformer model (fp16 + ONNX optimized) |
| **Entry Summarization** | BART transformer model (fp16 + ONNX optimized) |
| **Media Recommendations** | Intent-based ranking with semantic embeddings + external providers |
| **AI Insights** | Qwen2 local LLM or Google Gemini API |
| **Analytics** | Mood pattern tracking, entry frequency statistics |
| **Data Persistence** | Firebase Firestore with timezone-aware timestamps |
| **Authentication** | Firebase Auth (email/password) |
| **API Security** | JWT token validation, user isolation |

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Applications                      │
│                   (Web, Mobile, Desktop)                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                  ┌────────┴────────┐
                  │  HTTP / HTTPS   │
                  │  (REST API)     │
                  └────────┬────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Flask Backend                                 │
│   • /api/v1/entries       (CRUD journal entries)                │
│   • /api/v1/auth          (Authentication)                      │
│   • /api/v1/media/*       (Recommendations & search)            │
│   • /api/v1/generate_insights   (AI-generated insights)        │
│   • /api/v1/stats         (User analytics)                      │
└──────────────────┬────────────────┬────────────────┬───────────┘
                   │                │                │
      ┌────────────▼──┐  ┌──────────▼──┐  ┌─────────▼────────┐
      │   ML Pipeline │  │  Embedding  │  │  Media Providers │
      │  • Mood       │  │  Service    │  │  • TMDb (Movies) │
      │  • Summary    │  │             │  │  • Spotify       │
      │  • Insights   │  │ Intent      │  │  • Google Books  │
      └────────────┬──┘  │ Vectors     │  └────────┬────────┘
                   │     └─────────────┘           │
      ┌────────────▼──────────────────────────────┘
      │
┌─────▼──────────────────────────────────────────┐
│   Firebase Services                             │
│   • Firestore (journal_entries, analysis)      │
│   • Firebase Auth                              │
│   • Media Cache (Firestore-backed)             │
└─────────────────────────────────────────────────┘
```

---

## System Components

### 1. **API Gateway (Flask)**
- Entry point for all client requests
- Route registration for auth, entries, media, insights, stats
- Authentication middleware (JWT token validation)
- Request/response logging
- Error handling and status code mapping

### 2. **ML Inference Pipeline**
- **Mood Detection**: RoBERTa (v2, fp16)
  - Input: Journal entry text
  - Output: 7-class emotion distribution (anger, disgust, fear, happy, neutral, sad, surprise)
  - Threshold: 0.35

- **Summarization**: BART (v2, fp16)
  - Input: Journal entry text
  - Output: Concise summary (20-128 tokens)
  - Num beams: 4

- **Insight Generation**: Qwen2 (local) or Gemini (cloud)
  - Input: Mood patterns, entry analysis over date range
  - Output: Structured reflection with goals, progress, remedies

### 3. **Embedding Service**
- Sentence-Transformers (`all-mpnet-base-v2`)
- Generates dense vectors for:
  - Journal entries (intent building)
  - Media titles and metadata (recommendation ranking)
- Blend weights: Journal 5%, Taste 95%

### 4. **Media Recommendation Engine**
- **Providers**: TMDb (movies), Spotify (songs/podcasts), Google Books
- **Pipeline**: Intent → Candidate Fetch → Ranking → Dedup → Format
- **Caching**: Firestore-backed media cache (24h TTL)
- **Fallback**: Live provider fetch if cache misses

### 5. **Database Layer (Firestore)**
- **journal_entries**: User journal text + timestamps
- **entry_analysis**: Mood, summary, raw ML outputs
- **insights**: AI-generated reflections
- **journal_embeddings**: Dense vectors for intent matching
- **user_vectors**: User embedding aggregate (taste profile)
- **media_cache**: Cached media items from external providers

### 6. **External Integrations**
- **Firebase**: Auth, Firestore data store
- **TMDb API**: Movie recommendations (trending, popular, top-rated)
- **Spotify Web API**: Song and podcast recommendations
- **Google Books API**: Book recommendations
- **Google Gemini** (optional): Advanced insight generation

---

## Data Flow Overview

### Create Journal Entry
```
1. User submits entry text
2. Backend validates authentication
3. Insert into journal_entries collection
4. Trigger ML analysis:
   - Mood detection (RoBERTa)
   - Summarization (BART)
5. Store analysis in entry_analysis
6. Generate and cache embeddings
7. Return entry_id + analysis to client
```

### Get Media Recommendations
```
1. Fetch today's mood summary for user
2. Determine dominant mood
3. Build intent vector (user embeddings + mood context)
4. Query media cache (24h freshness window)
5. Rank cached results by similarity + popularity
6. If low cache hit: fallback to live provider fetch
7. Deduplicate, format, return
```

### Generate Insights
```
1. Query entries for date range (user-specified)
2. Aggregate mood patterns
3. If Gemini enabled: call API with aggregated data
4. Else: invoke local Qwen2 model
5. Parse structured response (goals, progress, etc.)
6. Store in insights collection with entry mappings
7. Return to client
```

---

## Key Services & Responsibilities

| Service | Responsibility | Tech Stack |
|---------|-----------------|-----------|
| **Journal Entries** | CRUD + reanalysis | Firestore, RoBERTa, BART |
| **Media Recommendations** | Intent → ranking → provider fallback | Embedding service, Cache, Providers |
| **Embedding Service** | Vector generation for entries & media | sentence-transformers |
| **Search Service** | Cache-first hybrid search across media types | Firestore, Providers, fuzzy matching |
| **Insights Service** | Mood-based reflection generation | Qwen2 or Gemini |
| **Export Service** | CSV/PDF export of entries & data | Firestore queries |
| **Stats Service** | User analytics (mood trends, frequency) | Firestore aggregation |
| **Health Service** | System status monitoring | Service checks |

---

## Deployment Model

- **Framework**: Flask + Gunicorn
- **Containerization**: Docker with NVIDIA CUDA runtime (GPU support)
- **Database**: Firebase Firestore (managed)
- **Authentication**: Firebase Auth (managed)
- **Logging**: Colored console output, per-module levels
- **Configuration**: YAML + environment variable overrides

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **API** | Flask 3.1.2, Werkzeug 3.1.5, Gunicorn 25.1.0 |
| **Database** | Firebase Admin SDK, google-cloud-firestore |
| **ML/NLP** | transformers, torch, sentence-transformers |
| **API Clients** | requests, spotipy, RapidFuzz |
| **Utilities** | LangChain, pytz, tqdm, python-dotenv |

---

## Performance Targets

- **Mood Detection**: <500ms per entry
- **Summarization**: <2s per entry
- **Media Recommendation**: <1.5s (cache hit), <3s (provider fallback)
- **Embedding Generation**: <300ms per entry
- **API Response**: <2s p99 (auth + validation included)

---

## Security Model

- **Authentication**: Firebase JWT tokens (validated on each request)
- **Authorization**: User-scoped data access (UID isolation)
- **Secrets**: Firebase credentials from env var `FIREBASE_CREDENTIALS_PATH`
- **API Keys**: External service keys from environment variables
- **Rate Limiting**: Per-provider configuration (Spotify, TMDb, Google)
- **Data Protection**: Firestore security rules (enforced server-side)

---

## Development Phases

| Phase | Scope |
|-------|-------|
| **Phase 1** | Core entry management + mood detection |
| **Phase 2** | Summarization + basic recommendations |
| **Phase 2.5** | Embedding-based ranking (semantic similarity) |
| **Phase 3** | Cache-first media pipeline + search optimization |
| **Phase 4** | Insights generation + export |
| **Phase 5** | Advanced analytics, multi-user features |

---

## Known Limitations & Constraints

1. **ML Models**: RoBERTa/BART optimized for English; non-English entries may have degraded accuracy
2. **Media Providers**: Dependent on external API availability (TMDb, Spotify, Google Books)
3. **Cache Strategy**: 24-hour TTL; time-sensitive recommendations may miss very recent releases
4. **Concurrency**: Single Flask process; scale horizontally with Gunicorn workers
5. **Insights**: Local Qwen2 requires GPU; fallback to Gemini API if GPU unavailable
6. **Emoji Support**: Some unicodes may not serialize correctly (Firestore limitation)

---

## Next Steps

- Refer to **ARCHITECTURE.md** for detailed service breakdown
- See **API_SPECIFICATION.md** for endpoint contracts
- Check **DATABASE_SCHEMA.md** for data model details
- Review **DEPLOYMENT.md** for local/Docker setup instructions


