# DEPLOYMENT & OPERATIONS GUIDE
## Pocket Journal — Deployment & Environment Configuration

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## DEPLOYMENT ENVIRONMENTS

### Development Environment

**Setup:**
```bash
cd Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Run:**
```bash
python app.py  # Starts on http://localhost:5000
```

**Configuration:**
```ini
# Backend/.env
FLASK_ENV=development
PORT=5000
DEBUG=True
FIREBASE_CREDENTIALS_PATH=secrets/firebase-adminsdk.json
```

---

### Production Environment (Docker)

**Build:**
```bash
docker build -f Dockerfile -t pocket-journal:latest .
```

**Run with GPU:**
```bash
docker run --gpus all \
  --env-file Backend/.env \
  -v $(pwd)/Backend/secrets:/app/secrets:ro \
  -v /models:/models:ro \
  -p 8080:8080 \
  --name pocket-journal-api \
  pocket-journal:latest
```

**Docker Compose:**
```bash
docker-compose up -d
docker-compose logs -f pocket-journal
docker-compose down
```

**Configuration:**
```yaml
# docker-compose.yml
version: '3.8'
services:
  pocket-journal:
    image: pocket-journal:latest
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - FLASK_ENV=production
      - FIREBASE_CREDENTIALS_JSON=${FIREBASE_CREDENTIALS_JSON}
    volumes:
      - ./Backend/secrets:/app/secrets:ro
      - /models:/models:ro
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## ENVIRONMENT CONFIGURATION

### Required Environment Variables

```bash
# Firebase
FIREBASE_CREDENTIALS_JSON='{...json string...}'  # OR
FIREBASE_CREDENTIALS_PATH=/app/secrets/firebase-adminsdk.json

# External APIs
GEMINI_API_KEY=your_key_here
TMDB_API_KEY=your_key_here
SPOTIFY_CLIENT_ID=your_id_here
SPOTIFY_CLIENT_SECRET=your_secret_here

# Server
FLASK_ENV=production|development
PORT=8080
DEBUG=false

# ML Models
MODEL_SOURCE=local|gcs|s3
MODEL_STORE_PATH=/models  # For local model storage
MODEL_CACHE_DIR=/tmp/models
MODEL_DOWNLOAD_ON_STARTUP=false

# Logging
LOG_LEVEL=INFO|DEBUG
```

---

## DATABASE SETUP

### Firestore Initialization

**Create Collections:**
```bash
# Run database initialization script
python Backend/scripts/db/database_manager.py init
```

**Security Rules:**
```firestore
# Deploy via Firebase Console or CLI
firebase deploy --only firestore:rules
```

**Indexes:**
Create required composite indexes (see Database.md for list):

```bash
firebase deploy --only firestore:indexes
```

---

## MODEL DOWNLOADS

### Pre-download Models (Optional)

```bash
python Backend/scripts/download_models.py
```

This downloads:
- RoBERTa (mood detection): ~500MB
- BART (summarization): ~1.5GB
- Qwen2 (insights, if use_gemini=false): ~4GB
- Sentence-Transformers (embeddings): ~500MB

**Total:** ~6.5GB

---

## HEALTH CHECKS

### Liveness Probe

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-01-15T10:30:00Z",
  "checks": {
    "database": {"status": "ok"},
    "models": {"status": "ok"},
    "external_apis": {"status": "ok"}
  }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pocket-journal
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pocket-journal
  template:
    metadata:
      labels:
        app: pocket-journal
    spec:
      containers:
      - name: api
        image: pocket-journal:latest
        ports:
        - containerPort: 8080
        
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
            nvidia.com/gpu: "1"
          limits:
            memory: "8Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
        
        env:
        - name: FIREBASE_CREDENTIALS_JSON
          valueFrom:
            secretKeyRef:
              name: firebase-creds
              key: credentials.json
        
        - name: GEMINI_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: gemini
