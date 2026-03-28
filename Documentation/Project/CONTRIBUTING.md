# Contributing: Pocket Journal Backend

## Code Standards

### Python Style Guide: PEP 8

```python
# ✓ Good
def create_user_entry(user_id: str, entry_text: str) -> str:
    """Create a new journal entry for user.
    
    Args:
        user_id: Firebase Auth UID
        entry_text: Journal entry content
    
    Returns:
        Entry document ID
    """
    if not entry_text:
        raise ValueError("entry_text cannot be empty")
    
    entry_id = db.insert_entry(user_id, entry_text)
    return entry_id

# ✗ Bad
def createUserEntry(uid,text):  # camelCase, no type hints
    """Create entry"""  # Unclear docstring
    x = db.insert_entry(uid, text)  # Single-letter variable
    return x
```

### Formatting Tools

**Install**:
```bash
pip install black flake8 isort
```

**Pre-commit Hook**:
```bash
# .git/hooks/pre-commit
#!/bin/bash
black Backend/
flake8 Backend/ --max-line-length=100
isort Backend/
```

**Run Manually**:
```bash
black Backend/  # Format all files
flake8 Backend/ --max-line-length=100  # Lint
isort Backend/  # Sort imports
```

### Naming Conventions

| Entity | Convention | Example |
|--------|-----------|---------|
| Variables | snake_case | `entry_id`, `user_uid` |
| Functions | snake_case | `get_entries()`, `insert_analysis()` |
| Classes | PascalCase | `DBManager`, `SentencePredictor` |
| Constants | UPPER_SNAKE_CASE | `MAX_ENTRY_LENGTH`, `DEFAULT_TIMEOUT` |
| Private | Leading underscore | `_load_model()`, `_internal_helper` |

### Docstring Format

**Google Style**:
```python
def recommend_media(
    uid: str,
    media_type: str,
    filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, object]:
    """Generate media recommendations based on user mood.
    
    Implements Phase 3 recommendation pipeline:
    1. Build intent vector from user embeddings
    2. Query media cache
    3. Rank by similarity + popularity
    4. Fallback to live provider if cache miss
    
    Args:
        uid: Firebase Auth UID
        media_type: "movies", "songs", "books", or "podcasts"
        filters: Optional dict with language, genre, etc.
    
    Returns:
        Dict with keys:
            - results: List of media items
            - source: "cache" or "live"
            - metrics: Performance metrics
    
    Raises:
        ValueError: If media_type invalid
        RuntimeError: If all providers fail
    
    Example:
        >>> recs = recommend_media("uid_123", "movies")
        >>> recs["results"][0]["title"]
        "Inception"
    """
```

---

## Folder Structure

