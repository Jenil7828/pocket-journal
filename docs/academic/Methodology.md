# METHODOLOGY
## Experimental Design,Algorithm Specification, and Validation Approach

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## 1. RESEARCH METHODOLOGY

### 1.1 Research Design

This work employs a **systems research methodology** combining:
- **Algorithmic development:** Selection and fine-tuning of pre-trained models
- **System engineering:** Integration of multiple components into production system
- **Empirical evaluation:** Performance measurement on specified metrics
- **User validation:** Testing with representative user interactions

### 1.2 Data Sources

**Training Data:**
- Pre-trained models (RoBERTa, BART) trained on large public corpora
- No custom training data created
- Transfer learning from general domain to journaling domain

**Evaluation Data:**
- Internal test set: 500 journal entries
- Derived from public sources and synthetic generation
- Labeled for emotion ground truth

**System Validation:**
- Load testing: Simulated 1000+ concurrent users
- Latency testing: Time all key operations
- Reliability testing: Uptime and error rates

---

## 2. ALGORITHM SPECIFICATION

### 2.1 RoBERTa for Emotion Detection

**Architecture:**
- Transformer encoder with 12 layers
- 768 hidden dimensions, 12 attention heads
- 110M parameters total

**Input:**
- Text sequence (max length 128 tokens)

**Processing:**
1. Tokenization: BPE tokenizer, truncation to 128 tokens
2. Embedding layer: Token embeddings + positional embeddings
3. 12 transformer encoder layers:
   - Multi-head self-attention (12 heads)
   - Feed-forward (3072 hidden)
   - Layer normalization
4. Output:  Sequence of 768-dim contextual representations
5. Classification: Linear layer (768 → 7 classes)
6. Softmax: Convert logits to probability distribution

**Output:**
- Probability vector [p_anger, p_disgust, p_fear, p_happy, p_neutral, p_sad, p_surprise]
- Primary emotion: argmax(probabilities)
- Confidence: max(probabilities)

**Hyperparameters:**
- learning_rate: 2e-5 (from original BERT)
- batch_size: 32
- num_epochs: 3
- optimizer: AdamW
- warmup_steps: 500

---

### 2.2 BART for Abstractive Summarization

**Architecture:**
- Encoder-decoder transformer
- Encoder: 12 layers, 768 hidden, 12 heads (BERT-like)
- Decoder: 12 layers, 768 hidden, 12 heads (GPT-like)
- 400M parameters total

**Input:**
- Text sequence (max length 1024 tokens)

**Processing:**
1. Tokenization: BPE tokenizer, truncation to 1024 tokens
2. Encoder:
   - Process input with bidirectional attention
   - Generate contextual representations
3. Decoder (autoregressive generation):
   - Start token: [BOS]
   - Generate one token at a time
   - Use encoder output for cross-attention
   - Beam search: Track top-4 hypotheses (num_beams=4)
   - Length controls: min_length=20, max_length=128
   - Early stopping: Stop if any beam completes

**Output:**
- Generated summary text (20-128 tokens)
- Detokenized to human-readable string

**Hyperparameters:**
- num_beams: 4
- max_length: 128
- min_length: 20
- length_penalty: 1.0
- early_stopping: True

**Fallback:**
- If inference fails: Truncate to first 128 tokens

---

### 2.3 Sentence-Transformers for Embeddings

**Architecture:**
- Siamese transformer network
- Pre-trained model: all-mpnet-base-v2
- Based on RoBERTa-base

**Input:**
- Text sequence (doc or sentence)

**Processing:**
1. Pass through BERT-like encoder
2. Mean pooling over token sequence → sentence vector (384-dim)
3. Normalize to unit length (L2 norm)

**Output:**
- 384-dimensional embedding vector
- Normalized: ||embedding|| = 1

**Similarity:**
```
similarity(u, v) = u · v  (dot product, normalized vectors)
```

---

### 2.4 Recommendation Ranking Algorithm

**Input:**
- User mood (string): "happy", "sad", etc.
- Media type: "movie", "music", "book"
- Target count (k): desired number of recommendations

**Processing:**

Step 1: Cold-start check
```
IF num_entries[user] < 3:
  RETURN popular_items(media_type, k)
```

Step 2: Candidate generation
```
candidates = media_cache[mood][media_type]
IF not candidates OR age > 24h:
  candidates = provider_api.search(mood, media_type)
  cache(mood, media_type, candidates)
```

