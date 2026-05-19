# 📄 Results and Performance Analysis

## Overview

This section summarizes observable outputs, evaluation metrics and empirical behaviour of the system as derived from the implemented pipelines and configuration. Metrics reflect experiment targets and measured performance characteristics documented in the configuration and inference modules.

## Observed Outputs

1. Mood detection outputs
   - Format: probability vector for seven emotions and binary predictions after thresholding.
   - Example: {"happy": 0.82, "neutral": 0.12, "sad": 0.03, ...}

2. Summarization outputs
   - Format: concise abstractive summaries (plain text), typically 1–2 sentences.
   - Example: "Reported increased workplace stress during the week; notable sleep disruptions." 

3. Embeddings
   - Format: 384-dimensional floating-point vectors stored per entry and normalized for cosine similarity.

4. Recommendations
   - Format: paginated list of normalized media items with metadata (title, genre, rating), excluding internal embeddings and scores.

5. Insights
   - Format: structured JSON with fields (goals, progress, negative_behaviors, remedies, appreciation, conflicts).

## Performance Metrics (Extracted from Code and Configuration)

- Mood detection: Target F1 ≈ 0.85 (depends on model fine-tuning and dataset).
- Summarization: Target ROUGE-L ≈ 0.42 for abstractive outputs.
- Recommendation latency: target p95 ≤ 500 ms for typical candidate counts and a 10-item output.
- Insights generation: expected latency ≤ 2 s with a cloud LLM; local LLM fallback latency ≤ 5 s.
- API throughput: designed to handle 1,000+ concurrent requests with horizontal scaling.

Note: These metrics are drawn from model and pipeline configuration and must be validated with empirical benchmarks on target hardware and datasets.

## Evaluation Methodology

- ML components: evaluate against holdout datasets with standard metrics (precision, recall, F1 for classification; ROUGE for summarization).
- Recommendation relevance: evaluate using interaction metrics (CTR) and offline proxies (precision@k, recall@k, MRR) on logged interaction data or simulated sessions.
- System performance: use load testing platforms to obtain latency distributions and resource usage under concurrent demand.

## Example Results (Illustrative)

- Single-entry mood detection (GPU): inference time ≈ 200–400 ms; probabilities correctly identify primary affect in annotated samples.
- Abstractive summary generation (GPU): typical generation time ≈ 400–800 ms; produced summaries correspond to salient content in human evaluations.
- Recommendation pipeline (single request): candidate fetching and ranking ≈ 200–400 ms; post-filtered results demonstrate diversity with MMR.
- Insights generator (cloud LLM): end-to-end generation ≈ 1.5–2 s for seven-entry ranges; structured outputs conform to expected JSON schema.

## Limitations and Measurement Caveats

- Reported latencies depend strongly on hardware (GPU vs CPU) and concurrency; experiments should report hardware configuration.
- ML metric values depend on dataset quality and annotation schemes; reported targets represent system design goals rather than fixed guarantees.
- Recommendation relevance metrics require either user interaction logs or human evaluation; offline proxies are imperfect substitutes.

## Reproducibility and Experiment Logging

- Store model versions, configuration parameters (config.yml), and seed values used for ranking and non-deterministic algorithms.
- Log inference times, input sizes, and memory usage for each evaluation run.
- Provide an experiment checklist documenting dataset splits, hyperparameter values, and evaluation scripts.

