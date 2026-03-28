# Security: Pocket Journal Backend

## Authentication Model

### Firebase Auth (Primary)

**Flow**:
1. Client app calls Firebase SDK locally
2. User enters email/password
3. Firebase verifies and returns JWT token (ID token)
4. Client includes token in `Authorization: Bearer <token>` header
5. Backend verifies JWT signature and extracts `uid`

**JWT Structure**:
```json
{
  "iss": "https://securetoken.google.com/{PROJECT_ID}",
  "aud": "{PROJECT_ID}",
  "auth_time": 1711734600,
  "user_id": "firebase_uid_abc123",
  "sub": "firebase_uid_abc123",
  "iat": 1711734600,
  "exp": 1711738200,
  "email": "user@example.com",
  "email_verified": true,
  "firebase": {
    "sign_in_provider": "password"
  }
}
```

**Validation** (Backend):
```python
from firebase_admin import auth

try:
    decoded = auth.verify_id_token(id_token)
    uid = decoded['uid']
    email = decoded['email']
    # Token valid, proceed
except auth.InvalidIdTokenError:
    # Token invalid or expired
    return {"error": "unauthorized"}, 401
```

**Token Expiry**: 1 hour (Firebase default)

**Refresh**: Client refreshes token automatically via Firebase SDK

### No Session State

- **Stateless design**: Each request includes full JWT
- **No server-side sessions**: Reduces DB queries
- **Distributed deployment ready**: Any backend instance can verify token

---

## Authorization Model

### User-Scoped Data Access

**Principle**: Users can only access their own data

**Implementation**:
```python
def get_entries(uid):
    # Extract uid from verified JWT
    user_uid = request.user["uid"]
    
    # Query: filter by uid
    entries = db.collection("journal_entries").where("uid", "==", user_uid).stream()
    return entries

# If user tries to access someone else's entries:
@app.route("/api/v1/entries/<entry_id>")
def get_entry(entry_id):
    user_uid = request.user["uid"]
    entry = db.collection("journal_entries").document(entry_id).get()
    
    if entry.get("uid") != user_uid:
        return {"error": "forbidden"}, 403  # Not their entry
    return entry
```

### Resource Ownership

| Resource | Owner Verification |
|----------|-------------------|
| Journal Entries | entry.uid == request.user.uid |
| Entry Analysis | Query by entry_id, verify entry ownership |
| Embeddings | embedding.uid == request.user.uid |
| Insights | insight.uid == request.user.uid |
| User Vectors | user_vector.uid == request.user.uid |

### Shared Resources

- **Media Cache**: Read-only, shared by all users (populated by backend)
- **Public Health**: Read-only, no auth required

---

## Data Protection

### At Rest

**Firestore Encryption**:
- **Default**: Google-managed encryption (AES-256)
- **Enhanced** (optional): Customer-managed encryption keys (Cloud KMS)

**Sensitive Data**:
- Passwords: NOT stored (managed by Firebase Auth)
- API keys: NOT stored in Firestore (env vars only)
- PII: Minimal storage (email, name only)

### In Transit

**HTTP/HTTPS**:
- **Development**: HTTP (localhost only)
- **Production**: HTTPS mandatory (TLS 1.2+)

**API Example**:
```bash
# Development
curl -H "Authorization: Bearer $TOKEN" http://localhost:5000/api/v1/entries

# Production
curl -H "Authorization: Bearer $TOKEN" https://api.example.com/api/v1/entries
```

### In Motion

**Firestore Network**:
- Private Google-managed network
- Encrypted RPC calls
- DDoS protection included

**External APIs**:
- HTTPS enforced (TMDb, Spotify, Google Books)
- Request/response bodies encrypted

---

## API Security

### Authentication Decorator

```python
from functools import wraps
from firebase_admin import auth

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return {"error": "unauthorized", "message": "Missing token"}, 401
        
        try:
            decoded = auth.verify_id_token(token)
            request.user = {
                "uid": decoded["uid"],
                "email": decoded.get("email"),
            }
        except Exception as e:
            logger.warning("Token verification failed: %s", str(e))
            return {"error": "unauthorized", "message": "Invalid token"}, 401
        
        return f(*args, **kwargs)
    return decorated_function

# Usage
@app.route("/api/v1/entries", methods=["POST"])
@login_required
def create_entry():
    uid = request.user["uid"]  # Guaranteed to exist
    # ... create entry for this user
```

