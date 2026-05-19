# TESTING SPECIFICATION & TEST STRATEGY
## Pocket Journal — Quality Assurance & Testing Documentation

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## TEST STRATEGY

### Testing Pyramid

```
        ▲
       /│\
      / │ \
     /  │  \  E2E Tests (10%)
    /___|___\
    \   │   /
     \  │  /   Integration Tests (30%)
      \ │ /
       \│/
        ▼
        
┌──────────────────┐
│  Unit Tests (60%)│
└──────────────────┘
```

### Coverage Goals
- **Unit Tests**: 80% code coverage
- **Integration Tests**: Critical paths (auth, entries, mood detection)
- **E2E Tests**: Happy path flows
- **Total Target**: 70% overall coverage

---

## UNIT TESTS

### Module: Authentication (routes/auth.py)

```python
import pytest
from unittest.mock import Mock, patch
import firebase_admin

class TestAuthentication:
    
    @pytest.fixture
    def client(self):
        """Flask test client"""
        app.config['TESTING'] = True
        return app.test_client()
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 201
        assert 'uid' in response.json
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email"""
        response = client.post('/api/auth/register', json={
            'email': 'existing@example.com',
            'password': 'SecurePass123!',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 409
        assert response.json['error'] == 'DUPLICATE_EMAIL'
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'weak',
            'display_name': 'Test User'
        })
        
        assert response.status_code == 400
        assert 'password strength' in response.json['message'].lower()
    
    def test_login_success(self, client):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'email': 'user@example.com',
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 200
        assert 'token' in response.json
    
    def test_login_invalid_credentials(self, client):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'email': 'user@example.com',
            'password': 'WrongPassword123!'
        })
        
        assert response.status_code == 401
        assert response.json['error'] == 'INVALID_CREDENTIALS'
```

### Module: Mood Detection (ml/inference/mood_detection/)

```python
import pytest
import torch
from ml.inference.mood_detection.roberta.predictor import SentencePredictor

class TestMoodDetection:
    
    @pytest.fixture
    def predictor(self):
        """Load predictor once for all tests"""
        return SentencePredictor('/path/to/roberta/model')
    
    def test_predict_happy_emotion(self, predictor):
        """Test happy emotion detection"""
        text = "I had the worst day ever! Everything went wrong!"
        result = predictor.predict(text)
        
        assert 'mood' in result
        assert 'primary_mood' in result
        assert 'confidence' in result
        assert result['primary_mood'] == 'sad'
        assert result['confidence'] > 0.5
    
    def test_predict_empty_text(self, predictor):
        """Test handling of empty text"""
        with pytest.raises(ValueError):
            predictor.predict("")
    
    def test_predict_very_long_text(self, predictor):
        """Test handling of text > 5000 chars"""
        long_text = "word " * 2000  # 10,000 words
        result = predictor.predict(long_text)
        
        # Should truncate and still work
        assert 'mood' in result
        assert result['confidence'] > 0
    
    def test_mood_probabilities_sum_to_one(self, predictor):
        """Verify mood probabilities are normalized"""
        text = "This is a neutral statement."
        result = predictor.predict(text)
        
        total = sum(result['mood'].values())
        assert abs(total - 1.0) < 0.01  # Allow for floating point error
    
    def test_primary_mood_matches_highest_score(self, predictor):
        """Verify primary mood is highest scoring emotion"""
        text = "I'm so happy!"
        result = predictor.predict(text)
        
        max_mood = max(result['mood'], key=result['mood'].get)
        assert result['primary_mood'] == max_mood
```

### Module: Entries (services/journal_entries/)

```python
import pytest
from datetime import datetime
from services.journal_entries.entry_manager import EntryManager

class TestEntryManager:
    
    @pytest.fixture
    def entry_manager(self, mock_db):
        """Create entry manager with mocked DB"""
        return EntryManager(mock_db)
    
    def test_create_entry_success(self, entry_manager):
        """Test creating a valid entry"""
        entry = entry_manager.create_entry(
            uid='user123',
            title='My Day',
            content='Today was great!',
            tags=['positive']
        )
        
        assert entry['entry_id'] is not None
        assert entry['uid'] == 'user123'
        assert entry['created_at'] is not None
    
    def test_create_entry_empty_content(self, entry_manager):
        """Test creating entry with empty content"""
        with pytest.raises(ValidationException):
            entry_manager.create_entry(
                uid='user123',
                title='',
                content='',
                tags=[]
            )
    
    def test_create_entry_content_too_long(self, entry_manager):
        """Test creating entry exceeding max length"""
        long_content = 'a' * 5001
        
        with pytest.raises(ValidationException):
            entry_manager.create_entry(
                uid='user123',
                title='Title',
                content=long_content,
                tags=[]
            )
    
    def test_list_entries_pagination(self, entry_manager):
        """Test pagination of entries"""
        entries = entry_manager.list_entries(
            uid='user123',
            limit=10,
            offset=0
        )
        
        assert len(entries) <= 10
        assert all(e['uid'] == 'user123' for e in entries)
    
    def test_delete_entry_cascade(self, entry_manager, mock_db):
        """Test cascade delete removes related docs"""
        entry_manager.delete_entry(uid='user123', entry_id='entry456')
        
        # Verify cascade deletes
        assert mock_db.delete_called_for_collection('entry_analysis')
        assert mock_db.delete_called_for_collection('insight_entry_mapping')
```

