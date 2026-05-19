# SYSTEM DESIGN
## Architecture, Integration, and Design Decisions

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

**Note:** This document provides academic perspective on system design. For complete technical architecture, see engineering/Architecture.md.

---

## 1. OVERALL SYSTEM ARCHITECTURE

### 1.1 Architecture Overview

Pocket Journal implements a **layered microservices architecture** with clear separation of concerns:

```
┌─────────────────────────────────────┐
│   Presentation Layer (REST API)      │
│   - 81 endpoints                     │
│   - JSON request/response            │
│   - Authentication & validation      │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│   Business Logic Layer (Services)    │
│   - Entry management                 │
│   - Recommendation engine            │
│   - Analytics calculation            │
│   - Insight generation               │
└──────────────────┬──────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼───┐  ┌───────▼──────┐  ┌───▼───┐
│  ML   │  │ Persistence  │  │ Cache │
│Engine │  │  (Firestore) │  │ (24h) │
└───────┘  └──────────────┘  └───────┘
```

---

### 1.2 Design Decisions

**Decision 1: Layered Architecture**
- *Options:* Pure microservices vs layered vs serverless
- *Choice:* Layered (API → Services → Persistence)
- *Justification:* Simpler to deploy and maintain; suitable for team size

**Decision 2: REST API vs GraphQL**
- *Options:* REST (simple) vs GraphQL (flexible queries)
- *Choice:* REST
- *Justification:* Standard for journaling apps; simpler client implementation

**Decision 3: Firestore vs Traditional SQL**
- *Options:* SQL (PostgreSQL) vs NoSQL (Firestore, MongoDB)
- *Choice:* Firestore
- *Justification:* Fully managed; scales without DevOps; built-in security rules

**Decision 4: Cloud LLM vs Local LLM**
- *Options:* Cloud only vs local only vs both
- *Choice:* Both with fallback
- *Justification:* Gemini (quality) + Qwen2 (privacy); automatic fallback

---

## 2. ENTRY PROCESSING PIPELINE

### 2.1 Pipeline Design

The entry processing pipeline achieves **parallel execution** of three independent components:

```
User submits entry
       │
       ▼
[Validation]
       │
       ▼
[Store in DB]
       │
       ▼
┌──────┴──────┬─────────────┐
│             │             │
▼             ▼             ▼
[RoBERTa]  [BART]      [Embeddings]
│             │             │
└──────┬──────┴─────────────┘
       │ (wait for all 3)
       ▼
[Store analysis]
       │
       ▼
[Return to user]
```

**Key Design Insight:** All 3 models run in parallel (not sequentially), reducing total time from ~2.2s (sequential) to ~1.2s (parallel).

### 2.2 Error Handling

**Resilience Strategy:**
- Entry persisted BEFORE inference (reduces impact of model failures)
- If any model fails: Return entry with partial analysis
- Graceful degradation: System functional even if one model down

**Example:**
- RoBERTa fails → Return entry + summary + embedding (no mood)
- BART fails → Return entry + mood + embedding (no summary)
- All fail → Return entry only (still useful)

---

## 3. RECOMMENDATION ENGINE DESIGN

### 3.1 Two-Mode Design

The recommendation engine supports two modes:

**Mode A: Basic Ranking**
```
similarity = cosine(mood_embedding, candidate_embedding)
popularity = normalize(item_popularity)
score = similarity × 0.9 + popularity × 0.1
```

**Mode B: Phase 5 Advanced Ranking**
```
score = sim × 0.5 + interaction × 0.2 + popularity × 0.2 + recency × 0.1
mmr = 0.7 × relevance - 0.3 × diversity
temporal_decay = exp(-0.15 × days_old)
```

**Design Rationale:**
- Basic mode sufficient for cold-start users
- Advanced mode requires warm-up period
- Can switch between modes without code change

### 3.2 Cold-Start Problem

**Definition:** New user has <3 entries, insufficient data for personalization

**Solution:**
1. **Immediate:** Return popular items (no personalization)
2. **After 3 entries:** Analyze entries for mood patterns
3. **After 10 entries:** Full personalization possible

**Implementation:**
```python
num_entries = count_user_entries(uid)
if num_entries < 3:
    return popular_items(media_type)
elif num_entries < 10:
    return basic_ranking(mood_for_entries)
else:
    return advanced_ranking(user_taste_vector)
```

