# 9 Applications

The Pocket Journal system supports multiple real-world application scenarios that leverage its extraction and personalization capabilities.

1. Personal well-being and self-monitoring
   - Use: Individuals review summaries and mood trajectories to support habit formation and self-reflection.
   - Implementation detail: Summaries are generated via BART and moods via RoBERTa; visualizations built from `journal_entries` and `entry_analysis`.

2. Clinical research and therapy augmentation (non-diagnostic)
   - Use: Aggregated, consented summaries and mood trends can support clinicians in session planning.
   - Implementation detail: Researchers can export anonymized datasets via `GET /api/v1/export/data` for offline analysis.

3. Context-aware media personalization
   - Use: Content platforms can integrate mood-aware recommendations to surface emotionally congruent media.
   - Implementation detail: The recommendation pipeline blends `user_vectors` with recent journal `journal_embeddings` to produce context-aware ranked lists.

4. Organizational wellness programs
   - Use: Aggregate, privacy-preserving insights for employee well-being programs with explicit consent and data governance.

Integration considerations:
- Consent workflows are required for any application beyond personal use.
- For research, maintain dataset annotations and experiment logs for reproducibility.

These applications demonstrate both consumer and research value of the extraction-based architecture.
