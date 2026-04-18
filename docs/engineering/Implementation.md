# IMPLEMENTATION GUIDE
## Pocket Journal — Module-wise Implementation Details

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## IMPLEMENTATION OVERVIEW

This document details how each module is implemented, organized, and maintained.

---

## MODULE 1: AUTHENTICATION & USER MANAGEMENT

### File Structure
```
routes/
  └─ auth.py
services/
  └─ (user management)
```

### Implementation Details

#### routes/auth.py

**Key Functions:**
- `register()` - POST /api/auth/register
- `login()` - POST /api/auth/login
- `verify_token()` - Decorator in app.py

**Dependencies:**
- `firebase_admin` - Authentication
- `flask` - Web framework

**Key Logic:**
```python
# Registration
1. Validate email format (regex)
2. Validate password strength (min 8 chars, mixed case, numbers)
3. Create Firebase user with firebase_admin.auth.create_user()
4. Create Firestore user document
5. Return uid + user object

# Login
1. Accept email + password
2. Firebase handles validation (no direct API for server-side login)
3. Frontend obtains token via Firebase SDK
4. Validate token on subsequent requests using verify_id_token()
```

---

## MODULE 2: JOURNAL ENTRIES

### File Structure
```
routes/
  └─ journal_domain.py
services/
  └─ journal_entries/
     ├─ entry_manager.py
     └─ search_engine.py
persistence/
  └─ db_manager.py
```

### Implementation Details

#### routes/journal_domain.py

**Endpoints:**
- `POST /api/entries` → create_entry()
- `GET /api/entries` → list_entries()
- `GET /api/entries/{id}` → get_entry()
- `PUT /api/entries/{id}` → update_entry()
- `DELETE /api/entries/{id}` → delete_entry()
- `GET /api/entries/search?q=...` → search_entries()

#### services/journal_entries/entry_manager.py

**Key Methods:**
```python
class EntryManager:
    def create_entry(self, uid, title, content, tags):
        # 1. Validate input
        # 2. Generate entry_id (uuid.uuid4())
        # 3. Create document in journal_entries
        # 4. Return entry_id + metadata
    
    def list_entries(self, uid, limit, offset):
        # 1. Query journal_entries WHERE uid=uid
        # 2. Order by created_at DESC
        # 3. Apply pagination
        # 4. Foreach entry, fetch analysis data
        # 5. Return merged entries
    
    def get_entry(self, uid, entry_id):
        # 1. Verify ownership
        # 2. Get journal_entries document
        # 3. Get entry_analysis document
        # 4. Get journal_embeddings document (optional)
        # 5. Merge and return
    
    def update_entry(self, uid, entry_id, updates):
        # 1. Verify ownership
        # 2. Validate new content
        # 3. Update document
        # 4. Trigger re-analysis if content changed
    
    def delete_entry(self, uid, entry_id):
        # 1. Verify ownership
        # 2. Delete from journal_entries
        # 3. Cascade delete from entry_analysis
        # 4. Cascade delete from insight_entry_mapping
        # 5. Delete from journal_embeddings
```

#### Mood Detection Integration

When entry is created or updated, automatically trigger:

```python
def trigger_analysis_pipeline(entry_id, content, uid):
    # Parallel execution
    try:
        # 1. Mood Detection
        predictor = get_predictor()
        mood_result = predictor.predict(content)
        
        # 2. Summarization
        summarizer = get_summarizer()
        summary = summarizer.summarize(content)
        
        # 3. Embeddings
        embedding_svc = get_embedding_service()
        embedding = embedding_svc.embed(content)
        
        # 4. Store Analysis
        analysis_doc = {
            'entry_id': entry_id,
            'summary': summary,
            'mood': mood_result['mood'],
            'primary_mood': mood_result['primary_mood'],
            'confidence': mood_result['confidence'],
            'created_at': datetime.now()
        }
        db.collection('entry_analysis').document().set(analysis_doc)
        
        # 5. Store Embedding
        embedding_doc = {
            'entry_id': entry_id,
            'uid': uid,
            'embedding': embedding,
            'created_at': datetime.now()
        }
        db.collection('journal_embeddings').document().set(embedding_doc)
        
        return True
    except Exception as e:
        logger.error(f"Analysis pipeline failed: {e}")
        # Return entry without analysis; degrade gracefully
        return False
```

