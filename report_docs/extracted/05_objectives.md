# Objectives (Academic Formulation)

This document restates system-level aims as measurable research and engineering objectives. Each objective is expressed with explicit success criteria and validation procedures suitable for academic evaluation and reproducible reporting.

1. Objective: Accurate multi-label affective inference
   - Target: A multi-class F1 score (macro) ≥ 0.85 on a held-out annotated journal corpus covering seven emotion categories (anger, disgust, fear, happy, neutral, sad, surprise).
   - Validation: Standard cross-validation with stratified folds; report precision, recall and F1 per label; provide confusion matrices and confidence intervals.

2. Objective: High-fidelity abstractive summarization of entries
   - Target: ROUGE-L ≥ 0.42 and human-rated coherence ≥ 4.0/5 on a blinded evaluation set.
   - Validation: Automated ROUGE evaluation and human annotation on a 200-entry sample using inter-annotator agreement (Cohen's kappa ≥ 0.7).

3. Objective: Robust semantic representation for retrieval and personalization
   - Target: Embedding-driven retrieval recall ≥ 0.90 for semantically related entries and embedding dimensionality consistent with 384-D vectors.
   - Validation: Nearest-neighbour retrieval tasks and mean reciprocal rank (MRR) evaluation on curated query–document pairs.

4. Objective: Context-aware recommendation relevance and diversity
   - Target: Recommendation relevance measured by click-through rate (CTR) ≥ 0.15 and diversity metric (e.g., unique items ratio) ≥ 0.95 across returned lists; response latency p95 ≤ 500 ms for 10-item responses.
   - Validation: A/B evaluation on interaction logs (or simulated user studies), report CTR, precision@k, recall@k, and diversity indices; measure latency under representative load.

5. Objective: Time-bounded insight synthesis with structured output
   - Target: Generate structured insight documents (goals, progress, negative behaviors, remedies, appreciation, conflicts) within p95 latency ≤ 2 s (cloud LLM) or ≤ 5 s (local LLM), and qualitative usefulness score ≥ 4.0/5 from user reviewers.
   - Validation: Human evaluation of produced insights for actionability and fidelity; automatic schema validation for required fields.

6. Objective: Data protection and per-user isolation
   - Target: Every API request requiring authentication must validate a Firebase ID token and enforce uid-based access controls; zero incidents of unauthorized data exposure in audits.
   - Validation: Security audit of Firestore rules and penetration testing; automated unit tests that exercise authorization checks.

7. Objective: System reliability and graceful degradation
   - Target: System availability ≥ 99% and deterministic fallbacks for missing ML components (e.g., truncated summaries when summarizer is unavailable).
   - Validation: Synthetic failure injection tests and monitoring of uptime and fallback activation rates.

8. Objective: Scalability and performance
   - Target: Support ≥ 1,000 concurrent requests with median API latency within 500 ms under representative workloads; storage architecture to accommodate ≥ 10M journal documents.
   - Validation: Load testing (e.g., k6, Locust) and capacity planning reports.

9. Objective: Reproducibility and documentation for academic use
   - Target: Publicly available extraction of model configuration, dataset splits, hyperparameters and evaluation scripts enabling reproducibility; documentation sufficient for independent replication of core experiments.
   - Validation: Inclusion of model resolution paths, config.yml, and training/inference scripts; replication checklist and expected outputs.

Notes on measurement: Each objective requires explicit evaluation datasets and protocols that are documented in the accompanying testing and results sections; quantitative targets are intended for research reporting and may be refined after initial experimentation.



