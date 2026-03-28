# Testing: Pocket Journal Backend

## Testing Strategy

```
Test Pyramid:
           ▲
          / \
         /   \  E2E Tests (5%)
        /     \  - Full flow (Postman)
       /-------\
      /         \
     /           \ Integration Tests (20%)
    /             \ - Service interactions
   /               \ - External APIs
  /-----------------\
 /                   \
/                     \ Unit Tests (75%)
/                       \ - Individual functions
/_________________________\ - Mocks for dependencies
```

---

## Unit Testing Strategy

### Framework: pytest

**Setup**:
```bash
pip install pytest pytest-mock pytest-cov
```

### Test Structure

```
Backend/
├── tests/
│   ├── conftest.py               # Shared fixtures
│   ├── test_routes/
│   │   ├── test_auth.py
│   │   ├── test_entries.py
│   │   ├── test_media.py
│   │   └── test_insights.py
│   ├── test_services/
│   │   ├── test_embedding.py
│   │   ├── test_recommendations.py
│   │   └── test_search.py
│   └── test_ml/
│       ├── test_mood_detection.py
│       ├── test_summarization.py
│       └── test_insights_generation.py
```

### Example Test: Entry Creation

```python
# tests/test_routes/test_entries.py

import pytest
from unittest.mock import Mock, patch

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_token(mocker):
    # Mock Firebase token verification
    mocker.patch("firebase_admin.auth.verify_id_token", 
                 return_value={"uid": "test_uid_123"})
    return "valid_token"

def test_create_entry_success(client, auth_token, mocker):
    """Test successful entry creation with mood + summary"""
    
    # Mock dependencies
    mocker.patch("app.get_db").return_value = Mock(
        insert_entry=Mock(return_value="entry_123"),
        insert_analysis=Mock()
    )
    mocker.patch("app.get_predictor").return_value = Mock(
        predict=Mock(return_value={
            "dominant": "happy",
            "probabilities": {"happy": 0.85, "neutral": 0.10, ...}
        })
    )
    mocker.patch("app.get_summarizer").return_value = Mock(
        summarize=Mock(return_value="Today was a great day.")
    )
    
    # Request
    response = client.post(
        "/api/v1/entries",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"entry_text": "Today was a great day..."}
    )
    
    # Assertions
    assert response.status_code == 201
    assert response.json["entry_id"] == "entry_123"
    assert response.json["analysis"]["mood"] == "happy"
    assert response.json["analysis"]["summary"] == "Today was a great day."

def test_create_entry_validation_error(client, auth_token):
    """Test entry validation failure"""
    
    response = client.post(
        "/api/v1/entries",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"entry_text": ""}  # Empty text
    )
    
    assert response.status_code == 400
    assert "error" in response.json

def test_create_entry_mood_detection_failure(client, auth_token, mocker):
    """Test fallback when mood detection fails"""
    
    mocker.patch("app.get_db").return_value = Mock()
    mocker.patch("app.get_predictor").side_effect = Exception("Model error")
    
    response = client.post(
        "/api/v1/entries",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"entry_text": "Test entry"}
    )
    
    # Should fallback to neutral mood
    assert response.status_code == 201
    assert response.json["analysis"]["mood"] == "neutral"
    assert response.json["analysis"].get("note") is not None
```

### Key Test Cases

#### Authentication Tests
```
✓ Valid JWT token accepted
✓ Missing token returns 401
✓ Expired token returns 401
✓ Invalid signature returns 401
✓ User can only access own data
```

#### Validation Tests
```
✓ Missing required fields return 400
✓ Invalid data types return 400
✓ Oversized payload returns 413
✓ SQL injection attempts sanitized
✓ XSS payloads escaped
```

#### Business Logic Tests
```
✓ Mood detection works correctly
✓ Summarization produces reasonable output
✓ Recommendation ranking is consistent
✓ Cache hit/miss logic correct
✓ Fallback paths executed on error
```

---

## Integration Testing

### Framework: pytest + testcontainers (for Firestore)