---

## MODULE 3: MOOD DETECTION (RoBERTa)

### File Structure
```
ml/
  └─ inference/
     └─ mood_detection/
        └─ roberta/
           ├─ predictor.py
           └─ tokenizer setup (cached)
```

### Implementation Details

#### ml/inference/mood_detection/roberta/predictor.py

```python
class SentencePredictor:
    def __init__(self, model_path: str):
        # Load model from disk
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Move to GPU if available
        self.device = get_device()  # 'cuda' or 'cpu'
        self.model.to(self.device)
        self.model.eval()  # Inference mode
        
        # Class labels (ordered by index)
        self.labels = ['anger', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
    
    def predict(self, text: str) -> dict:
        # 1. Truncate if needed
        text = text[:5000]
        
        # 2. Tokenize
        inputs = self.tokenizer(
            text,
            max_length=128,
            truncation=True,
            padding='max_length',
            return_tensors='pt'
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 3. Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits[0]
        
        # 4. Softmax
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        
        # 5. Extract results
        primary_idx = np.argmax(probs)
        primary_mood = self.labels[primary_idx]
        confidence = float(probs[primary_idx])
        
        # 6. Build output
        mood_dict = {
            label: float(prob)
            for label, prob in zip(self.labels, probs)
        }
        
        return {
            'mood': mood_dict,
            'primary_mood': primary_mood,
            'confidence': confidence
        }
```

**Performance Characteristics:**
- Model Size: ~500MB (fp16)
- Inference Time: 300-500ms per entry
- GPU Memory: ~2GB
- Batch Processing: 32 entries/batch

---

## MODULE 4: INSIGHTS GENERATION

### File Structure
```
services/
  └─ insights_service/
     ├─ insight_generator.py
     └─ llm_backend.py
ml/
  └─ inference/
     └─ insight_generation/
        └─ qwen2/
           └─ predictor.py
```

### Implementation Details

#### services/insights_service/insight_generator.py

```python
class InsightGenerator:
    def generate(self, uid: str, start_date: str, end_date: str):
        # 1. Retrieve entries
        entries = self.db.query_entries(uid, start_date, end_date)
        if len(entries) < 2:
            return self._generic_insights(uid, start_date, end_date)
        
        # 2. Retrieve analysis
        analyses = self._fetch_analyses(entry_ids=[e['id'] for e in entries])
        
        # 3. Aggregate
        mood_dist = self._aggregate_moods(analyses)
        themes = self._extract_themes(entries)
        
        # 4. Build prompt
        prompt = self._build_prompt(entries, analyses, mood_dist, themes)
        
        # 5. Call LLM
        if self.use_gemini:
            response = self._call_gemini(prompt)
        else:
            response = self._call_qwen2(prompt)
        
        # 6. Parse
        insight_dict = self._parse_response(response)
        
        # 7. Store
        insight_id = self._store_insight(uid, start_date, end_date, insight_dict)
        self._create_mappings(insight_id, entry_ids)
        
        return insight_dict
    
    def _build_prompt(self, entries, analyses, mood_dist, themes):
        prompt = f"""
        Analyze the following journal entries from {start_date} to {end_date}.
        
        Summary:
        - Total entries: {len(entries)}
        - Mood distribution: {mood_dist}
        - Common themes: {themes}
        
        Entries:
        {formatted_entries}
        
        Please provide:
        1. Goals identified (title + description)
        2. Progress assessment
        3. Negative behaviors noticed
        4. Remedies/suggestions
        5. Appreciations (strengths)
        6. Conflicts identified
        
        Format as JSON with these exact keys.
        """
        return prompt
```