```
Backend/
├── app.py                           # Entry point
├── config.yml                       # Configuration
├── config_loader.py                 # Config parser
├── requirements.txt                 # Dependencies
│
├── routes/                          # HTTP endpoints
│   ├── __init__.py
│   ├── auth.py                      # Auth endpoints
│   ├── entries.py                   # Entry CRUD
│   ├── media.py                     # Media endpoints
│   ├── insights.py                  # Insights endpoints
│   ├── stats.py                     # Statistics
│   ├── export_route.py              # Data export
│   └── user.py                      # User profile
│
├── services/                        # Business logic
│   ├── __init__.py
│   ├── embedding_service.py         # Embedding generation
│   ├── health_service.py            # Health checks
│   ├── search_service.py            # Media search (cache-first)
│   ├── export_service/              # Export package
│   ├── insights_service/            # Insights generation
│   ├── journal_entries/             # Entry management
│   ├── media_recommender/           # Recommendation engine
│   ├── media_recommender/
│   │   ├── recommendation.py        # Main logic
│   │   ├── cache_store.py           # Cache ops
│   │   └── providers/
│   │       ├── base_provider.py     # Abstract provider
│   │       ├── tmdb_provider.py     # TMDb
│   │       ├── spotify_provider.py  # Spotify
│   │       └── books_provider.py    # Google Books
│   └── stats_service/               # Analytics
│
├── persistence/                     # Database
│   ├── __init__.py
│   ├── db_manager.py                # Firestore CRUD
│   └── database_schema.py           # Schema definitions
│
├── ml/                              # ML models
│   ├── __init__.py
│   ├── utils/
│   │   ├── model_loader.py          # Model loading
│   │   └── convert_to_onnx.py       # ONNX conversion
│   ├── inference/
│   │   ├── mood_detection/roberta/
│   │   ├── summarization/bart/
│   │   └── insight_generation/qwen2/
│   └── models/                      # Model weights (git-ignored)
│       ├── mood_detection/roberta/v2/
│       ├── summarization/bart/v2/
│       └── insight_generation/qwen2/v1/
│
├── utils/                           # Utilities
│   ├── __init__.py
│   ├── log_formatter.py             # Colored logging
│   ├── logging_utils.py             # Request/response logging
│   └── firestore_serializer.py      # Date serialization
│
├── scripts/                         # Scripts
│   ├── download_models.py           # Download model weights
│   ├── cache_media.py               # Refresh media cache
│   ├── entrypoint.sh                # Docker entry
│   └── backup_firestore.py          # Backup script
│
├── secrets/                         # Credentials (git-ignored)
│   └── *.json                       # Firebase keys
│
└── tests/                           # Test suite
    ├── conftest.py                  # Shared fixtures
    ├── test_routes/
    ├── test_services/
    └── test_ml/
```

### Where to Add Code

| Task | Location |
|------|----------|
| New API endpoint | `routes/*.py` |
| New business logic | `services/*.py` or subpackage |
| Database operation | `persistence/db_manager.py` |
| ML model integration | `ml/inference/*/predictor.py` |
| Utility function | `utils/*.py` |
| Test | `tests/test_*.py` (mirror source structure) |

---

## PR Guidelines

### Before Submitting

1. **Format Code**:
   ```bash
   black Backend/
   isort Backend/
   ```

2. **Run Linter**:
   ```bash
   flake8 Backend/ --max-line-length=100
   ```

3. **Write Tests**:
   ```bash
   pytest Backend/tests/ --cov=Backend
   # Target: >80% coverage
   ```

4. **Update Documentation**:
   - Add/update docstrings
   - Update README if user-facing
   - Update Architecture docs if design changed

5. **Check Secrets**:
   ```bash
   # Ensure no credentials committed
   git diff --cached | grep -i "password\|secret\|key"
   ```

### PR Title Format

```
[TYPE] Brief description

TYPE: feature | bugfix | refactor | docs | test | chore

Examples:
[feature] Add sentiment analysis to mood detection
[bugfix] Fix rate limiting for Spotify API
[refactor] Optimize embedding cache lookups
[docs] Add performance benchmarks to PERFORMANCE.md
```

### PR Description Template

```markdown
## Description
Brief explanation of changes.

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How was this tested?
- [ ] Unit tests added
- [ ] Integration tests added
- [ ] Manual testing on [env]

## Checklist
- [ ] Code formatted (black, isort)
- [ ] Tests passing
- [ ] Coverage > 80%
- [ ] Docstrings updated
- [ ] No credentials committed
- [ ] Documentation updated (if needed)

## Related Issues
Closes #123
```

### Review Process

**Reviewers Check**:
1. Code quality (PEP 8, naming)
2. Test coverage (>80%)
3. No security issues
4. Performance implications
5. Backward compatibility

**Approval**: 2 approvals required before merge

**Merge Strategy**: Squash commits to main

---

## Branching Strategy

### Git Flow

```
main (stable, production-ready)
  ├─ develop (integration branch)
  │   ├─ feature/mood-boost (from develop)
  │   ├─ bugfix/cache-ttl (from develop)
  │   └─ release/v3.0 (release candidate)
  └─ hotfix/security-patch (from main)
```

### Branch Naming

```
feature/short-description         # New feature
bugfix/issue-number               # Bug fix
refactor/component-name           # Code cleanup
docs/what-document                # Documentation
hotfix/urgent-issue               # Production fix
```