**Setup**:
```bash
pip install pytest testcontainers
```

### Test Firestore Integration

```python
# tests/test_integration/test_firestore.py

from testcontainers.firebase import FirestoreContainer
import pytest

@pytest.fixture(scope="module")
def firestore():
    """Spin up ephemeral Firestore container"""
    with FirestoreContainer() as container:
        yield container.get_client()

def test_insert_and_fetch_entry(firestore):
    """Integration test: write and read from Firestore"""
    
    db = DBManager(firebase_client=firestore)
    
    # Write
    entry_id = db.insert_entry(uid="user_123", entry_text="Test entry")
    assert entry_id is not None
    
    # Read
    entries = db.fetch_entries(uid="user_123", limit=10, offset=0)
    assert len(entries) == 1
    assert entries[0]["entry_text"] == "Test entry"

def test_mood_analysis_workflow(firestore):
    """Integration test: full entry + analysis workflow"""
    
    db = DBManager(firebase_client=firestore)
    predictor = SentencePredictor("./ml/models/mood_detection/roberta/v2")
    
    # Create entry
    text = "I'm happy today!"
    entry_id = db.insert_entry(uid="user_123", entry_text=text)
    
    # Analyze
    mood_result = predictor.predict(text)
    db.insert_analysis(entry_id, summary="Happy entry", mood=mood_result)
    
    # Verify
    analysis = db.fetch_entry_analysis(entry_id)
    assert analysis["mood"] == "happy"
```

### External API Mocking

```python
# tests/test_integration/test_recommendations.py

import responses

@responses.activate
def test_tmdb_recommendation_fallback():
    """Test recommendation with mocked TMDb API"""
    
    # Mock TMDb response
    responses.add(
        responses.GET,
        "https://api.themoviedb.org/3/movie/popular",
        json={"results": [
            {"title": "Inception", "id": 27205, "popularity": 85.5},
            {"title": "Dark Knight", "id": 155, "popularity": 80.0}
        ]},
        status=200
    )
    
    # Call recommendation service
    results = recommend_media(uid="user_123", media_type="movies")
    
    # Verify results
    assert len(results["recommendations"]) == 2
    assert results["recommendations"][0]["title"] == "Inception"
    assert results["source"] == "live"  # Fallback path
```

---

## ML Model Testing

### Unit Tests for Inference

```python
# tests/test_ml/test_mood_detection.py

def test_mood_detection_basic():
    """Test basic mood detection"""
    
    predictor = SentencePredictor("./ml/models/mood_detection/roberta/v2")
    
    # Test cases
    test_cases = [
        ("I'm so happy!", "happy"),
        ("I'm angry!", "angry"),
        ("I'm sad.", "sad"),
        ("It is raining.", "neutral"),
    ]
    
    for text, expected_mood in test_cases:
        result = predictor.predict(text)
        assert result["dominant"] == expected_mood

def test_mood_detection_confidence():
    """Test that probabilities sum to 1"""
    
    predictor = SentencePredictor("./ml/models/...")
    result = predictor.predict("Test text")
    
    probs = result["probabilities"]
    total = sum(probs.values())
    assert abs(total - 1.0) < 0.001  # Float tolerance

def test_summarization_length():
    """Test summary stays within bounds"""
    
    summarizer = SummarizationPredictor("./ml/models/...")
    
    long_text = "word " * 500  # 500 words
    summary = summarizer.summarize(long_text)
    
    word_count = len(summary.split())
    assert 20 <= word_count <= 128  # Config bounds
```

### Performance Tests

