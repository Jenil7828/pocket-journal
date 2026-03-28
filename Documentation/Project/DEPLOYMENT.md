# Deployment: Pocket Journal Backend

## Environment Setup

### Prerequisites

- **Operating System**: Linux (Ubuntu 22.04+) or macOS
- **Python**: 3.10+
- **GPU** (Optional): NVIDIA CUDA 12.1+ (for optimized ML inference)
- **Firebase Project**: Created in Firebase Console
- **External APIs**: TMDb, Spotify, Google Books API keys

### Required Environment Variables

Create a `.env` file in the `Backend/` directory:

```bash
# Firebase
FIREBASE_CREDENTIALS_PATH=./secrets/pocket-journal-be-firebase-adminsdk-fbsvc-b311d88edc.json

# External APIs
TMDB_API_KEY=your_tmdb_api_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
GOOGLE_BOOKS_API_KEY=your_google_books_api_key

# Optional: LLM
GOOGLE_API_KEY=your_google_gemini_api_key  # For Gemini insights

# Server
FLASK_PORT=5000
FLASK_DEBUG=true  # development only

# Model Store
MODEL_SOURCE=local  # local | gcs | s3
MODEL_STORE_PATH=./ml/models  # For local source
# MODEL_GCS_BUCKET=your-bucket  # For GCS
# MODEL_S3_BUCKET=your-bucket  # For S3
```

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/pocket-journal.git
cd pocket-journal/Backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Download Models

```bash
python scripts/download_models.py
# Downloads: RoBERTa, BART, Qwen2 to ml/models/
```

### 5. Set Up Firebase

1. Download service account JSON from Firebase Console:
   - Project Settings → Service Accounts → Generate new private key
2. Save to `Backend/secrets/pocket-journal-be-firebase-adminsdk-fbsvc-b311d88edc.json`
3. Set `FIREBASE_CREDENTIALS_PATH` in `.env`

### 6. Configure External APIs

1. **TMDb**: Create account at https://www.themoviedb.org/settings/api, copy API key
2. **Spotify**: Create app at https://developer.spotify.com/dashboard, copy client ID/secret
3. **Google Books**: Create API key in Google Cloud Console
4. Set all keys in `.env`

### 7. Run Development Server

```bash
python app.py
```

**Output**:
```
[2026-03-29 10:30:00] INFO pocket_journal: Initialized Firebase app...
[2026-03-29 10:30:01] INFO pocket_journal: Loaded RoBERTa model (v2)
[2026-03-29 10:30:02] INFO pocket_journal: Loaded BART model (v2)
[2026-03-29 10:30:05] INFO pocket_journal: Starting Flask server on port 5000
```

**Test the API**:
```bash
curl http://localhost:5000/api/v1/health
# Response: {"status": "ok", "services": {...}}
```

---

## Docker Deployment

### Build Docker Image

```bash
docker build -f Dockerfile -t pocket-journal-backend:latest .
```

**Build Arguments**:
- `CUDA_VERSION`: nvidia/cuda version (default: 12.1.1)
- `BASE_IMAGE`: nvidia/cuda or python:3.11 (default: nvidia/cuda)

### Run Container

**Basic**:
```bash
docker run \
  --gpus all \
  -e FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase-key.json \
  -e TMDB_API_KEY=your_key \
  -e SPOTIFY_CLIENT_ID=your_id \
  -e SPOTIFY_CLIENT_SECRET=your_secret \
  -e GOOGLE_BOOKS_API_KEY=your_key \
  -v /path/to/secrets:/app/secrets \
  -p 8080:8080 \
  pocket-journal-backend:latest
```

**Production (with environment file)**:
```bash
docker run \
  --gpus all \
  --env-file .env.production \
  -v /path/to/models:/tmp/models \
  -p 8080:8080 \
  pocket-journal-backend:latest
```

### Environment Variables in Container

Override in `.env.production`:
```
PORT=8080
MODEL_SOURCE=local
MODEL_CACHE_DIR=/tmp/models
FLASK_DEBUG=false
APP_LOG_LEVEL=INFO
```

---

## Docker Compose Setup

### Configuration

