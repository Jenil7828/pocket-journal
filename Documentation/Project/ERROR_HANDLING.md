# Error Handling & Recovery: Pocket Journal Backend

## Error Hierarchy

```
Error
├── HTTP Errors (4xx, 5xx)
├── ML Errors (Model Unavailable, OOM)
├── Provider Errors (API failures, rate limits)
├── Database Errors (Connection, quota)
└── Validation Errors (Input, schema)
```

---

## HTTP Error Responses

All errors return JSON with consistent format:

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "timestamp": "2026-03-29T10:30:00Z",
  "request_id": "unique_id_for_tracing"  // optional
}
```

### Error Code Reference

| Code | Status | Cause | Recovery |
|------|--------|-------|----------|
| `invalid_input` | 400 | Validation failed | Review request format |
| `missing_field` | 400 | Required field missing | Add missing field |
| `unauthorized` | 401 | Invalid/expired token | Refresh Firebase token |
| `forbidden` | 403 | User not permitted | Verify authorization |
| `not_found` | 404 | Resource doesn't exist | Check resource ID |
| `conflict` | 409 | Resource already exists | Use existing resource |
| `rate_limited` | 429 | Quota exceeded | Retry after backoff |
| `server_error` | 500 | Internal error | Retry or contact support |
| `unavailable` | 503 | Service degraded | Retry or use fallback |

---

## ML Inference Error Handling

### Mood Detection Failures

**Scenario**: RoBERTa model fails to load or crashes

**Detection**:
```python
try:
    mood_result = predictor.predict(text)
except Exception as e:
    logger.error("Mood detection failed: %s", str(e))
    # Fallback
```

**Recovery Strategy**:
1. **Immediate Fallback**: Return neutral mood
   ```json
   {
     "dominant_mood": "neutral",
     "confidence": 0.0,
     "note": "Mood detection unavailable; defaulting to neutral"
   }
   ```

2. **Cache Fallback**: Use previous entry's mood (if available)
   ```python
   if not mood_result:
       last_analysis = db.fetch_latest_analysis(uid)
       if last_analysis:
           mood_result = last_analysis.get("mood")
   ```

3. **Manual User Input**: Prompt user to specify mood (frontend)

**Prevention**:
- Health checks on model loading at startup
- Monitor GPU memory and OOM errors
- Implement circuit breaker (disable inference after N failures)

### Summarization Failures

**Scenario**: BART model memory error or timeout

**Detection**:
```python
try:
    summary = summarizer.summarize(text, max_length=128)
except Exception as e:
    logger.warning("Summarization failed: %s", str(e))
    # Fallback
```

**Recovery Strategy**:
1. **Truncate & Retry**: Reduce input length
   ```python
   if len(text) > 512:
       text = text[:512]  # Truncate
       summary = summarizer.summarize(text)
   ```

2. **Generic Fallback**: Extract first N words
   ```python
   summary = " ".join(text.split()[:30]) + "..."  # ~200 chars
   ```

3. **Log & Continue**: Store placeholder, alert ops
   ```python
   summary = "Entry recorded. Summarization temporarily unavailable."
   logger.error("Summarization failed for entry %s", entry_id)
   alert_ops("summarizer_down")
   ```

**Prevention**:
- Memory limits: `torch.cuda.set_per_process_memory_fraction(0.8)`
- Timeout: Wrap in timeout decorator
- Batch limiting: Process one entry at a time

### Embeddings Generation Failures

**Scenario**: sentence-transformers model unavailable

**Recovery**:
1. **Zero Vector**: Return 768-dim zero vector (safe but ineffective)
   ```python
   embedding = [0.0] * 768
   ```

2. **Random Vector**: Generate random normalized vector (worse alternative)
   ```python
   embedding = np.random.randn(768)
   embedding /= np.linalg.norm(embedding)
   ```

3. **Retry Later**: Queue for async processing
   ```python
   queue_for_retry(entry_id, "embeddings", priority="high")
   ```

**Prevention**:
- Pre-load model at startup (fail-fast)
- Monitor GPU memory
- Test embedding service in health checks

---

## Provider API Error Handling

### Network Errors

**Scenario**: External API unreachable (TMDb, Spotify, Google Books)

**Retry Strategy** (Exponential Backoff):
```python
attempt = 0
max_retries = 1  # Single retry (config: API_REQUEST_MAX_RETRIES)
backoff = [0, 2]  # Seconds to wait

