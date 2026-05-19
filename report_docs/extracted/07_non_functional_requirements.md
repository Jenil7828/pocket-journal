# 🔧 Non-Functional Requirements

## Performance Requirements

### NFR1: Response Time
- **API Response Time**: <500ms for 95th percentile
  - Journal list: <200ms
  - Recommendation request: <500ms
  - Insights generation: <2s (Gemini), <5s (Qwen2)
  - Search query: <200ms
- **Model Inference Time**:
  - Mood detection: <500ms per entry (GPU), <2s (CPU)
  - Summarization: <1s per entry (GPU), <3s (CPU)
  - Embedding generation: <100ms per summary
- **Database Query Time**:
  - Simple retrieval (index hit): <50ms
  - Complex filtering with date range: <200ms

### NFR2: Throughput
- **Concurrent Users**: System must handle ≥1000 simultaneous requests
- **Requests Per Second**: >100 RPS sustained
- **Batch Processing**: Support batch operations for insights generation (5+ entries)

### NFR3: Latency Optimization
- **Model Loading**: Eager load models at startup (loaded before first user request)
- **Caching**: Media cache refreshed every 24 hours
- **Connection Pooling**: Firestore connection reuse across requests
- **No Blocking Operations**: All I/O operations properly async/concurrent where possible

## Scalability Requirements

### NFR4: Horizontal Scaling
- **Stateless Design**: Flask instances can be replicated independently
- **Database Scaling**: Firestore automatic sharding supports >1M requests/day
- **Model Scaling**: Can add GPU instances without modifying code
- **Load Balancing**: Ready for load balancer (nginx, Kubernetes)

### NFR5: Data Capacity
- **Storage Capacity**:
  - Per-user entries: Support >50,000 entries per user
  - Total system entries: >10 million entries
  - Embeddings: 384 dimensions × 10M entries = ~1.5GB
  - Media cache: ~500 items per type = ~2GB
- **Query Performance**: Maintain <500ms latency even at scale

### NFR6: Cost Efficiency
- **Model Inference**: ONNX optimization for faster inference
- **Float16 Precision**: GPU float16 for memory efficiency
- **Batch Processing**: Batch embeddings for cost reduction
- **Cache Hit Rate**: Maintain >95% media cache hit rate

## Reliability Requirements

### NFR7: Availability
- **Uptime**: 99% monthly availability (2.88 hours downtime allowed)
- **Graceful Degradation**:
  - If mood model fails: Skip mood detection, return empty mood object
  - If summary model fails: Return truncated summary (200 chars)
  - If embedding fails: Entry created without embeddings (recommendations unaffected)
  - If recommend engine fails: Return error with 503 status, retry suggestion
- **Connection Resilience**:
  - Firestore connection failures: Auto-retry with exponential backoff
  - API timeouts: Request timeout after 30s

### NFR8: Data Integrity
- **ACID Compliance**: Firestore transactions for multi-field updates
- **Atomic Operations**:
  - Entry creation includes mood + summary + embedding atomicity
  - Insight deletion includes mapping cleanup
- **Data Validation**: All inputs validated before storage
- **Backup**: Firestore automatic backup (managed by GCP)

### NFR9: Fault Tolerance
- **Model Failure Handling**: System continues without specific model output
- **Database Connection Loss**: Queue requests, retry when available
- **Provider API Failures**: Fallback to cached data
- **Partial Success**: Return partial results if some operations fail

## Security Requirements

### NFR10: Authentication
- **Method**: Firebase ID tokens (JWT)
- **Token Verification**: All endpoints except health/home require valid JWT
- **Session Management**: Tokens valid for 1 hour
- **Re-authentication**: Automatic on token expiry

### NFR11: Authorization
- **User Isolation**: uid-based filtering on all queries
- **Field-Level Security**: Sensitive fields (raw_analysis) not returned to client
- **Write Authorization**: User can only modify own entries
- **Delete Authorization**: User can only delete own entries and insights

### NFR12: Data Protection
- **Encryption in Transit**: TLS 1.2+ for all HTTPS connections
- **Encryption at Rest**: Firestore automatic encryption (AES-256)
- **API Keys**: Sensitive APIs (Gemini, Spotify, TMDb) hidden in environment variables
- **Service Account**: Firebase service account JSON protected in secrets/

### NFR13: Input Validation
- **Length Limits**:
  - entry_text: max 5000 characters
  - query: max 500 characters
  - title: max 200 characters
- **Type Validation**: All inputs validated for correct type
- **Injection Prevention**: No SQL/NoSQL injection possible (Firestore parameterized queries)
- **Rate Limiting**: Max 10 interactions per media type per hour