#### Gemini Backend

```python
def _call_gemini(self, prompt: str) -> str:
    import google.generativeai as genai
    
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    
    response = model.generate_content(
        prompt,
        generation_config={
            'temperature': 0.7,
            'top_p': 0.9,
            'max_output_tokens': 4096,
            'candidate_count': 1
        }
    )
    
    return response.text
```

#### Qwen2 Backend

```python
def _call_qwen2(self, prompt: str) -> str:
    from ml.inference.insight_generation.qwen2.predictor import InsightsPredictor
    
    predictor = self.get_or_load_qwen2()
    response = predictor.generate(prompt, max_new_tokens=4096)
    
    return response
```

---

## MODULE 5: MEDIA RECOMMENDATIONS

### File Structure
```
services/
  └─ media_recommender/
     ├─ recommendation_engine.py
     ├─ providers/
     │  ├─ tmdb_provider.py
     │  ├─ spotify_provider.py
     │  ├─ google_books_provider.py
     │  └─ podcast_provider.py
     ├─ cache_store.py
     └─ ranker.py
routes/
  └─ media_domain.py
```

### Implementation Details

#### services/media_recommender/recommendation_engine.py

**Key Method:**
```python
def recommend(self, uid, mood, media_type, top_k):
    # 1. Cold-start check
    if self._is_cold_start(uid):
        return self._get_popular_items(media_type, top_k)
    
    # 2. Get mood embedding
    mood_emb = self.embedding_svc.get_mood_embedding(mood)
    
    # 3. Fetch candidates (cache or provider)
    candidates = self._fetch_candidates(media_type, mood, limit=200)
    
    # 4. Filter
    candidates = self._filter_duplicates(candidates)
    candidates = self._remove_seen(uid, media_type, candidates)
    candidates = self._apply_popularity_filter(candidates)
    
    # 5. Rank
    if self.config.use_phase5:
        ranked = self._rank_phase5(candidates, mood_emb, uid)
    else:
        ranked = self._rank_basic(candidates, mood_emb)
    
    # 6. Select top K
    results = ranked[:top_k]
    
    # 7. Log interaction (if enabled)
    # Will be logged when user clicks/saves/skips
    
    return results
```

#### Basic Ranking

```python
def _rank_basic(self, candidates, mood_embedding):
    """Simple ranking: similarity + popularity"""
    
    for candidate in candidates:
        # Get or compute embedding
        cand_emb = candidate.get('embedding') or \
                   self.embedding_svc.embed(candidate['description'])
        
        # Similarity
        similarity = self._cosine_similarity(mood_embedding, cand_emb)
        
        # Popularity (normalized 0-100)
        popularity = self._normalize_popularity(candidate['popularity'])
        
        # Combined score
        score = (similarity * 0.9) + (popularity * 0.1)
        candidate['score'] = score
    
    # Sort by score
    candidates_sorted = sorted(candidates, key=lambda x: x['score'], reverse=True)
    
    return candidates_sorted
```

#### Phase 5 Advanced Ranking

```python
def _rank_phase5(self, candidates, mood_embedding, uid):
    """Advanced ranking with MMR, temporal decay, hybrid scoring"""
    
    # Get user interaction history
    interactions = self.db.get_user_interactions(uid)
    
    # Compute scores
    for candidate in candidates:
        # Similarity
        cand_emb = candidate.get('embedding') or self.embedding_svc.embed(...)
        similarity = self._cosine_similarity(mood_embedding, cand_emb)
        
        # Interaction frequency
        interaction_freq = len([i for i in interactions if i['media_id'] == candidate['id']])
        
        # Popularity
        popularity = self._normalize_popularity(candidate['popularity'])
        
        # Recency (temporal decay)
        last_interaction = max([i['timestamp'] for i in interactions if i['media_id'] == candidate['id']], default=None)
        recency = self._compute_temporal_decay(last_interaction) if last_interaction else 0.5
        
        # Hybrid scoring
        hybrid_score = (
            similarity * self.config.hybrid_weights['similarity'] +
            interaction_freq * self.config.hybrid_weights['interaction_frequency'] +
            popularity * self.config.hybrid_weights['popularity'] +
            recency * self.config.hybrid_weights['recency']
        )
        
        candidate['score'] = hybrid_score
    
    # MMR diversification
    if self.config.use_mmr:
        candidates = self._apply_mmr(candidates, mood_embedding)
    
    # Sort
    candidates_sorted = sorted(candidates, key=lambda x: x['score'], reverse=True)
    
    return candidates_sorted
```