Step 3: Filtering
```
FOR each candidate in candidates:
  IF duplicate OR user_seen OR popularity < threshold:
    REMOVE
```

Step 4: Ranking
```
mood_emb = encode(mood)
FOR each candidate c:
  sim[c] = cosine(mood_emb, c.embedding)
  pop[c] = normalize(c.popularity, 0, 100)
  score[c] = sim[c] × 0.9 + pop[c] × 0.1

SORT candidates BY score DESC
RETURN candidates[0:k]
```

Step 5 (Optional): MMR Diversification
```
selected = []
WHILE len(selected) < k:
  IF selected IS EMPTY:
    selected.append(candidates[0])
  ELSE:
    FOR each c NOT IN selected:
      rel[c] = score[c]
      diversity[c] = MIN(cosine(c.emb, s.emb) for s in selected)
      mmr[c] = 0.7 × rel[c] - 0.3 × diversity[c]
    best = argmax_c(mmr[c])
    selected.append(best)
RETURN selected
```

---

## 3. EVALUATION METHODOLOGY

### 3.1 Emotion Detection Evaluation

**Metric: F1-Score**

```
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × (Precision × Recall) / (Precision + Recall)
```

**Procedure:**
1. Collect 500 journal entries
2. Label with ground-truth emotion (manual annotation)
3. Run RoBERTa model on each entry
4. Compare predicted vs ground truth
5. Calculate F1 for each emotion class
6. Report macro-average F1

**Target:** F1 ≥ 0.85

---

### 3.2 Summarization Evaluation

**Metric: ROUGE-L**

```
ROUGE-L = (1 + β²) × (Precision × Recall) / (β² × Precision + Recall)
where β = 1 (equal weight)
```

- Longest common subsequence between reference and generated
- Range: 0-1 (higher is better)
- Less strict than ROUGE-1 (word overlap)

**Procedure:**
1. Collect 100 entries with reference summaries
2. Generate summaries with BART
3. Calculate ROUGE-L (reference vs generated)
4. Report average ROUGE-L

**Target:** ROUGE-L ≥ 0.40

---

### 3.3 System Performance Evaluation

**Metrics:**
- **Latency (p95):** 95th percentile response time
- **Throughput:** Requests per second
- **Scalability:** Max concurrent users

**Procedure:**
1. Load test with 1000 concurrent users
2. Measure response time distribution
3. Identify bottleneck (database vs inference)
4. Calculate p50, p95, p99 latencies

**Targets:**
- p95 < 2000ms
- Throughput > 100 req/s
- 1000+ concurrent users

---

### 3.4 Recommendation Evaluation

**Metric: Precision @10**

```
Precision@10 = (# relevant items in top-10) / 10
```

- Relevance determined by user interaction (click, save)
- A/B test: Basic vs Phase 5 ranking

**Procedure:**
1. Deploy baseline recommender
2. Collect user interactions for 100 users
3. Measure click-through rate (CTR)
4. Deploy Phase 5 ranking
5. Compare CTR improvement

**Target:** ≥3% CTR improvement with Phase 5

---

## 4. IMPLEMENTATION CHOICES

### 4.1 Framework Selection: Flask

**Rationale:**
- Lightweight (vs FastAPI overhead for this use case)
- Mature ecosystem  
- Good PyTorch/TensorFlow integration
- Suitable for serving models via REST

### 4.2 Database: Firestore

**Rationale:**
- Fully managed (no DevOps overhead)
- Real-time capabilities (future subscriptions)
- Built-in security rules
- Scales automatically
- Geographic distribution

### 4.3 Model Serving: Native PyTorch

**Rationale:**
- Direct inference (no TensorFlow converter needed)
- Efficient memory usage
- Full control over batch processing
- GPU support straightforward

---

## REFERENCES

[1] Devlin, J., et al. (2019). BERT: Pre-training of deep bidirectional transformers for language understanding. In *NAACL* (pp. 4171-4186).

[2] Lewis, M., et al. (2020). BART: Denoising sequence-to-sequence pre-training for natural language generation, translation, and comprehension. In *ACL*.

[3] Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using siamese BERT-networks. In *EMNLP*.

[4] Carbonell, J., & Goldstein, J. (1998). The use of MMR, diversity-based reranking for reordering documents and producing summaries. In *SIGIR*.

---

**END OF METHODOLOGY**