```

---

## MONITORING & LOGGING

### Logging Setup

Logs are output to stdout (for container capture):

```
[2025-01-15 10:30:00] INFO Starting Pocket Journal API...
[2025-01-15 10:30:01] INFO Loaded RoBERTa model
[2025-01-15 10:30:02] INFO Firebase initialized
[2025-01-15 10:30:03] INFO Flask server running on 0.0.0.0:8080
```

**Log Levels:**
- DEBUG: Detailed debugging info
- INFO: Application lifecycle events
- WARNING: Recoverable issues (fallbacks used)
- ERROR: Non-fatal errors
- CRITICAL: Fatal errors requiring shutdown

**ELK Stack Integration (Optional):**
```yaml
# fluent-bit config to ship logs to Elasticsearch
[OUTPUT]
    Name es
    Match *
    Host elasticsearch.default.svc.cluster.local
    Port 9200
```

---

## BACKUP & RECOVERY

### Firestore Backups

**Automated Daily Backup:**
```bash
gcloud firestore export gs://pocket-journal-backups/daily-$(date +%Y%m%d)
```

**Restore from Backup:**
```bash
gcloud firestore import gs://pocket-journal-backups/daily-20250115
```

---

## SCALING STRATEGY

### Horizontal Scaling

**Multiple Instances (Behind Load Balancer):**
```
┌─────────────────────────────────────┐
│       Load Balancer (LB)             │
│       Port 443 (HTTPS)               │
└──────────────┬──────────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
    ┌──▼──┐┌──▼──┐┌──▼──┐
    │Pod 1││Pod 2││Pod 3│
    │8080 ││8080 ││8080 │
    └─────┘└─────┘└─────┘
       │       │       │
       └───────┼───────┘
               │
         ┌─────▼─────┐
         │ Firestore │
         │ (Shared)  │
         └───────────┘
```

**Auto-Scaling Policy:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: pocket-journal-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: pocket-journal
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## RELEASE PROCESS

## Pre-Release Checklist

- [ ] All tests passing (unit + integration)
- [ ] Code reviewed by 2+ team members
- [ ] API documentation updated
- [ ] Database migrations tested
- [ ] Performance tests pass (< 2s response time)
- [ ] Security scan clean (no CVEs)
- [ ] Release notes prepared

### Release Steps

1. **Tag Release:**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **Build Docker Image:**
   ```bash
   docker build -t pocket-journal:1.0.0 .
   docker push registry/pocket-journal:1.0.0
   ```

3. **Deploy to Staging:**
   ```bash
   kubectl set image deployment/pocket-journal-staging \
     pocket-journal=registry/pocket-journal:1.0.0 \
     --record
   ```

4. **Run Smoke Tests:**
   ```bash
   pytest tests/smoke/
   ```

5 **Canary Deployment** (Optional):
   - Deploy to 10% of production pods
   - Monitor for 1 hour
   - Gradually increase to 100%

6. **Deploy to Production:**
   ```bash
   kubectl set image deployment/pocket-journal-prod \
     pocket-journal=registry/pocket-journal:1.0.0 \
     --record
   ```

7. **Rollback Plan** (if needed):
   ```bash
   kubectl rollout undo deployment/pocket-journal-prod
   ```

---

## TROUBLESHOOTING

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Models not loaded | Model path wrong | Check MODEL_STORE_PATH env var |
| Firebase auth fails | Invalid credentials | Verify FIREBASE_CREDENTIALS_JSON |
| OOM killed | Large batch size | Reduce batch_size in config.yml |
| Slow inference | CPU only | Enable GPU with docker --gpus flag |
| Database timeout | Connection pool exhausted | Increase pool size in config |

### Debug Logs

```bash
# Enable DEBUG logging
export LOG_LEVEL=DEBUG
python app.py

# Check model loading
python -c "from ml.utils.model_loader import resolve_model_path; print(resolve_model_path('mood_detection', 'roberta', 'v2'))"

# Verify Firestore connection
python -c "from persistence.db_manager import DBManager; print(DBManager().db.collection('users').limit(1).get())"
```

---

**END OF DEPLOYMENT GUIDE**