---

## 4. INSIGHT GENERATION PIPELINE

### 4.1 LLM Backend Abstraction

The system abstracts LLM backend selection:

```python
if config.use_gemini and api_available():
    insight = gemini_backend.generate(prompt)
else:
    insight = qwen2_backend.generate(prompt)
```

**Design Benefits:**
1. **Quality:** Gemini better (larger, more training data)
2. **Privacy:** Qwen2 local (no data leaves system)
3. **Cost:** Qwen2 cheaper (no API costs)
4. **Resilience:** Automatic fallback if API down

### 4.2 Prompt Engineering

**Prompt Structure:**
```
You are a thoughtful psychological assistant analyzing journal entries.

Given entries from {date_range}:
- Mood distribution: {moods}
- Common themes: {themes}
- Entry summaries: {summaries}

Provide insights as JSON:
{
  "goals": [...],
  "progress": "...",
  "negative_behaviors": "...",
  "remedies": "...",
  "appreciation": "...",
  "conflicts": "..."
}
```

**Design Decisions:**
- Structured output (JSON) for parsing
- Few-shot (examples provided)
- Role definition ("psychological assistant")

---

## 5. SCALABILITY DESIGN

### 5.1 Horizontal Scaling

The system scales horizontally:
- Stateless API layer (no session affinity)
- Shared database (Firestore handles concurrent access)
- Load balancer distributes requests

```
LB → Pod 1 (8080)
  → Pod 2 (8080)
  → Pod 3 (8080)
     ↓
   Firestore (shared)
```

**Bottleneck Analysis:**
- Not API layer (stateless, easily parallelizable)
- Potentially database (Firestore handles auto-scaling)
- Potentially model inference (GPU memory limited)

### 5.2 GPU Allocation

**Challenge:** GPUs expensive, limited resource

**Solution:**
- Batch processing: Multiple entries per GPU forward pass
- Model sharing: Single model instance serves all requests
- Time-sharing: Multiplex requests over time

**Trade-off:** Latency vs throughput (tunable)

---

## 6. SECURITY DESIGN

### 6.1 Authentication

- Firebase authentication (industry standard)
- JWT tokens (stateless, scalable)
- Token verification on every request

**Trade-off:** No refresh tokens (simpler) vs refresh tokens (more complex)

### 6.2 Data Privacy

**At Rest:**
- Firestore encrypts data automatically
- Backup encryption enabled

**In Transit:**
- All connections TLS 1.2+
- API endpoints HTTPS only

**Privacy Policy:**
- User data not sold
- LLM calls sent to Gemini (privacy concern)
- Option: Use local Qwen2 for privacy

---

## 7. ALGORITHM DESIGN JUSTIFICATIONS

### 7.1 Why RoBERTa for Emotion Detection?

**Alternatives Considered:**
- Lexicon-based: Fast but inaccurate (F1 ~0.60)
- LSTM: Medium accuracy (F1 ~0.78), slower
- BERT: Good (F1 ~0.85), larger
- RoBERTa: Best (F1 ~0.89), balanced

**Choice:** RoBERTa balances accuracy, speed, and model size

### 7.2 Why BART for Summarization?

**Alternatives:**
- Extractive: Fast but incoherent
- T5: Larger (ROUGE ~41)
- BART: Strong (ROUGE ~42.85), efficient

**Choice:** BART proven on benchmark tasks

### 7.3 Why Sentence-Transformers for Recommendations?

**Alternatives:**
- Word embeddings (Word2Vec): Less semantic
- RoBERTa embeddings: Resource-intensive
- Sentence-Transformers: Efficient, proven

**Choice:** Pre-trained, well-validated

### 7.4 Why MMR for Ranking?

**Alternatives:**
- Pure relevance: Redundant recommendations
- Pure diversity: Lacks specificity
- MMR: Balance (tunable via λ)

**Choice:** λ=0.7 balances relevance/diversity

---

## REFERENCES

[1] See engineering/Architecture.md for technical details

[2] See engineering/HLD.md for module design

[3] See engineering/LLD.md for implementation details

---

**END OF SYSTEM DESIGN**

