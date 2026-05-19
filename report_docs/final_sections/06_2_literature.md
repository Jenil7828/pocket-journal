# 2 Literature Survey

This literature survey synthesizes leading work relevant to emotion detection, abstractive summarization, recommendation systems and digital journaling. The review integrates findings from the provided literature table and selected research papers in `Documentation/Research Papers` and highlights the research gap targeted by this project.

1. Emotion detection
   - Transformer-based models such as RoBERTa (Liu et al., 2019) and BERT have demonstrated superior contextualized representations for emotion and sentiment tasks compared to RNN-based approaches. Multi-label classification using sigmoid outputs and calibrated thresholds improves detection of co-occurring emotions.

2. Abstractive summarization
   - Encoder–decoder transformers (BART, Lewis et al., 2020; T5, Raffel et al., 2020) are state-of-the-art for abstractive summarization. Techniques to improve factual consistency include constrained decoding (no_repeat_ngram_size), length penalties, and domain-specific fine-tuning.

3. Embeddings and semantic search
   - Sentence-transformers (Reimers & Gurevych, 2019) and the `all-mpnet-base-v2` model provide compact, high-quality sentence embeddings enabling semantic similarity, retrieval and intent construction.

4. Recommendation systems
   - Hybrid models combining collaborative signals (taste vectors) and content/context embeddings are effective in balancing long-term preference and short-term intent. Diversity promotion via MMR and temporal decay models addresses novelty and recency.

5. LLMs for insight synthesis
   - Large language models (LLMs) can synthesize multi-document inputs into structured outputs but require prompt engineering and output validation to avoid hallucination. Cloud-hosted LLMs (Gemini-class) reduce latency but introduce costs, while local models (Qwen2) support offline operation.

Comparison table (representative works)

| Topic | Representative Method | Strengths | Limitations |
|-------|-----------------------|----------:|------------|
| Emotion detection | RoBERTa fine-tuning | Contextualized, strong multi-label performance | Requires in-domain data for calibration |
| Summarization | BART/T5 | High-quality abstractive summaries | Potential for hallucination; compute heavy |
| Embeddings | MPNet / SBERT | Compact, high recall for semantic search | May require approximate nearest neighbours for scale |
| Recommendations | Hybrid + MMR | Balances relevance and diversity | Complexity in tuning multiple signals |
| LLM synthesis | Gemini / Qwen2 | Rich synthesis, flexible prompts | Cost, latency, hallucination risk |

Research gap and link to system
- Few prior works present an end-to-end, reproducible pipeline specifically tailored to digital journaling combining multi-label emotion detection, abstractive summarization, embedding-driven personalization, and LLM-based insight synthesis.
- This project situates itself in that gap by providing concrete engineering artifacts, evaluation targets and documented pipelines aligned with the literature.

References used for this section are drawn from the provided literature table and the repository `Documentation/Research Papers/`. Full bibliographic listings are included in the References section of this report.