Create `docker-compose.yml` in project root:

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    image: pocket-journal-backend:latest
    container_name: pocket-journal-api
    
    # GPU Support
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    
    # Ports
    ports:
      - "8080:8080"
    
    # Environment
    environment:
      PORT: 8080
      MODEL_SOURCE: local
      MODEL_CACHE_DIR: /tmp/models
      FLASK_DEBUG: "false"
      APP_LOG_LEVEL: INFO
    
    # Secrets (mounted)
    volumes:
      - ./Backend/secrets:/app/secrets:ro
      - ./Backend/ml/models:/tmp/models:ro
      - ./logs:/app/logs
    
    # Health Check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    
    # Restart Policy
    restart: unless-stopped
    
    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  # Optional: Ollama for local LLM (if using Qwen2 via Ollama)
  ollama:
    image: ollama/ollama:latest
    container_name: pocket-journal-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    
volumes:
  ollama-data:
```

### Deploy with Docker Compose

```bash
# Set required env vars
export FIREBASE_CREDENTIALS_PATH=./Backend/secrets/...
export TMDB_API_KEY=your_key
# ... (set all required keys)

# Build and start
docker-compose up -d

# Check logs
docker-compose logs -f backend

# Stop
docker-compose down
```

---

## Firebase Configuration

### Firestore Setup

1. **Create Database**:
   - Firebase Console → Firestore Database → Create database
   - Region: Choose closest to users (e.g., `us-central1`)
   - Start in production mode (configure rules in next step)

2. **Security Rules**:
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       // User-owned collections
       match /journal_entries/{document=**} {
         allow read, write: if request.auth.uid == resource.data.uid;
       }
       // Shared cache (readable by all authenticated users)
       match /media_cache/{document=**} {
         allow read: if request.auth.uid != null;
         allow write: if request.auth.token.iss == "https://securetoken.google.com/{PROJECT_ID}";
       }
       // ... (configure other collections)
     }
   }
   ```

3. **Create Indexes**:
   - Firestore → Indexes → Create composite index
   - Add critical indexes (see DATABASE_SCHEMA.md for full list)

### Firebase Auth

1. **Enable Email/Password**:
   - Firebase Console → Authentication → Sign-in methods
   - Enable Email/Password provider

2. **Configure CORS** (if frontend on different domain):
   - Firebase Console → Settings → Authorized domains
   - Add your frontend domain

---

## API Keys Management

### Secure Storage

**Development**:
- Store in `.env` file (add to `.gitignore`)
- Use `python-dotenv` to load

**Production**:
- Use environment variables from CI/CD pipeline
- Or Cloud Secret Manager (GCP) / AWS Secrets Manager
- Never commit keys to version control

### Rotating Keys

1. Generate new key in provider console
2. Update environment variable
3. Restart application
4. Verify health check passes
5. Disable old key

---

## Configuration Management

### config.yml Overrides

All settings in `Backend/config.yml` can be overridden via environment variables:

```yaml
# config.yml
api:
  request_timeout: 10
```

Override:
```bash
export API_REQUEST_TIMEOUT=20
python app.py
```

### Example Production Config

`.env.production`:
```bash
# Server
FLASK_DEBUG=false
APP_LOG_LEVEL=WARNING
WERKZEUG_LOG_LEVEL=ERROR

# Timeouts & Retries
API_REQUEST_TIMEOUT=30
API_REQUEST_MAX_RETRIES=2

# ML Models
MOOD_MODEL_VERSION=v2
SUMMARIZATION_MODEL_VERSION=v2
INSIGHTS_USE_GEMINI=true
INSIGHTS_GEMINI_MODEL_NAME=gemini-2.0-flash

# Cache
MEDIA_CACHE_MAX_AGE_HOURS=24
MEDIA_CACHE_FETCH_LIMIT=500

# Recommendations
RECOMMENDATION_FETCH_LIMIT=200
RECOMMENDATION_REFINE_TOP=100

# Rate Limiting (if implemented)
RATE_LIMIT_PER_MINUTE=60
```

---

## Monitoring & Logging

### Log Levels

```python
# Set per-module log level in config.yml
logging:
  app_level: "INFO"         # Pocket Journal
  werkzeug_level: "WARNING" # Flask/Werkzeug
  firebase_level: "WARNING" # Firebase SDK
```

### Log Output

- **Development**: Colored console output (via `ColoredFormatter`)
- **Production**: JSON-formatted logs (for log aggregation)