### CORS Configuration

```python
from flask_cors import CORS

CORS(app, 
     origins=["https://example.com", "https://app.example.com"],
     methods=["GET", "POST", "PUT", "DELETE"],
     allow_headers=["Authorization", "Content-Type"],
     max_age=3600)
```

### Input Validation

**All user inputs validated**:
```python
# Entry text: Required, non-empty, max length
entry_text = request.get_json().get("entry_text", "").strip()
if not entry_text:
    return {"error": "invalid_input"}, 400
if len(entry_text) > 100000:  # 100KB max
    return {"error": "payload_too_large"}, 413

# Query parameters: Type checking
limit = request.args.get("limit", 10, type=int)
if limit < 1 or limit > 100:
    return {"error": "invalid_input"}, 400
```

### Rate Limiting

**Client-side** (recommended):
- Max 5 recommendations/minute per user
- Max 10 searches/minute per user
- Max 3 insights generation/day per user

**Server-side** (if needed):
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.user["uid"])

@app.route("/api/v1/generate_insights", methods=["POST"])
@limiter.limit("3 per day")
@login_required
def generate_insights():
    # Max 3 calls per user per day
    ...
```

**Provider-level**:
- Implement backoff for 429 responses
- Monitor quota usage

---

## Secrets Management

### Environment Variables

**Sensitive Secrets** (Never hardcode):
```bash
# .env (local development only)
FIREBASE_CREDENTIALS_PATH=./secrets/firebase-key.json
TMDB_API_KEY=sk_live_abc123...
SPOTIFY_CLIENT_SECRET=client_secret_xyz...
GOOGLE_API_KEY=AIzaSyD...
GOOGLE_BOOKS_API_KEY=AIzaSyD...
```

**Load via python-dotenv**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
FIREBASE_CREDS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
```

### Production Secrets

**Option 1: Google Cloud Secret Manager**
```python
from google.cloud import secretmanager

def get_secret(secret_id, version_id="latest"):
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

api_key = get_secret("tmdb_api_key")
```

**Option 2: CI/CD Pipeline Secrets**
```yaml
# GitHub Actions example
jobs:
  deploy:
    env:
      TMDB_API_KEY: ${{ secrets.TMDB_API_KEY }}
      FIREBASE_CREDENTIALS_PATH: ${{ secrets.FIREBASE_CREDENTIALS_PATH }}
```

### Secrets Rotation

**Policy**: Rotate keys every 90 days

**Process**:
1. Generate new key in provider console
2. Update secret manager or CI/CD
3. Restart application (picks up new key)
4. Verify new key works (monitor logs for failures)
5. Disable old key (provider console)

**Automation** (Optional):
```python
# Scheduled task (runs weekly, checks key age)
@scheduled_job('cron', day='*/7')
def check_key_rotation():
    key_age = datetime.now() - key_created_date
    if key_age > timedelta(days=85):  # 90-day max, alert at 85
        alert_ops("Key rotation needed")
```

---

## Abuse Prevention

### Rate Limiting

**Per-User Quotas** (Configurable):
```
Recommendations: 5 requests/minute
Search: 10 requests/minute
Insights: 3 requests/day
Entry creation: 100 entries/day
```

**Implementation**:
```python
from redis import Redis
from datetime import datetime, timedelta

redis_client = Redis()

def check_rate_limit(user_id, action, limit, window):
    key = f"ratelimit:{user_id}:{action}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, window)
    
    if current > limit:
        remaining = redis_client.ttl(key)
        return {
            "error": "rate_limited",
            "retry_after": remaining
        }, 429
    return None

# Usage
@app.route("/api/v1/generate_insights", methods=["POST"])
@login_required
def generate_insights():
    error = check_rate_limit(request.user["uid"], "insights", limit=3, window=86400)
    if error:
        return error
    # ... proceed
```

### Input Sanitization

**Prevent injection attacks**:
```python
# Sanitize entry text (remove scripts, etc.)
import bleach

entry_text = bleach.clean(entry_text, tags=[], strip=True)

# Validate email format
from email_validator import validate_email, EmailNotValidError

try:
    validate_email(email)
except EmailNotValidError:
    return {"error": "invalid_email"}, 400
```

### Account Takeover Prevention