while attempt <= max_retries:
    try:
        response = requests.get(url, timeout=10)  # API_REQUEST_TIMEOUT
        if 200 <= response.status_code < 300:
            return response.json()
    except requests.exceptions.Timeout:
        attempt += 1
        if attempt <= max_retries:
            time.sleep(backoff[attempt])
    except requests.exceptions.ConnectionError:
        attempt += 1
        if attempt <= max_retries:
            time.sleep(backoff[attempt])

# After retries exhausted
raise RuntimeError("Provider unavailable after retries")
```

**Response to Client**:
- If cache available: Return cached results (stale-while-revalidate)
- If no cache: Return 503 Service Unavailable

### Rate Limiting (429)

**Scenario**: Provider quota exceeded

**Detection**:
```python
if response.status_code == 429:
    retry_after = response.headers.get("Retry-After", 60)
    logger.warning("Rate limited by %s. Retry after %s seconds", provider, retry_after)
    return None  # Signal caller to use cache
```

**Strategy**:
1. **Don't retry immediately** (429 indicates quota)
2. **Use cache**: Serve stale results to user
3. **Backoff**: Implement request throttling
   ```python
   provider_last_request = {}
   min_interval = 1  # seconds between requests per provider
   
   if time.time() - provider_last_request.get(provider, 0) < min_interval:
       time.sleep(min_interval)
   provider_last_request[provider] = time.time()
   ```
4. **Alert ops** if rate limiting persists

**Prevention**:
- Monitor request counts per provider
- Implement request queuing
- Set up API quota alerts
- Cache aggressively (max_age_hours=24)

### Unauthorized (401)

**Scenario**: API key invalid or expired

**Response**:
```python
if response.status_code == 401:
    logger.error("Unauthorized access to %s. Check API key.", provider)
    raise UnauthorizedError("Invalid API credentials")
```

**Recovery**:
1. **Rotate key** (manual action required)
2. **Use fallback provider** if available
3. **Return 500** to client (don't expose API key issue)

**Prevention**:
- Validate API keys at startup
- Monitor for 401 errors
- Implement key rotation schedule

### Server Errors (5xx)

**Scenario**: Provider experiencing outages

**Retry Strategy**:
```python
if 500 <= response.status_code < 600:
    attempt += 1
    if attempt <= max_retries:
        backoff_seconds = 2 ** attempt  # Exponential: 2, 4
        logger.warning("Server error %s. Retry in %s seconds", 
                       response.status_code, backoff_seconds)
        time.sleep(backoff_seconds)
    else:
        raise RuntimeError(f"Provider returned {response.status_code} after retries")
```

**Client Response**:
- Use cache if available
- Return 503 if no cache

---

## Database Errors

### Connection Failures

**Scenario**: Firestore connection lost

**Firebase Admin SDK Handling** (automatic):
```python
# Firebase SDK retries with exponential backoff (built-in)
# Default: 5 retries, up to 32 seconds total
try:
    doc = db.collection("journal_entries").document(entry_id).get()
except Exception as e:
    logger.error("Firestore connection failed: %s", str(e))
    # Propagate to client
    return {"error": "Database unavailable"}, 503
