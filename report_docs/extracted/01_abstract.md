# 📄 Abstract

This document provides an academic abstract for an extraction-based intelligent journaling system designed to transform unstructured personal text into structured psychological and behavioral information. The system addresses the challenge of deriving longitudinal emotional signals and actionable recommendations from free-form diary entries by integrating modern transformer-based models with a scalable data architecture.

Problem: Individuals maintain extensive personal journals but lack automated, evidence-based tools to detect emotional states, distill long-form writing into concise representations, and synthesize cross-entry patterns into actionable insights. Manual tagging and retrospective analysis are laborious and inconsistent, limiting the utility of journaling for self-monitoring and behavioral intervention.

System capabilities: The system (a) performs multi-label emotion classification on raw journal text, (b) generates abstractive summaries that preserve semantic content, (c) constructs semantic embeddings for search and personalization, (d) produces context-aware media recommendations informed by user taste and current state, and (e) synthesizes aggregated insights over configurable time windows using large language models.

Technologies: The implementation combines: RoBERTa-based sequence classification for emotion detection; BART-based encoder–decoder models for abstractive summarization; sentence-transformer embeddings (all-mpnet-base-v2) for semantic representation; a hybrid recommendation pipeline employing cosine similarity, maximal marginal relevance (MMR), temporal decay, and hybrid scoring; and an LLM-backed insights generator configurable to use cloud-hosted or local models. The system is deployed as Flask services with Firestore persistence and Firebase authentication.

Contributions: This work documents an end-to-end architecture that (1) operationalizes multi-label affective inference in journaling contexts with configurable thresholds, (2) couples abstractive summarization with embedding-driven personalization to produce context-aware recommendations, (3) formalizes a recommendation ranking strategy combining relevance, diversity, temporal decay and interaction signals, and (4) establishes a reproducible pipeline for synthesizing time-bounded insights using LLMs while preserving per-user data isolation. The extracted artifacts and structured schemas enable reproducible evaluation and integration into research workflows.

Keywords: digital journaling, emotion detection, abstractive summarization, sentence embeddings, recommender systems, large language models, Firestore.