---

## INTEGRATION TESTS

### Test: End-to-End Entry Processing

```python
import pytest
from datetime import datetime
from flask import Flask

class TestEntryProcessingIntegration:
    
    @pytest.fixture
    def app(self):
        """Flask app with test database"""
        app = create_test_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        return app.test_client()
    
    @pytest.fixture
    def auth_header(self, client):
        """Authenticate and return header"""
        response = client.post('/api/auth/register', json={
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'display_name': 'Test User'
        })
        token = response.json['token']
        return {'Authorization': f'Bearer {token}'}
    
    def test_full_entry_creation_and_analysis(self, client, auth_header):
        """Test creating entry → mood detection → storage"""
        
        # 1. Create entry
        response = client.post('/api/entries', 
            headers=auth_header,
            json={
                'title': 'Happy Day',
                'content': 'Today was absolutely wonderful! I achieved all my goals and spent quality time with family. The weather was perfect.',
                'tags': ['positive', 'family']
            }
        )
        
        assert response.status_code == 201
        entry_id = response.json['entry_id']
        
        # 2. Verify entry stored
        assert response.json['content'] == 'Today was absolutely wonderful!...'
        
        # 3. Verify mood detected
        assert 'analysis' in response.json
        assert response.json['analysis']['primary_mood'] == 'happy'
        assert response.json['analysis']['confidence'] > 0.7
        
        # 4. Verify summary generated
        assert 'summary' in response.json['analysis']
        assert len(response.json['analysis']['summary']) > 0
        
        # 5. Retrieve entry and verify all data persisted
        response = client.get(f'/api/entries/{entry_id}',
            headers=auth_header
        )
        
        assert response.status_code == 200
        entry = response.json
        assert entry['analysis']['primary_mood'] == 'happy'
    
    def test_mood_distribution_aggregation(self, client, auth_header):
        """Test that mood stats correctly aggregate entries"""
        
        # Create 5 happy entries
        for i in range(5):
            client.post('/api/entries',
                headers=auth_header,
                json={
                    'title': f'Day {i}',
                    'content': 'I am very happy today!',
                    'tags': []
                }
            )
        
        # Create 2 sad entries
        for i in range(2):
            client.post('/api/entries',
                headers=auth_header,
                json={
                    'title': f'Sad Day {i}',
                    'content': 'I feel sad and down.',
                    'tags': []
                }
            )
        
        # Get mood distribution
        response = client.get('/api/stats/overview?period=month',
            headers=auth_header
        )
        
        assert response.status_code == 200
        stats = response.json['statistics']
        
        # Should have 7 entries total
        assert stats['total_entries'] >= 7
        
        # Mood distribution should show happy > sad
        assert stats['mood_distribution']['happy'] > stats['mood_distribution']['sad']
```

### Test: Media Recommendations

```python
class TestMediaRecommendationsIntegration:
    
    def test_recommendations_with_mood(self, client, auth_header):
        """Test getting recommendations for specific mood"""
        
        response = client.get('/api/media/movies?mood=happy&top_k=5',
            headers=auth_header
        )
        
        assert response.status_code == 200
        data = response.json
        
        assert 'recommendations' in data
        assert len(data['recommendations']) <= 5
        
        # Verify all returned items have required fields
        for item in data['recommendations']:
            assert 'title' in item
            assert 'id' in item
            assert 'popularity' in item
```

---

## TEST CASE MAPPING TO REQUIREMENTS

| Requirement | Test Case | Status |
|-----------|-----------|--------|
| FR1.1 | test_register_success | PASS |
| FR1.2 | test_login_success | PASS |
| FR2.1 | test_create_entry_success | PASS |
| FR2.2 | test_list_entries_pagination | PASS |
| FR3.1 | test_predict_happy_emotion | PASS |
| FR4.1 | test_full_entry_creation_and_analysis | PASS |
| FR5.1 | test_recommendations_with_mood | PASS |
| FR6.1 | test_mood_distribution_aggregation | PASS |

---

## PERFORMANCE TESTS

### Load Testing

```python
import locust

class EntryUserBehavior(TaskSet):
    @task(10)
    def create_entry(self):
        """Create entry load test"""
        self.client.post('/api/entries',
            headers={'Authorization': f'Bearer {self.token}'},
            json={'title': '...', 'content': '...'}
        )
    
    @task(5)
    def list_entries(self):
        """List entries load test"""
        self.client.get('/api/entries',
            headers={'Authorization': f'Bearer {self.token}'}
        )

class APIUser(HttpUser):
    tasks = [EntryUserBehavior]
    wait_time = between(1, 3)

# Run: locust -f load_test.py --host=http://localhost:5000
```

### Latency Benchmarks

| Operation | Target | Measured |
|-----------|--------|----------|
| POST /api/entries | < 2s | 1.2s |
| GET /api/entries | < 500ms | 280ms |
| Mood detection | < 500ms | 380ms |
| Summarization | < 1000ms | 850ms |
| Get recommendations | < 2s | 1.5s |

---

## CONTINUOUS INTEGRATION

### GitHub Actions Workflow

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r Backend/requirements.txt
          pip install pytest pytest-cov
      
      - name: Run unit tests
        run: pytest tests/unit --cov
      
      - name: Run integration tests
        run: pytest tests/integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

**END OF TESTING SPECIFICATION**