### Workflow

```bash
# 1. Create feature branch from develop
git checkout develop
git pull origin develop
git checkout -b feature/new-recommendation-logic

# 2. Commit regularly with meaningful messages
git commit -m "Add intent vector blending for personalization"

# 3. Push and create PR
git push origin feature/new-recommendation-logic
# Create PR on GitHub → develop branch

# 4. After 2 approvals and CI passes, merge
# (maintainer squashes and merges)

# 5. Delete local branch
git checkout develop
git pull origin develop
git branch -d feature/new-recommendation-logic
```

---

## Commit Message Format

**Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Example**:
```
feat(media): implement cache-first recommendation pipeline

- Add media_cache collection queries
- Implement ranking by similarity + popularity
- Add fallback to live provider
- Add comprehensive logging

Closes #234
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `test`: Test additions/changes
- `docs`: Documentation
- `chore`: Dependencies, tooling

**Scope**: Component (media, ml, auth, db, etc.)

**Subject**:
- Imperative mood ("add", not "adds" or "added")
- No period
- < 50 characters

---

## Local Development Checklist

- [ ] Fork repository
- [ ] Clone locally
- [ ] Create virtual environment (`venv`)
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Download models (`python scripts/download_models.py`)
- [ ] Set up `.env` with Firebase credentials
- [ ] Run tests (`pytest`)
- [ ] Start dev server (`python app.py`)
- [ ] Open http://localhost:5000/api/v1/health (should return ok)

---

## Common Development Tasks

### Adding a New API Endpoint

1. **Define in routes**:
   ```python
   # routes/insights.py
   @app.route("/api/v1/insights/custom", methods=["GET"])
   @login_required
   def get_custom_insights():
       # Implementation
       return response, 200
   ```

2. **Test it**:
   ```bash
   pytest tests/test_routes/test_insights.py::test_get_custom_insights
   ```

3. **Document in API_SPECIFICATION.md**

### Adding a Service

1. **Create module**:
   ```python
   # services/my_service.py
   class MyService:
       def __init__(self, db):
           self.db = db
       
       def do_something(self):
           pass
   ```

2. **Inject into app.py**:
   ```python
   from services.my_service import MyService
   my_service = MyService(get_db())
   ```

3. **Write tests**:
   ```bash
   pytest tests/test_services/test_my_service.py
   ```

### Updating ML Model

1. **Train new model locally**
2. **Convert to ONNX**:
   ```bash
   python ml/utils/convert_to_onnx.py --model my_model
   ```
3. **Update config.yml**:
   ```yaml
   ml:
     mood_detection:
       model_version: "v3"  # Bump version
   ```
4. **Test inference**:
   ```bash
   pytest tests/test_ml/test_mood_detection.py
   ```

---

## Debugging Tips

### Enable Debug Logging

```bash
export APP_LOG_LEVEL=DEBUG
export FIREBASE_LOG_LEVEL=DEBUG
python app.py
```

### Use pdb (Python Debugger)

```python
import pdb; pdb.set_trace()  # Breakpoint

# In debugger:
(Pdb) p variable_name  # Print value
(Pdb) n                 # Next line
(Pdb) s                 # Step into function
(Pdb) c                 # Continue
```

### Profile Code

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)  # Top 10 functions
```

### Monitor Model Performance

```bash
# GPU memory
nvidia-smi

# CPU usage
top

# Firestore latency
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/v1/health
# Check timestamps
```

---

## Code Review Checklist

When reviewing others' code:

- [ ] Code follows PEP 8 style guide
- [ ] Meaningful variable/function names
- [ ] Docstrings present and clear
- [ ] Tests written and passing (>80% coverage)
- [ ] No hardcoded secrets or credentials
- [ ] No commented-out code (unless explaining something)
- [ ] Error handling appropriate (try/except, validation)
- [ ] Performance implications considered
- [ ] Backward compatibility maintained
- [ ] Documentation updated (if needed)
- [ ] No breaking changes without deprecation notice


