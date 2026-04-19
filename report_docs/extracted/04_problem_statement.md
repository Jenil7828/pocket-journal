# 📋 Problem Statement

## Core Problem 1: Automated Emotion Tracking from Unstructured Text

### The Problem
- Users want to track emotional patterns over time in their journal
- Manual mood selection is cumbersome and breaks the stream of consciousness
- Raw text entries contain rich emotional information that is difficult to extract manually
- Current journaling apps require explicit mood tagging, creating friction

### Solution Implemented
- **RoBERTa Fine-Tuned Model** (v2, fp16 optimized)
  - Automatically classifies emotions in journal entries
  - 7-dimensional emotion output: anger, disgust, fear, happy, neutral, sad, surprise
  - Multi-label classification (entries can contain multiple emotions)
  - Probability-based output (0-1) with configurable threshold (default 0.25)
  
- **Inference Pipeline**
  - Input: Raw journal entry text (up to 512 tokens)
  - Process: Tokenization → Model → Sigmoid probability
  - Output: `{"probabilities": {"anger": 0.1, "happy": 0.8, ...}, "predictions": {...}}`
  - Latency: <500ms per entry (GPU), <2s (CPU)

- **User Configuration**
  - Per-user setting: `users.settings.mood_tracking_enabled` (boolean)
  - Default enabled globally via `config.mood_tracking_enabled_default`
  - Users can disable mood tracking if they prefer

## Core Problem 2: Information Overload in Long Entries

### The Problem
- Journal entries range from 100 to 5000+ words
- Users want quick summaries without re-reading entire entries
- No standard format for entry structure (prose, bullets, mixed)
- Summarization must preserve emotional and semantic meaning

### Solution Implemented
- **BART-Large-CNN Fine-Tuned Model** (v2, fp16 optimized)
  - Abstractive summarization (not just extraction)
  - Produces human-quality summaries from varied input formats
  - Output length: 20-128 tokens (configurable)
  - Beam search (num_beams=4) for quality
  
- **Summarization Pipeline**
  - Input: Raw entry text (max 1024 tokens)
  - Process: Tokenization → Seq2Seq model → Beam search (4 beams)
  - Output: Coherent 1-2 sentence summary
  - Fallback: Truncate to 200 chars if BART unavailable
  
- **Integration Points**
  - Called during entry creation: `entry_create.py:process_entry()`
  - Output stored in `entry_analysis.summary` collection
  - Full summary always returned in API responses
  - Used as input for embed ding generation

## Core Problem 3: Context-Aware Media Recommendations

### The Problem
- Generic recommendation systems ignore emotional context
- User taste changes based on mood (sad might prefer uplifting movies)
- Current users have diverse media preferences (movies, music, books, podcasts)
- Static recommendations become stale and repetitive

### Solution Implemented
- **Intent Builder** (Context Aggregation)
  - Extracts emotional intent from recent journal entries
  - Builds 384-dimensional intent vector combining:
    - Entry embeddings (summarized journal text)
    - User taste vector (historical preference profile)
    - Mood distribution from recent entries
  - Output: Contextual user embedding for ranking
  
- **Unified Recommendation Pipeline**
  - **Step 1 - Candidate Fetching**
    - Fetch ~300-500 items from media cache (Firestore)
    - Cache populated from TMDb, Spotify, Google Books APIs
    - Supports movies, songs, books, podcasts
  
  - **Step 2 - Hard Filtering**
    - Genre filter (if provided): keep items in requested genres
    - Search filter: fuzzy text matching on title/description
    - Mood filter: pre-tagged content matching emotional context
    - Language filter (songs/podcasts): prefer user's language
  
  - **Step 3 - Personalized Ranking**
    - Compute cosine similarity between intent vector and each candidate
    - Phase 5 Advanced Ranking:
      - **Maximal Marginal Relevance (MMR)**: λ=0.7 diversity vs relevance
      - **Temporal Decay**: Reduce score of old user interactions (-15% per day)
      - **Hybrid Scoring**: Blend similarity (50%), interaction frequency (20%), popularity (20%), recency (10%)
  
  - **Step 4 - Sorting**
    - Options: default (relevance), rating, trending, recent
    - Applied after ranking before pagination
  
  - **Step 5 - Pagination & Response**
    - Return paginated results (default 10, max 100)
    - Strip internal fields (embeddings, similarity scores)
    - Response normalized to consistent schema

