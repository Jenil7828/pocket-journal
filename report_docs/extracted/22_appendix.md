# 📄 Appendix

## A. Sample API Requests and Responses

### 1. Create Journal Entry (POST /api/v1/journal)

Request (JSON):
```
POST /api/v1/journal
Authorization: Bearer <ID_TOKEN>
Content-Type: application/json

{
  "entry_text": "Today I felt anxious after the meeting but also relieved that it ended well.",
  "title": "Work meeting"
}
```

Response (200 OK):
```
{
  "entry_id": "abc123",
  "created_at": "2026-04-01T10:00:00Z",
  "mood": {
    "happy": 0.12,
    "sad": 0.05,
    "fear": 0.72
  },
  "summary": "Felt anxious following a work meeting but relieved afterwards.",
  "analysis_id": "anl456"
}
```

### 2. Generate Insights (POST /api/v1/insights/generate)

Request (JSON):
```
POST /api/v1/insights/generate
Authorization: Bearer <ID_TOKEN>
Content-Type: application/json

{
  "start_date": "2026-03-25",
  "end_date": "2026-04-01"
}
```

Response (200 OK):
```
{
  "goals": [{"title":"Improve sleep","description":"Establish 10pm phone curfew"}],
  "progress": "Some nights improved sleep hygiene observed.",
  "negative_behaviors": "Late-night screen time",
  "remedies": "Set phone curfew; evening relaxation routine",
  "appreciation": "Consistent morning runs noted",
  "conflicts": "Work deadlines vs personal time"
}
```

## B. Additional Tables

### B.1. Emotion Labels and Short Descriptions

| Label | Description |
|-------|-------------|
| anger | Irritation, frustration |
| disgust | Aversion, revulsion |
| fear | Anxiety, worry |
| happy | Joy, contentment |
| neutral | Neutral tone |
| sad | Sorrow, low mood |
| surprise | Startlement, astonishment |

### B.2. Recommendation Ranking Components

| Component | Role | Typical Weight |
|-----------|------|----------------|
| similarity | Intent–item cosine similarity | 0.50 |
| interaction_frequency | Historical user interactions | 0.20 |
| popularity | Global popularity metric | 0.20 |
| recency | Recency of interactions | 0.10 |
| temporal_decay | Penalize old interactions | applied multiplicatively |

## C. Configuration Example (Snippets)

config.yml (excerpt):
```
ml:
  mood_detection:
    model_version: "v2"
    prediction_threshold: 0.25
  summarization:
    model_version: "v2"
    max_summary_length: 128
  embedding:
    model_name: "all-mpnet-base-v2"
    embedding_dimension: 384
recommendation:
  ranking:
    use_mmr: true
    mmr_lambda: 0.7
    temporal_decay_rate: 0.15
```

## D. Reproducibility Checklist

- Persist `config.yml` and environment variables used for experiments.
- Record model paths and versions resolved by `resolve_model_path()`.
- Store dataset splits and annotation schemas for emotion and summarization evaluations.
- Log random seeds used for ranking and sampling during experiments.

## E. Contact and References

Refer to the project `docs/` folder for configuration details, academic artifacts and supporting files used in empirical evaluation.

