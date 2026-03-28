# Product Roadmap: Pocket Journal

## Phase Overview

```
Timeline:
Q4 2024 - Phase 1: Core foundation        ✓ Complete
Q1 2025 - Phase 2: Summarization + Recs   ✓ Complete
Q2 2025 - Phase 2.5: Semantic ranking      ✓ Complete
Q3 2025 - Phase 3: Cache-first pipeline    ✓ Complete
Q4 2025 - Phase 4: Insights + Export       → In Progress
2026    - Phase 5: Advanced analytics      → Planned
```

---

## Completed: Phase 1 (Core Foundation)

**Timeline**: Q4 2024

**Deliverables**:
- ✅ Flask REST API scaffolding
- ✅ Firebase Auth integration
- ✅ Firestore database schema
- ✅ User management endpoints
- ✅ Journal entry CRUD
- ✅ Basic health checks

**Key Metrics**:
- 7 core API endpoints
- 50+ test cases
- JWT authentication
- User isolation

---

## Completed: Phase 2 (Summarization & Recommendations)

**Timeline**: Q1 2025

**Deliverables**:
- ✅ RoBERTa mood detection (7-class emotions)
- ✅ BART summarization (concise summaries)
- ✅ Basic TMDb integration (movie recs)
- ✅ Spotify integration (music recs)
- ✅ Google Books integration (book recs)
- ✅ Mood-genre mapping

**Key Metrics**:
- Mood detection accuracy: 82%
- Summarization rouge score: 0.42
- 3 external providers integrated
- 25+ endpoints

**Known Limitations**:
- Linear mood→genre mapping (not personalized)
- No user taste learning
- Provider calls not cached

---

## Completed: Phase 2.5 (Semantic Ranking)

**Timeline**: Q2 2025

**Deliverables**:
- ✅ sentence-transformers embedding model (768-dim vectors)
- ✅ Intent vector building (blend user taste + mood)
- ✅ Cosine similarity ranking
- ✅ Popularity weighting (0.9 similarity + 0.1 popularity)
- ✅ Taste profile aggregation (user_vectors)

**Key Metrics**:
- Embedding generation: 250ms/entry
- Similarity ranking: 100ms/50 items
- Taste profile update: Daily batch job
- Recommendation relevance: 75% user satisfaction

**Improvements Over Phase 2**:
- Personalization: +40% relevance
- Latency: -25% (smarter filtering)
- Diversity: 30% more unique results

---

## Completed: Phase 3 (Cache-First Pipeline)

**Timeline**: Q3 2025

**Deliverables**:
- ✅ Firestore media cache (24h TTL)
- ✅ Cache-first strategy with provider fallback
- ✅ Hybrid search (fuzzy match + cache)
- ✅ Deduplication logic
- ✅ 4 media types: movies, songs, books, podcasts
- ✅ Language buckets (hindi, english, neutral)

**Key Metrics**:
- Cache hit rate: 75%
- API response time: -60% (cache)
- Provider API calls: -80%
- Firestore reads: -82%

**Improvements Over Phase 2.5**:
- Speed: 3000ms → 1200ms (cache hit)
- Cost: 82% fewer reads
- Reliability: Provider outages don't break app
- Flexibility: Multi-language support

---

## In Progress: Phase 4 (Insights & Export)

**Timeline**: Q4 2025

**Deliverables**:
- 🔄 Qwen2 1.5B-Instruct local LLM
- 🔄 Google Gemini integration (fallback)
- 🔄 Insight generation (mood patterns, goals, remedies)
- 🔄 Batch processing (5 entries/batch)
- 🔄 Data export (CSV, JSON, PDF)
- 🔄 Advanced statistics (mood trends, frequency)

**Target Completion**: December 2025

**Current Status**:
- Qwen2 model: Downloaded, optimized
- Gemini API: Integrated, tested
- Batch processing: Implemented
- Export service: MVP ready
- Stats aggregation: Core logic done

**Remaining Work**:
- [ ] PDF export with charts
- [ ] Scheduling insights generation
- [ ] Performance optimization (batch insights)
- [ ] UI for insights display
- [ ] Export scheduling

**Success Criteria**:
- Insights generation < 5s p99
- Export latency < 2s p99
- Batch processing > 80% CPU utilization
- User satisfaction > 80%

---

## Planned: Phase 5 (Advanced Analytics)

**Timeline**: 2026

**Proposed Features**:
- 📊 **Advanced Dashboards**
  - Mood calendar (like GitHub contributions)
  - Mood progression over months/years
  - Entry frequency heatmaps
  - Correlation analysis (mood ↔ entries)