```python
# tests/test_ml/test_performance.py

import time

def test_mood_detection_latency():
    """Ensure mood detection stays under SLA"""
    
    predictor = SentencePredictor("./ml/models/...")
    text = "Long entry text" * 10
    
    start = time.time()
    result = predictor.predict(text)
    elapsed = time.time() - start
    
    # SLA: < 500ms
    assert elapsed < 0.5, f"Latency {elapsed:.3f}s exceeded SLA"

def test_embedding_batch_performance():
    """Batch embeddings should be faster per-item"""
    
    embedding_service = get_embedding_service()
    texts = ["Entry " + str(i) for i in range(10)]
    
    # Single
    start = time.time()
    for text in texts:
        embedding_service.embed(text)
    single_time = time.time() - start
    
    # Batch (if supported)
    start = time.time()
    embeddings = embedding_service.embed_batch(texts)
    batch_time = time.time() - start
    
    # Batch should be faster
    assert batch_time < single_time * 0.8
```

---

## End-to-End Testing

### Postman Collection

**File**: `Pocket Journal API Collection.postman_collection.json`

**Test Scenarios**:
1. **User Registration & Login**
   - Create user
   - Verify user created in Firestore

2. **Entry Management**
   - Create entry with mood + summary
   - List entries
   - Update entry
   - Delete entry

3. **Recommendations**
   - Get movie recommendations (cache hit)
   - Search for movies
   - Verify results formatted correctly

4. **Insights**
   - Generate insights for date range
   - Fetch insights
   - Verify structure

5. **Error Cases**
   - 401 (missing token)
   - 403 (unauthorized access)
   - 404 (not found)
   - 400 (validation)

### Running E2E Tests

```bash
# Using Newman (Postman CLI)
npm install -g newman

newman run "Pocket Journal API Collection.postman_collection.json" \
  --environment production.postman_environment.json \
  --reporters cli,json \
  --reporter-json-export report.json
```

---

## Load Testing

### Locust Script

```python
# tests/load_test.py

from locust import HttpUser, task, between
import random

class PocketJournalUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        """Login and get auth token"""
        response = self.client.post("/api/v1/auth/create-user", json={
            "email": f"user_{random.randint(1000, 9999)}@test.com",
            "password": "test_password",
            "name": "Test User"
        })
        self.token = response.json()["uid"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    @task(3)
    def create_entry(self):
        """Create entry (3x as common)"""
        self.client.post("/api/v1/entries", 
            headers=self.headers,
            json={"entry_text": "Today was interesting..."})
    
    @task(2)
    def list_entries(self):
        """List entries (2x as common)"""
        self.client.get("/api/v1/entries", headers=self.headers)
    
    @task(1)
    def get_recommendations(self):
        """Get recommendations (1x as common)"""
        self.client.get("/api/v1/movies/recommend", headers=self.headers)
```

**Run**:
```bash
locust -f tests/load_test.py \
  --host http://localhost:5000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m
```

---

## Coverage Requirements

| Component | Minimum Coverage | Target |
|-----------|------------------|--------|
| Routes | 80% | 90% |
| Services | 85% | 95% |
| ML Inference | 70% | 85% |
| Database Layer | 90% | 95% |
| Utilities | 70% | 80% |
| **Overall** | **80%** | **90%** |

**Generate Coverage Report**:
```bash
pytest --cov=Backend --cov-report=html
# Opens: htmlcov/index.html
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      firestore-emulator:
        image: google/cloud-firestore-emulator
        options: >-
          --health-cmd "curl -f http://localhost:8080"
          --health-interval 10s
          --health-timeout 5s
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install -r Backend/requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: Run unit tests
        run: |
          pytest Backend/tests/unit --cov=Backend --cov-report=xml
      
      - name: Run integration tests
        env:
          FIRESTORE_EMULATOR_HOST: localhost:8080
        run: |
          pytest Backend/tests/integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Testing Checklist

- [ ] Unit tests written for all business logic
- [ ] Integration tests for Firestore operations
- [ ] ML model tests verify correctness
- [ ] Performance tests verify SLA adherence
- [ ] E2E tests cover critical user flows
- [ ] Load tests verify scalability
- [ ] Error scenarios tested (400, 401, 403, 404, 500)
- [ ] Edge cases tested (empty inputs, null values, large payloads)
- [ ] Security tests (injection, CORS, auth)
- [ ] Coverage > 80% overall
- [ ] CI/CD pipeline running all tests
- [ ] Test results reviewed before merge


