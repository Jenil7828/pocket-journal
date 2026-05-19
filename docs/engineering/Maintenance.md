# MAINTENANCE & OPERATIONS GUIDE
## Pocket Journal — Operational Procedures & Support

**Document Version:** 1.0  
**Last Updated:** April 18, 2026

---

## TABLE OF CONTENTS
1. [Monitoring & Observability](#monitoring--observability)
2. [Logging Strategy](#logging-strategy)
3. [Alerting & Incident Management](#alerting--incident-management)
4. [Routine Maintenance](#routine-maintenance)
5. [Performance Optimization](#performance-optimization)
6. [Security & Compliance](#security--compliance)
7. [Disaster Recovery](#disaster-recovery)

---

## MONITORING & OBSERVABILITY

### Key Metrics to Monitor

#### API Health Metrics
- Request rate (req/sec)
- Response time (p50, p95, p99)
- Error rate (5xx, 4xx)
- Availability (uptime %)

#### ML Model Metrics
- Inference latency (mood, summary, insights)
- Model accuracy (mood detection F1 score)
- GPU utilization
- Memory usage

#### Database Metrics
- Query latency (p95)
- Read/write throughput (ops/sec)
- Collection sizes (GB)
- Index usage

#### User Metrics
- Active users (DAU, MAU)
- Entries created per day
- API endpoint usage distribution
- Error rate by endpoint

### Monitoring Stack (Recommended)

```
┌─────────────────────────────────┐
│  Application (Flask)             │
│  - Prometheus metrics export     │
│  - Custom metrics (mood acc)     │
└──────────────┬──────────────────┘
               │
    ┌──────────▼──────────┐
    │   Prometheus        │
    │   (Time-series DB)  │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Grafana           │
    │   (Dashboards)      │
    └─────────────────────┘
```

**Prometheus Config:**
```yaml
global:
  scrape_interval: 15s
  
scrape_configs:
  - job_name: 'pocket-journal'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
```

**Key Dashboards:**
1. System Health (uptime, errors, latency)
2. ML Performance (inference times, accuracy)
3. Database (query times, throughput)
4. Business Metrics (users, entries, moods)

---

## LOGGING STRATEGY

### Log Levels & Categories

| Level | Category | Example |
|-------|----------|---------|
| DEBUG | Development | "Tokenizing text: 'hello world'" |
| INFO | Lifecycle | "Entry created: entry_123" |
| WARNING | Recoverable | "Mood confidence below threshold, using default" |
| ERROR | Non-fatal | "Summarization failed, using truncation" |
| CRITICAL | Fatal | "Firebase initialization failed" |

### Log Retention

```bash
# Logs rotated daily, kept for 30 days
# Location: /var/log/pocket-journal/

-rw-r--r-- 1 root root 128M Jan 15 10:00 app.log
-rw-r--r-- 1 root root 92M  Jan 14 10:00 app.log.1
-rw-r--r-- 1 root root 85M  Jan 13 10:00 app.log.2
```

### Structured Logging Example

```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "services.mood_detection",
  "message": "Mood prediction successful",
  "context": {
    "user_id": "uid_abc123",
    "entry_id": "entry_def456",
    "mood": "happy",
    "confidence": 0.85,
    "latency_ms": 420
  }
}
```

### Centralized Logging (ELK Stack)

**Elasticsearch Index Template:**
```json
{
  "template": "pocket-journal-*",
  "mappings": {
    "properties": {
      "timestamp": {"type": "date"},
      "level": {"type": "keyword"},
      "logger": {"type": "keyword"},
      "message": {"type": "text"},
      "context": {"type": "object"}
    }
  }
}
```

---

## ALERTING & INCIDENT MANAGEMENT

### Alert Rules

#### Critical Alerts (Page PagerDuty)
```
1. Service Down (5min continuous error)
   - Condition: Error rate > 50% for 5 minutes
   - Action: Page on-call engineer

2. High Error Rate
   - Condition: 5xx errors > 1% for 10 minutes
   - Action: Page on-call engineer

3. High Latency
   - Condition: p95 response time > 5 seconds
   - Action: Page on-call engineer

4. Database Unavailable
   - Condition: Firestore connection failures > 10/min
   - Action: Page on-call engineer
```

#### Warning Alerts (Email)
```
1. High Disk Usage
   - Condition: Disk usage > 80%
   - Action: Email ops team

2. Model Accuracy Drop
   - Condition: Mood detection F1 < 0.80
   - Action: Email ML team

3. Memory Pressure
   - Condition: Memory usage > 85%
   - Action: Email ops team
```

### Incident Response

**Severity Levels:**
- **SEV1**: Service down, no workaround (RTO < 15min)
- **SEV2**: Major degradation (RTO < 1 hour)
- **SEV3**: Minor issues (RTO < 4 hours)
- **SEV4**: Low-priority (fix in next release)

**Incident Workflow:**
1. Alert triggered → Page on-call engineer
2. Engineer acknowledges incident
3. Create incident in Jira with SEV level
4. Investigate root cause
5. Implement fix or workaround
6. Deploy and verify fix
7. Post-incident review (within 24 hours)

---

## ROUTINE MAINTENANCE

### Daily Tasks

**Automated:**
- [ ] Health check passes
- [ ] Logs monitored for errors
- [ ] Backup completed

**Manual:‌**
- [ ] Review error logs (if any)
- [ ] Check API latency trends
- [ ] Verify no pending security patches

### Weekly Tasks

- [ ] Review performance metrics
- [ ] Check database growth trends
- [ ] Update dependencies (security patches)
- [ ] Review user feedback
- [ ] Test rollback procedures

### Monthly Tasks

- [ ] Database maintenance (analyze, optimize)
- [ ] Cache cleanup (media_cache_* TTL)
- [ ] Log archival (compress old logs)
- [ ] Security audit
- [ ] Capacity planning

### Quarterly Tasks

- [ ] Model retraining (if accuracy dips below 80%)
- [ ] Performance optimization review
- [ ] Disaster recovery drill
- [ ] Documentation update

### Annual Tasks

- [ ] Complete security assessment
- [ ] Dependency audit (check for EOL packages)
- [ ] Architecture review
- [ ] Budget & cost optimization

---

## PERFORMANCE OPTIMIZATION

### Database Query Optimization

**Identify Slow Queries:**
```python
# Enable query logging
firebase.Client.enable_debug()

# Or use Firestore Query Stats
# From Firebase Console → Firestore → Stats
```

**Common Issues & Fixes:**

| Issue | Symptom | Fix |
|-------|---------|-----|
| Missing index | Queries timeout | Create composite index |
| Inefficient filter | Slow result | Add indexed field to WHERE |
| Large result set | Memory spike | Add LIMIT constraint |
| N+1 queries | Repeated queries | Batch queries or denormalize |

**Example Optimization:**

Before:
```python
# N+1 query
entries = db.collection('journal_entries').where('uid', '==', uid).get()
for entry in entries:
    analysis = db.collection('entry_analysis').where('entry_id', '==', entry.id).get()
    # Use analysis
```

After:
```python
# Batch fetch
entries = db.collection('journal_entries').where('uid', '==', uid).get()
entry_ids = [e.id for e in entries]

analyses = db.collection('entry_analysis').where('entry_id', 'in', entry_ids).get()
analysis_map = {a['entry_id']: a for a in analyses}

for entry in entries:
    analysis = analysis_map.get(entry.id)
    # Use analysis
```

### ML Model Optimization

**Quantization:**
```python
# Use fp16 instead of fp32
model = model.half()  # For GPU
quantized_model = torch.quantization.quantize_dynamic(model, {torch.nn.Linear}, dtype=torch.qint8)
```

**Batch Processing:**
```python
# Process multiple entries in one inference call
batch_size = 32
for i in range(0, len(texts), batch_size):
    batch = texts[i:i+batch_size]
    results = model.predict_batch(batch)
```

### API Response Caching

```python
# Cache mood analysis results
@app.route('/api/entries/<entry_id>')
@cache.cached(timeout=3600)  # 1 hour
def get_entry(entry_id):
    return db.get_entry(entry_id)
```

---

## SECURITY & COMPLIANCE

### Security Checklist

- [ ] All API endpoints require authentication
- [ ] Secrets not hardcoded (use env vars)
- [ ] HTTPS/TLS enabled (port 443)
- [ ] CORS whitelisting configured
- [ ] Rate limiting enabled (100 req/min per IP)
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM usage)
- [ ] CSRF protection enabled
- [ ] Security headers set (CSP, X-Frame-Options, etc.)
- [ ] Dependencies scanned for CVEs

### Firestore Security Rules Audit

```firestore
# Run monthly audit
firebase rules:test --debug-rules
```

### Data Privacy Compliance

**GDPR:**
- [ ] Users can export personal data (/api/export/*)
- [ ] Data retention policy enforced (see Database.md)
- [ ] Right to deletion implemented
- [ ] Privacy policy published

**CCPA (California):**
- [ ] Users can request data deletion
- [ ] Opt-out from data sharing

### Vulnerability Management

**CV E Scanning:**
```bash
# Weekly dependency scan
pip check  # Or Safety check
safety check -r requirements.txt

# GitHub Dependabot: Auto-alert on CVEs
# Enable in Settings → Code security & analysis
```

**Response Plan:**
1. Identify affected versions
2. Update to patched version
3. Test in staging
4. Deploy hotfix to production
5. Document in release notes

---

## DISASTER RECOVERY

### RTO/RPO Goals

| Scenario | RTO | RPO |
|----------|-----|-----|
| Single instance failure | 5 min | 0 min (state-less) |
| Database corruption | 1 hour | < 24 hours |
| Complete region failure | 4 hours | < 24 hours |
| Data breach | 24 hours (notification) | N/A |

### Backup Strategy

**Daily Firestore Backup:**
```bash
gcloud firestore export \
  gs://pocket-journal-backups/daily-$(date +%Y%m%d) \
  --async
```

**Weekly Manual Backup:**
```bash
gcloud firestore export \
  gs://pocket-journal-backups/weekly-$(date +%Y%W) \
  --async
```

**Retention:**
- Daily: 30 days
- Weekly: 1 year
- Monthly: Indefinite

### Disaster Recovery Procedures

#### Scenario 1: Database Corruption

```bash
# 1. Stop serving traffic (take API offline)
kubectl scale deployment/pocket-journal-prod --replicas=0

# 2. Restore from backup
gcloud firestore import gs://pocket-journal-backups/daily-20250115

# 3. Verify restore integrity
python scripts/db/verify_database.py

# 4. Resume traffic
kubectl scale deployment/pocket-journal-prod --replicas=3
```

#### Scenario 2: Region Failure

```bash
# 1. Firestore automatically handles multi-region failover
#    (if multi-region replication enabled)

# 2. Update DNS/load balancer to alternate region (if needed)

# 3. Verify service health in new region
curl https://api-backup.pocketjournal.io/api/health
```

#### Scenario 3: Data Breach

```
1. Confirm breach scope
2. Notify users affected (within 48 hours)
3. Force password reset
4. Rotate API keys
5. Review access logs
6. Post-incident security review
```

### Disaster Recovery Testing

**Monthly DR Drills:**
```bash
# 1. Take snapshot of current database
gcloud firestore export gs://pocket-journal-backups/test-$(date +%s)

# 2. Restore to test environment
gcloud firestore import gs://pocket-journal-backups/test-123456

# 3. Run smoke tests
pytest tests/smoke/

# 4. Verify data integrity
python scripts/db/verify_database.py

# 5. Document results
# Expected: All tests pass within RTO < 1 hour
```

---

## SUPPORT & ESCALATION

### Support Hierarchy

```
Tier 1 (L1): Support team
  - Handle user issues
  - Collect logs
  - Check status page
  - Escalate to L2 if needed

Tier 2 (L2): Engineering team
  - Diagnose issues
  - Implement hotfixes
  - Escalate to L3 if critical

Tier 3 (L3): Architects/On-call
  - Major outages
  - Infrastructure issues
  - Architecture changes
```

### On-Call Rotation

```
Week 1: Alice (Mon-Fri) + Bob (Sat-Sun)
Week 2: Charlie + Dave
Week 3: Eve + Frank
Week 4: Grace + Henry
(Repeat)

Handoff: Friday 4 PM UTC
```

### Documentation for Support Team

- [ ] Runbook for common issues
- [ ] API documentation (for request tracing)
- [ ] Database schema guide
- [ ] Troubleshooting checklist
- [ ] Escalation contacts

---

**END OF MAINTENANCE GUIDE**

