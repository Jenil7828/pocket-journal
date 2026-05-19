# 📄 Testing Strategy and Validation

## Testing Objectives

The testing strategy is designed to ensure correctness, robustness and reproducibility of the system. Tests target: (1) functional correctness of API endpoints and service logic; (2) fidelity and stability of ML inference components; (3) integration correctness across service–database–model interactions; and (4) system-level performance and reliability under representative workloads.

## Test Levels

1. Unit tests
   - Scope: Isolated modules and functions in services, utilities and persistence wrappers.
   - Technique: Mock external dependencies (Firestore client, model predictors) to verify business logic and error handling.
   - Examples: validation of parameter parsing, correct invocation of DBManager methods, authorization checks.

2. Integration tests
   - Scope: Service-to-database and service-to-model interactions.
   - Technique: Use an integration test Firestore instance or emulator and replace heavy models with lightweight fixtures where appropriate.
   - Examples: process_entry end-to-end with stubbed predictors; verify insert_analysis and journal_embeddings writes.

3. System tests
   - Scope: End-to-end scenarios through the HTTP API under realistic configurations.
   - Technique: Start the application in a test environment; exercise API endpoints and validate responses against schemas.
   - Examples: create entry → list entries → generate insights → get insights.

4. Performance and load testing
   - Scope: Measure latency, throughput and resource usage.
   - Technique: Use load testing tools (e.g., k6, Locust) to simulate concurrent users and measure p95/p99 latencies.
   - Targets: Recommendation p95 ≤ 500 ms (10-item), Entry processing median under defined thresholds depending on model hardware.

5. Security and privacy testing
   - Scope: Authorization enforcement and data isolation checks.
   - Technique: Automated tests that attempt cross-user access and verify Firestore rules and service checks prevent exposure.

## Validation Procedures and Metrics

- Unit test coverage: Aim for coverage thresholds for critical modules (≥ 80% for core services).
- Model validation: Evaluate ML components on holdout datasets reporting precision, recall, F1, ROUGE metrics, and inference latency under target hardware.
- End-to-end acceptance: Maintain a set of acceptance tests that must pass before publishing an artifact or running experiments.
- Regression tests: Capture known failure modes (e.g., model unavailable, DB timeouts) and confirm graceful degradation.

## Example Test Cases

1. Test: Create entry with valid input
   - Input: authenticated request with entry_text
   - Mocks: summarizer returns expected summary; predictor returns fixed emotion probabilities
   - Assertions: response contains entry_id, summary and mood; `entry_analysis` document exists in test DB

2. Test: Search with invalid limit parameter
   - Input: GET /api/v1/journal/search?limit=abc
   - Assertions: 400 response with explanatory error

3. Test: Recommendation ranking stability
   - Setup: Populate media cache with synthetic items and create a user_vectors document
   - Action: Call movie recommendation endpoint with identical request multiple times
   - Assertions: deterministic top-k ordering given fixed random seeds; scores are within expected ranges

4. Test: Insights generation error handling
   - Input: enable_llm=true, but LLM backend returns malformed JSON
   - Assertions: endpoint returns 500 with logged exception and no partial insight document persisted

## Test Data and Fixtures

- Use small, representative corpora for unit and integration tests; anonymize or synthesize example entries to avoid personal data exposure.
- Provide fixtures for model outputs (probabilities, summaries, embeddings) to reduce test resource requirements.

## Continuous Integration and Reproducibility

- Integrate test suites into CI pipelines; run unit tests on every commit and full integration suites on merge events.
- Document environment requirements for reproducible experiments (Python version, dependency versions, model artifacts, and config.yml). Provide scripts to prepare test Firestore instances and to seed media cache fixtures.