```

**Recovery**:
1. **Wait & retry** (let SDK handle internally)
2. **Circuit breaker**: If multiple failures, fail-fast
   ```python
   if consecutive_db_failures > 3:
       logger.error("Database circuit breaker activated")
       return {"error": "Database service degraded"}, 503
   ```

### Quota Exceeded

**Scenario**: User or project hits Firestore quota

**Detection**:
```
com.google.firebase.firestore.FirestoreException: 
  (RESOURCE_EXHAUSTED): "Quota exceeded for quota metric..."
```

**Response to Client**:
```json
{
  "error": "quota_exceeded",
  "message": "Service temporarily unavailable due to quota limits",
  "status": 429
}
```

**Recovery**:
1. **Client-side retry** (with exponential backoff)
   ```javascript
   // Client code
   fetch(url, {retries: 5, backoff: exponential})
   ```
2. **Server-side throttling** (rate limit requests)
3. **Upgrade quota** (if production)

### Duplicate Key Errors

**Scenario**: Document already exists

**Handling**:
```python
try:
    doc_ref.set(data)
except AlreadyExistsError:
    # Update instead of create
    doc_ref.update(data)
```

---

## Validation Errors

### Input Validation

**Scenario**: Missing or malformed request fields

```python
# Validate entry_text
if not data.get("entry_text", "").strip():
    return {"error": "invalid_input", 
            "message": "entry_text is required and cannot be empty"}, 400

# Validate date range
try:
    start = datetime.fromisoformat(data["start_date"])
    end = datetime.fromisoformat(data["end_date"])
except ValueError:
    return {"error": "invalid_input", 
            "message": "Dates must be ISO format (YYYY-MM-DD)"}, 400

if start > end:
    return {"error": "invalid_input", 
            "message": "start_date must be before end_date"}, 400
```

**User-Friendly Error Messages**:
- ❌ `"Invalid JSON in request body"`
- ✅ `"Request must contain 'entry_text' field with non-empty string"`

### Schema Validation

**Scenario**: Firestore document doesn't match expected schema

```python
def validate_entry_schema(doc):
    required_fields = ["uid", "entry_text", "created_at"]
    if not all(field in doc for field in required_fields):
        logger.error("Invalid entry schema: missing fields")
        return False
    if not isinstance(doc["entry_text"], str):
        logger.error("Invalid entry schema: entry_text must be string")
        return False
    return True
```

---

## Fallback Strategies

### Media Recommendations Fallback Chain

```
Cache hit?
  ├─ YES: Serve cached results
  └─ NO: Query live provider
       ├─ Success: Rank and return
       ├─ Rate limited (429): Serve empty array + cache advice
       ├─ Server error (5xx): Retry once
       │    ├─ Success: Return results
       │    └─ Fail: Serve empty array
       └─ Connection error: Serve empty array
```

**Client Implementation**:
```json
{
  "recommendations": [],
  "fallback_reason": "provider_unavailable",
  "status": "degraded"
}
```

### Insights Generation Fallback Chain

```
Qwen2 (local)?
  ├─ Success: Return structured insights
  └─ Failure (OOM, timeout, not available)
       └─ Gemini (cloud)?
           ├─ Success: Return insights
           └─ Failure (no API key, rate limited, unavailable)
               └─ Generic template with mood summary only
```

**Generic Template Fallback**:
```json
{
  "emotional_state": "Your mood distribution over this period was: {distribution}",
  "goals": ["Continue journaling consistently"],
  "progress": "You logged {count} entries during this period.",
  "note": "Advanced insights currently unavailable. Check back soon."
}
```

---

## Logging Strategy

### Log Levels by Severity

| Level | When to Use | Example |
|-------|-----------|---------|
| DEBUG | Detailed troubleshooting | Cache hit count, embedding dimensions |
| INFO | Normal operation milestones | Entry created, analysis complete |
| WARNING | Recoverable issues | Provider rate limited, fallback triggered |
| ERROR | Serious problems | Model crash, API key invalid |
| CRITICAL | Service breaking | Firebase auth failed at startup |

### Log Format

```
[timestamp] [level] [module]: [message]