---

## MODULE 6: ANALYTICS & STATISTICS

### File Structure
```
services/
  └─ stats_service/
     └─ stats_calculator.py
routes/
  └─ stats.py
```

### Implementation Details

```python
class StatsCalculator:
    def get_overview(self, uid, start_date, end_date):
        entries = self.db.query_entries(uid, start_date, end_date)
        analyses = self.db.query_analyses(entry_ids=[...])
        
        return {
            'total_entries': len(entries),
            'avg_length': np.mean([len(e['content']) for e in entries]),
            'mood_distribution': self._calc_mood_dist(analyses),
            'entries_per_day': len(entries) / days_in_range,
            'writing_patterns': self._calc_patterns(entries),
            'mood_trend': self._calc_trend(analyses),
            'current_streak': self._calc_streak(uid)
        }
    
    def _calc_mood_dist(self, analyses):
        moods = [a['primary_mood'] for a in analyses]
        return dict(Counter(moods))
    
    def _calc_trend(self, analyses):
        # Linear regression: mood_score ~ days
        dates = [a['created_at'].day for a in analyses]
        scores = [a['confidence'] for a in analyses]
        
        # numpy.polyfit
        coeffs = np.polyfit(dates, scores, 1)
        slope = coeffs[0]  # m in y = mx + b
        
        return {
            'direction': 'improving' if slope > 0.05 else 'declining' if slope < -0.05 else 'stable',
            'slope': slope
        }
```

---

## MODULE 7: DATA EXPORT

### File Structure
```
services/
  └─ export_service/
     ├─ export_manager.py
     ├─ csv_exporter.py
     ├─ json_exporter.py
     └─ pdf_exporter.py
routes/
  └─ export_route.py
```

### Implementation Example (CSV)

```python
def export_csv(self, uid, start_date, end_date):
    # 1. Query entries
    entries = self.db.query_entries(uid, start_date, end_date)
    
    # 2. Build DataFrame
    data = []
    for entry in entries:
        analysis = self.db.get_analysis(entry['id'])
        data.append({
            'date': entry['created_at'].strftime('%Y-%m-%d'),
            'title': entry.get('title', ''),
            'mood': analysis['primary_mood'],
            'confidence': analysis['confidence'],
            'content': entry['content'],
            'summary': analysis['summary'],
            'tags': ';'.join(entry.get('tags', []))
        })
    
    df = pd.DataFrame(data)
    
    # 3. Export to CSV
    csv_data = df.to_csv(index=False, quotechar='"', quoting=csv.QUOTE_ALL)
    
    return csv_data.encode('utf-8')
```

---

## DEPLOYMENT & CONTAINER SETUP

### Docker Setup

**Dockerfile Key Sections:**
```dockerfile
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Install Python 3.10
RUN apt-get update && apt-get install -y python3.10

# Set working directory
WORKDIR /app

# Copy requirements
COPY Backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY Backend/ /app/

# Download models at startup (optional)
RUN python -c "from ml.inference.mood_detection.roberta import SentencePredictor; predictor = SentencePredictor('/path/to/models')"

# Expose port
EXPOSE 8080

# Run Flask app
CMD ["python", "app.py"]
```

---

**END OF IMPLEMENTATION GUIDE**