## Core Problem 4: Personalized Insights from Patterns

### The Problem
- Users cannot manually identify patterns across dozens of journal entries
- Behavioral insights require cross-entry analysis and synthesis
- Goal tracking is manual and fragmented
- Conflict identification and resolution strategies are not suggested

### Solution Implemented
- **Insights Generation Pipeline**
  - **Input**: Journal entries from date range (start_date to end_date)
  - **Processing**:
    1. Fetch all entries in date range
    2. Extract mood profiles and entry summaries
    3. Send to LLM (Gemini or Qwen2) with structured prompt
    4. Parse response into structured format
  
  - **Gemini Backend** (Production Default)
    - Model: Gemini 2.0 Flash
    - Speed: <2 seconds per request
    - Capabilities: Advanced reasoning, nuanced understanding
    - Fallback: Qwen2 if Gemini fails
  
  - **Qwen2 Local Backend** (Offline Capable)
    - Model: Qwen2-1.5B-Instruct
    - Parameters: 1.5 billion
    - Inference: Via HuggingFace or Ollama
    - Max tokens: 4096, temperature: 0.7
  
  - **Output Structure**:
    ```json
    {
      "goals": [{"title": "Exercise", "description": "Daily morning runs"}],
      "progress": "Good progress on fitness routine",
      "negative_behaviors": "Late night scrolling affecting sleep",
      "remedies": "Set phone curfew at 10 PM",
      "appreciation": "Consistent waking times improving",
      "conflicts": "Work deadlines vs personal time",
      "raw_response": "Full LLM response"
    }
    ```

## Core Problem 5: Fast Entry Search and Discovery

### The Problem
- Users have hundreds of entries but struggle to find specific ones
- Keyword search misses semantic relationships
- Date-based filtering is tedious
- Users want to find entries by emotional content, not just keywords

### Solution Implemented
- **Semantic Search with Embeddings**
  - Model: All-MpNet-Base-V2 (384 dimensions, 110M parameters)
  - Embedding generated for each entry summary at creation time
  - Stored in `journal_embeddings` collection with uid, entry_id, timestamp
  
  - **Search Types**:
    1. Full-text: Query matching in title, text, summary (case-insensitive)
    2. Semantic: Vector similarity search (not currently exposed via API)
    3. Combined: Filter by date range + text matching
  
  - **Current Implementation** (journal_domain.py:search_journal_entries)
    - Query parameter: `query` (text search)
    - Filter parameters: `start_date`, `end_date` (YYYY-MM-DD format)
    - Result limit: 1-50 items
    - Sort: by created_at descending
    - Matching: Simple substring match on entry_text, summary, title

## Design Decisions and Trade-offs

| Problem | Approach | Rationale | Trade-off |
|---------|----------|-----------|-----------|
| Emotion Tracking | RoBERTa multi-label | Automatic, multi-dimensional | Cannot capture context nuance |
| Summarization | Abstractive BART | Preserves semantic meaning | May lose specific details |
| Recommendations | Intent vector + ranking | Context-aware, diverse | Requires continuous model updates |
| Insights | LLM with Gemini default | Fast, high quality | Monthly API costs |
| Search | Text + semantic ready | Full-text covers 90% of use cases | Semantic search not exposed yet |

## Constraints and Assumptions

### Constraints
- Entry text limited to 5000 characters
- Maximum 100 entries returned per API call
- Model inference limited to 2 seconds per entry
- Recommendation diversity: no duplicates >5% of results

### Assumptions
- Users have Firebase-configured auth
- Models are pre-downloaded or available at startup
- Firestore is always available (no offline sync)
- User taste vectors are maintained by recommendation engine