### Health Check Endpoint

```bash
curl http://localhost:5000/api/v1/health
# Response: {"status": "ok", "services": {"firebase": "ok", "models": "ready"}}
```

### Monitoring Metrics

**Key Metrics to Track**:
- API response times (p50, p95, p99)
- ML inference latency (mood, summarization, insights)
- Cache hit rates (media_cache)
- Error rates by endpoint
- Provider API call counts and failures
- Database query latency

**Integration**:
- Prometheus for metrics collection
- Grafana for dashboards
- DataDog / New Relic for APM

---

## Scaling Strategy

### Horizontal Scaling

**Multiple Flask Workers**:
```bash
# Local development
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Docker
docker run -e WORKERS=8 pocket-journal-backend:latest
```

**Load Balancer**:
- Nginx or HAProxy in front of multiple backend instances
- Session affinity not required (stateless design)

### Firestore Auto-Scaling

- Firestore handles concurrent writes/reads automatically
- Monitor billing for cost optimization

### GPU Resource Management

- If using multiple GPUs: Use `--gpus all` to expose all
- Consider GPU sharing if multiple instances needed

---

## Backup & Recovery

### Firestore Backups

**Automated Export** (GCP):
```bash
# Export collections to GCS
gcloud firestore export gs://your-bucket/firestore-backup/

# Schedule with Cloud Scheduler
gcloud scheduler jobs create app-engine backup-job \
  --schedule="0 2 * * *" \
  --http-method=POST \
  --uri=https://firestore.googleapis.com/v1/projects/YOUR_PROJECT_ID/databases/(default):exportDocuments
```

**Manual Backup**:
```bash
python scripts/backup_firestore.py --output ./backups/
```

### Restore from Backup

```bash
gcloud firestore import gs://your-bucket/firestore-backup/
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r Backend/requirements.txt
          pip install pytest
      - name: Run tests
        run: pytest Backend/tests/
  
  build-and-push:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Build Docker image
        run: docker build -t gcr.io/${{ secrets.GCP_PROJECT_ID }}/pocket-journal-backend:latest .
      - name: Push to GCR
        run: |
          echo ${{ secrets.GCP_SA_KEY }} | docker login -u _json_key --password-stdin https://gcr.io
          docker push gcr.io/${{ secrets.GCP_PROJECT_ID }}/pocket-journal-backend:latest
  
  deploy:
    needs: build-and-push
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy pocket-journal-backend \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/pocket-journal-backend:latest \
            --platform managed \
            --region us-central1 \
            --set-env-vars FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase.json
```

---

## Performance Tuning

### Model Optimization

**ONNX Runtime** (quantized models):
```bash
# Convert PyTorch model to ONNX
python ml/utils/convert_to_onnx.py --model roberta-v2 --output ml/models/

# Enable GPU inference
export ONNXRUNTIME_EXECUTION_PROVIDERS="CUDAExecutionProvider,CPUExecutionProvider"
```

### Batch Processing

For insights generation (multiple users):
```bash
# Process up to 5 entries per batch
python scripts/batch_insights.py --batch-size=5 --workers=3
```

---

## Troubleshooting

### Common Issues

**Issue**: `FIREBASE_CREDENTIALS_PATH not set`
```
Solution: Set environment variable
export FIREBASE_CREDENTIALS_PATH=./secrets/firebase-key.json
```

**Issue**: `CUDA out of memory`
```
Solution: Reduce batch size or use CPU
export INSIGHTS_BACKEND=huggingface  # Uses CPU fallback
```

**Issue**: `Rate limited by Spotify`
```
Solution: Increase cache TTL
export MEDIA_CACHE_MAX_AGE_HOURS=48
```

**Issue**: `Firestore quota exceeded`
```
Solution: Implement query caching or pagination
Review Firestore billing settings
```

---

## Production Checklist

- [ ] Firebase security rules configured
- [ ] All API keys set and rotated
- [ ] HTTPS/TLS enabled
- [ ] Health check endpoint accessible
- [ ] Logs aggregated and monitored
- [ ] Backup strategy tested
- [ ] Database indexes created
- [ ] Load testing completed (target: 1000 req/s)
- [ ] Error handling verified
- [ ] Rate limiting configured
- [ ] CORS configured for frontend domains
- [ ] Performance baselines established