**Firebase handles**:
- Password strength requirements
- Brute force protection (after 5 failed attempts)
- Suspicious sign-in alerts

**Backend-level**:
- Log all auth actions
- Alert on unusual access patterns
- Require re-authentication for sensitive ops

```python
# Log auth events
logger.info("AUTH_EVENT: action=login uid=%s email=%s ip=%s",
            uid, email, request.remote_addr)

# Sensitive operation: delete all entries
if request.headers.get("X-Confirm-Delete") != "yes":
    return {"error": "confirmation_required"}, 400
```

---

## Firestore Security Rules

**Template** (configure in Firebase Console):

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // User can only read/write their own entries
    match /journal_entries/{document=**} {
      allow read, create, update, delete: 
        if request.auth != null && 
           request.auth.uid == resource.data.uid;
    }
    
    // Entry analysis: readable by owner, writable by service
    match /entry_analysis/{document=**} {
      allow read: 
        if request.auth != null;  // All users can read
      allow write: 
        if request.auth.token.firebase.identities["google.com"][0] == 
           "service-account@...";  // Service account only
    }
    
    // Media cache: read-only for users, write for service
    match /media_cache/{document=**} {
      allow read: 
        if request.auth != null;
      allow write: 
        if false;  // Disabled (only backend writes)
    }
    
    // Default deny
    match /{document=**} {
      allow read, write: if false;
    }
  }
}
```

**Key Principles**:
1. **Deny by default**: Start with `allow: false`
2. **Explicit grants**: Only allow specific operations
3. **User isolation**: Check `request.auth.uid == resource.data.uid`
4. **Service accounts**: Use for backend writes

---

## Audit Logging

**Log all sensitive operations**:
```python
import logging
from datetime import datetime

audit_logger = logging.getLogger("audit")

def log_audit(action, user_id, resource, result, details=""):
    audit_logger.info({
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "user_id": user_id,
        "resource": resource,
        "result": result,  # success | failure
        "details": details
    })

# Examples
log_audit("entry_create", uid, "journal_entries", "success", f"entry_id={entry_id}")
log_audit("insights_generate", uid, "insights", "success", f"days=28")
log_audit("export_request", uid, "entries", "failure", "unauthorized_format")
```

**Storage**:
- Cloud Logging (GCP)
- CloudWatch Logs (AWS)
- ELK Stack (self-hosted)

**Retention**: Minimum 90 days

---

## Vulnerability Management

### Known Vulnerabilities

**Dependency Scanning**:
```bash
# Python
pip install safety
safety check

# Or via GitHub
# Setup: GitHub → Settings → Security → Dependabot → Enable
```

**Response Process**:
1. Security alert triggered (CVE)
2. Assess severity (Critical → Immediate action)
3. Update dependency (if patch available)
4. Test in staging
5. Deploy to production
6. Document in SECURITY.md

### Security Headers

```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    return response
```

---

## Security Checklist

- [ ] HTTPS enforced in production
- [ ] All API endpoints require authentication
- [ ] Input validation on all endpoints
- [ ] Rate limiting implemented
- [ ] Secrets stored in secure manager (not env files)
- [ ] API keys rotated every 90 days
- [ ] Firestore security rules deployed
- [ ] Audit logging enabled
- [ ] CORS configured to specific domains
- [ ] SQL injection prevention (N/A, using Firestore)
- [ ] CSRF protection (N/A, stateless JWT)
- [ ] Dependency vulnerabilities monitored
- [ ] Security headers set
- [ ] Error messages don't leak sensitive info
- [ ] PII not logged
- [ ] Data encryption at rest configured
- [ ] Backups encrypted and tested

---

## Incident Response

### Breach Scenario: API Key Compromised

1. **Detect**: Monitor API calls for unusual patterns
2. **Contain**: Immediately disable key in provider console
3. **Assess**: Check logs for unauthorized usage
4. **Notify**: Alert users if their data accessed
5. **Rotate**: Generate new key, update secrets
6. **Test**: Verify new key works, old key disabled
7. **Review**: Post-mortem on how compromise occurred

### Breach Scenario: Firebase Account Compromised

1. **Detect**: Alert on unusual sign-in (Firebase built-in)
2. **Contain**: User resets password
3. **Assess**: Check what data was accessed (audit logs)
4. **Notify**: User of breach
5. **Enforce**: Require password reset + MFA