Examples:
[2026-03-29 10:30:00] INFO pocket_journal.routes.entries: Created entry doc_id_123 for uid_456
[2026-03-29 10:30:01] WARNING pocket_journal.ml.inference: Mood detection latency 523ms (threshold 500ms)
[2026-03-29 10:30:02] ERROR pocket_journal.providers.tmdb: HTTP 429 from TMDb. Rate limited.
```

### Structured Logging (JSON in Production)

```json
{
  "timestamp": "2026-03-29T10:30:00Z",
  "level": "ERROR",
  "module": "providers.tmdb",
  "message": "API call failed",
  "error_code": "429",
  "retry_count": 1,
  "user_id": "uid_456",
  "request_id": "req_789"
}
```

### Logging Critical Paths

**Entry Creation**:
```python
logger.info("Entry creation initiated: uid=%s, length=%d", uid, len(text))
logger.info("Mood detection completed: mood=%s, confidence=%.2f", mood, conf)
logger.info("Summarization completed: length=%d", len(summary))
logger.info("Entry finalized: entry_id=%s, analysis_stored=true", entry_id)
```

**Recommendations**:
```python
logger.info("Recommendation request: media_type=%s, uid=%s", media_type, uid)
logger.debug("Cache query returned %d results", len(cache_results))
logger.warning("Cache miss. Falling back to provider.", extra={"source": "live"})
logger.info("Recommendation completed: results=%d, source=%s", len(results), source)
```

---

## Circuit Breaker Pattern

Prevent cascading failures by disabling services temporarily:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout_seconds=300):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failures = 0
        self.last_failure_time = None
        self.state = "closed"  # closed | open | half-open
    
    def call(self, func, *args):
        if self.state == "open":
            # Check if timeout elapsed
            if time.time() - self.last_failure_time > self.timeout_seconds:
                self.state = "half-open"
            else:
                raise RuntimeError(f"Circuit breaker open. Try again in {self.timeout_seconds}s")
        
        try:
            result = func(*args)
            if self.state == "half-open":
                self.state = "closed"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            if self.failures >= self.failure_threshold:
                self.state = "open"
                logger.error("Circuit breaker opened after %d failures", self.failures)
            raise

# Usage
mood_breaker = CircuitBreaker(failure_threshold=3)
try:
    mood = mood_breaker.call(predictor.predict, text)
except RuntimeError:
    mood = "neutral"  # Fallback
```

---

## Monitoring & Alerting

### Key Metrics to Monitor

```
1. Error Rate (% of requests failing)
2. Latency (p50, p95, p99)
3. ML Model Availability (% uptime)
4. Provider API Health (response codes)
5. Database Quota Usage
6. Cache Hit Rate
```

### Alert Conditions

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Error rate | > 5% for 5 min | Page on-call |
| Model latency | > 3s p99 | Investigate GPU |
| Cache hit rate | < 50% | Review cache TTL |
| Provider 429s | > 10/min | Throttle requests |
| DB quota | > 80% | Scale up |

---

## Recovery Runbooks

### Mood Model Crashes

1. Check GPU memory: `nvidia-smi`
2. Restart service: `docker restart pocket-journal-api`
3. If persists: Upgrade GPU memory or reduce batch size
4. Monitor: Watch error logs for recurrence

### Firestore Connection Lost

1. Check Firebase project status: Firebase Console
2. Verify network connectivity: `curl https://firestore.googleapis.com`
3. Validate credentials: Check FIREBASE_CREDENTIALS_PATH
4. Restart service if credentials updated

### Provider Rate Limited

1. Check current quota: Provider console (TMDb, Spotify, Google)
2. Increase cache TTL: `MEDIA_CACHE_MAX_AGE_HOURS=48`
3. Reduce recommendation frequency: Educate users
4. Upgrade API tier if available