## Maintainability Requirements

### NFR14: Code Organization
- **Modular Structure**: Services, routes, utils clearly separated
- **Domain-Based Routing**: journal, insights, media routes organized by domain
- **Service Abstraction**: Business logic in service layer, not routes
- **Configuration Externalization**: All config values in config.yml

### NFR15: Testability
- **Unit Tests**: Services have minimal external dependencies
- **Mocking**: Database and ML models mockable for unit tests
- **Integration Tests**: Full request/response testing possible
- **Test Coverage**: ≥70% of critical paths covered

### NFR16: Documentation
- **Code Comments**: Non-obvious logic documented
- **API Documentation**: All endpoints documented (Postman collection available)
- **Configuration Guide**: Setup instructions in README, Docker.md
- **Architecture Guide**: System design documented in docs/

### NFR17: Error Handling
- **Error Responses**: Consistent JSON error format with status codes
- **Error Logging**: All errors logged with context (uid, operation, traceback)
- **User Feedback**: Non-technical error messages in API responses
- **Error Recovery**: Automatic retry logic for transient failures

## Compatibility Requirements

### NFR18: Framework Compatibility
- **Flask**: Version 2.0+
- **Python**: Version 3.10+
- **Transformers**: HuggingFace transformers library
- **PyTorch**: PyTorch 1.9+ with CUDA 11.0+ support

### NFR19: Device Compatibility
- **GPU Support**: NVIDIA CUDA 11.0+, RTX/A100
- **CPU Fallback**: Graceful degradation on CPU-only systems
- **Memory Efficiency**: Float16 precision for GPU memory savings

### NFR20: Database Compatibility
- **Firestore SDK**: Firebase Admin SDK 5.0+
- **Collection Structure**: Firestore-specific (no SQL dialect)
- **Query Language**: Firestore query filters

## Compliance Requirements

### NFR21: Privacy Compliance
- **GDPR Ready**: User data export functionality, deletion supported
- **Data Retention**: Configurable data retention (90 days for interactions, 180 for embeddings)
- **Audit Logging**: All access attempts logged

### NFR22: API Standards
- **REST Compliance**: Proper HTTP methods and status codes
- **JSON Format**: All responses in JSON
- **Error Format**: Consistent error JSON schema
- **Pagination**: Limit/offset pagination for list endpoints

## Monitoring Requirements

### NFR23: Observability
- **Structured Logging**: JSON log format for machine parsing
- **Log Levels**: DEBUG, INFO, WARNING, ERROR levels
- **Performance Monitoring**: Response times logged
- **Metrics Tracking**: Model inference times, cache hit rates tracked

### NFR24: Health Monitoring
- **Health Endpoint**: `GET /api/v1/health` returns system status
- **Database Health**: Connectivity check included
- **Model Status**: Model availability checked
- **Alerts**: Ready for integration with monitoring systems (Datadog, Prometheus)

## Configuration Requirements

### NFR25: Environment Configuration
- **Config File**: config.yml with all settings
- **Environment Overrides**: Environment variables override config.yml
- **Dynamic Loading**: Config loaded at startup, no restart needed for data changes
- **Feature Flags**: Toggle-able features (mood_tracking, insights LLM, etc.)

### NFR26: Deployment Configuration
- **Docker Support**: Multi-stage Dockerfile provided
- **Docker Compose**: Production-ready docker-compose.yml
- **Environment Files**: .env files for local development
- **Health Check**: Docker health check configured

## Cost Requirements

### NFR27: Operational Cost
- **Model Storage**: Optimized model sizes (ONNX format)
- **Inference Cost**: Target <$0.01 per user per month for inference
- **Storage Cost**: Target <$0.10 per user per month for database
- **API Calls**: Minimize external API calls (cache aggressively)

### NFR28: Cloud Provider Efficiency
- **GCP Free Tier**: Firestore <50k ops/day free
- **Model Caching**: Cache models locally to avoid re-download
- **Batch Processing**: Batch API calls to reduce requests

## Performance Summary Table

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API Response (p95) | <500ms | TBD | Target |
| Mood Detection | <500ms GPU | Confirmed | ✅ |
| Summarization | <1s GPU | Confirmed | ✅ |
| Recommendation | <500ms | Confirmed | ✅ |
| Uptime | 99% | TBD | Target |
| Concurrent Users | 1000+ | TBD | Target |
| Mood F1 Score | ≥0.85 | Confirmed | ✅ |
| Summary ROUGE-L | ≥0.42 | Confirmed | ✅ |