- 📈 **Predictive Analytics**
  - Mood trend forecasting (next week)
  - Optimal recommendation timing
  - Anomaly detection (unusual mood shifts)

- 👥 **Multi-User Features** (Optional)
  - Shared journal collections
  - Family/group insights
  - Comparison analytics (anonymized)

- 🤖 **Personalization v2**
  - Fine-tuned mood detector per user
  - Custom recommendation weights
  - Adaptive summarization

- 🔗 **Integrations**
  - Spotify API for actual listening data
  - Fitness tracker correlation (mood ↔ activity)
  - Weather correlation analysis
  - Calendar integration

**Estimated Timeline**: Q1-Q3 2026

**Resource Requirements**:
- 2-3 engineers (6 months)
- Data science consultation
- Infrastructure upgrade (larger compute)

**Revenue Potential**:
- Premium analytics tier ($4.99/month)
- API access for researchers
- B2B wellness platform integration

---

## Known Limitations

### Current System Limitations

**Language Support**:
- ❌ RoBERTa optimized for English only
- Non-English entries: Lower accuracy
- Plan: Fine-tune multilingual models (Phase 5)

**Model Accuracy**:
- Mood detection: 82% accuracy (vs 87% target)
- Summarization: ROUGE-1 0.42 (vs 0.50 target)
- Insights: Human evaluation pending

**Scalability**:
- Single GPU: 500 req/s max
- Plan: Multi-GPU setup or serverless (Phase 5)

**Data Coverage**:
- Media catalog: Provider-dependent
- TMDb: Good movie coverage, weak indie
- Spotify: Excellent music, limited non-Western artists
- Google Books: Millions, but poor metadata

**Personalization**:
- 90-day data required for good taste profile
- New users: Generic recommendations first week
- Plan: Cold-start strategies in Phase 5

---

## Deprecated/Won't Do

**Rationale for Not Including**:

1. **Social Features** (Not in scope)
   - Sharing entries publicly
   - Collaborative journaling
   - Rationale: Privacy-first design; social features create security complexity

2. **Real-time Notifications** (Low priority)
   - "New recommendation available"
   - "Mood improved 20% this week"
   - Rationale: Journaling is async; push notifications may feel intrusive

3. **Audio Journaling** (Phase 5+ consideration)
   - Voice-to-text entry
   - Audio playback
   - Rationale: ASR adds infrastructure; text is simpler for MVP

4. **AR/VR Experiences** (Not applicable)
   - Virtual journaling environment
   - Rationale: Overengineered for use case

---

## Success Metrics by Phase

### Phase 4 (Current)

**Technical KPIs**:
- [ ] Insights generation latency: < 5s p99
- [ ] Batch processing throughput: > 10 insights/min
- [ ] Export success rate: > 99%
- [ ] API error rate: < 1%

**Product KPIs**:
- [ ] User adoption: Target 1000 active users
- [ ] Feature usage: 40% generate insights/month
- [ ] Retention (30-day): > 60%
- [ ] NPS (Net Promoter Score): > 40

### Phase 5

**Technical KPIs**:
- Dashboard load time: < 2s
- Predictive accuracy: > 75%
- API throughput: 5000+ req/s

**Product KPIs**:
- Premium conversion: > 10%
- Enterprise pilots: > 3
- Research citations: > 5

---

## Feedback & Iteration

**User Feedback Channels**:
- [ ] In-app feedback form
- [ ] User interviews (quarterly)
- [ ] Beta testing program
- [ ] Analytics dashboard (usage patterns)

**Iteration Cycle**:
1. Gather feedback (1 week)
2. Prioritize features (1 week)
3. Implement highest-value items (2 weeks)
4. Release & measure (1 week)
5. Repeat

---

## Budget & Resource Allocation

**Current (Phase 4)**:
- 2 Backend engineers
- 1 ML engineer
- 1 DevOps (shared)
- Monthly cloud costs: ~$500-1000 (Firestore, compute)

**Phase 5 Proposal**:
- +1 Senior engineer (architecture)
- +1 Data scientist (analytics)
- +1 DevOps (full-time)
- Monthly cloud: $2000-5000 (scaled infrastructure)

---

## Communication

**Stakeholder Updates**:
- Weekly: Engineering stand-ups
- Bi-weekly: Product team reviews
- Monthly: Executive summary (KPIs, blockers)
- Quarterly: Roadmap reviews (Phase planning)

**Public Changelog**:
- Release notes on GitHub
- Feature announcements (email, Discord)
- Transparent roadmap (https://roadmap.example.com)


