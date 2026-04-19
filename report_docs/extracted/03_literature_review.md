# 📄 Literature Review

## Overview

This literature review synthesizes research relevant to automatic emotion detection, abstractive summarization, recommendation systems, and digital journaling platforms. The aim is to locate the implemented system within the current scholarly landscape, identify established methods that inform design choices, and articulate the research gaps addressed by the system.

## Emotion Detection Research

Emotion detection from text has evolved from lexicon and rule-based methods to statistical and deep learning approaches. Early work employed sentiment lexicons and bag-of-words models; subsequent advances used recurrent neural networks and attention mechanisms. Transformer-based architectures (BERT, RoBERTa) have established state-of-the-art results in multi-label and multi-class affective tasks due to contextualized representations and pretraining on large corpora.

Key observations:
- Contextual transformers outperform previous architectures on both short social text and longer narrative content.
- Multi-label emotion modelling better captures the co-occurrence of affective states than single-label classifiers.
- Threshold calibration and probability calibration are necessary for reliable deployment in user-facing systems.

Implication for system design: A RoBERTa-derived classifier offers robust multi-label inference for long-form journal text; production use requires attention to threshold selection and calibration on in-domain data.

## Text Summarization Techniques

Summarization research distinguishes extractive techniques (selecting salient spans) from abstractive methods (generating novel summaries). Transformer-based encoder–decoder models (BART, T5) demonstrate strong abstractive performance and generalize well across domains with fine-tuning. Beam search, length penalties and n-gram blocking are standard generation constraints to improve factuality and fluency.

Key observations:
- Abstractive systems require careful handling of hallucination; domain-specific fine-tuning and post-generation filtering mitigate errors.
- For long inputs, truncated or hierarchical encoding strategies preserve salient information.

Implication for system design: Use a BART-like model with adjusted generation parameters and fallback strategies (truncation) to ensure continuity of service when model inference is unavailable.

## Recommendation Systems

Recommendation systems research spans collaborative filtering, content-based methods, and hybrid approaches. Recent trends emphasize neural embeddings, hybrid scoring, diversity-promoting mechanisms (e.g., MMR), and incorporation of temporal dynamics and interaction feedback.

Key observations:
- Hybrid models that combine user history (taste vectors) with contextual intent (current session vectors) deliver better short-term relevance.
- MMR and diversification techniques are effective to reduce redundancy and increase perceived novelty.
- Temporal decay models account for preference drift and recency effects.

Implication for system design: A hybrid recommendation pipeline that blends stable taste vectors with immediate journal-derived intent, combined with MMR and temporal decay, is appropriate for personalized media recommendation in a journaling context.

## Digital Journaling and Clinical Applications

Existing journaling applications primarily focus on storage and retrieval, with a subset offering sentiment tags and simple analytics. Research on digital journaling in mental health contexts highlights potential for early detection of mood disorders, therapy augmentation and long-term behavioral monitoring. Ethical considerations and privacy-preserving architectures are central to responsible deployment.

Key observations:
- Automated analysis can increase the value of journaling for users and clinicians but must ensure data minimization and user-control over sharing.
- LLMs can synthesize narrative insights but require safeguards to avoid generative errors and sensitive inferences.

Implication for system design: The architecture must maintain per-user isolation, selective disclosure, and explicit opt-in for LLM-based insights.

## Comparative Analysis

Compared to prior work, the implemented system integrates state-of-the-art transformer models for both affect and summarization, couples embeddings for personalization, and operationalizes an advanced recommendation strategy with explicit diversity and temporal components. The addition of a structured LLM-driven insight synthesis pipeline differentiates the system from existing journaling platforms and aligns with current research directions in computational mental health and personal informatics.

## Research Gap and Contribution

The principal research gap is the absence of end-to-end, reproducible pipelines that combine multi-label affect inference, abstractive summarization, embedding-driven personalization, and LLM-based insight generation specifically for journaling data. The implemented system contributes an integrated, reproducible design and evaluation protocol that advances practical applications and empirical research into longitudinal affective analytics from free-form personal text.

