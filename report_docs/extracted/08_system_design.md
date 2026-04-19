# 📄 System Design (Academic Description)

## Architectural Overview

The system adopts a layered architecture composed of: (1) a presentation layer exposing RESTful endpoints; (2) a service layer encapsulating domain logic (journal management, recommendation, insights); (3) an inference layer hosting transformer-based models; (4) a persistence layer realized with Firestore; and (5) integrations with external provider APIs for media content. Each layer enforces a clear responsibility boundary and communicates through well-defined interfaces, enabling independent evolution and empirical evaluation.

## Component Roles and Rationale

Presentation layer: Provides authenticated endpoints for journal CRUD, search, insights generation and recommendations. The route modules perform parameter validation and delegate substantive work to services.

Service layer: Implements business logic including orchestration of ML inference, database transactions, and response normalization. Service modules are organized by domain (journal_entries, media_recommender, insights_service) to encapsulate responsibilities and improve testability.

Inference layer: Hosts model artifacts and inference wrappers. The architecture isolates model-specific code behind predictor classes (e.g., emotion predictor and summarizer) to enable substitution or local/cloud switching for insights generation.

Persistence layer: Uses Firestore collections to store primary journal content, analysis artifacts, embeddings, user vectors, interactions and cached media. The document model supports efficient per-user filtering and time-bounded queries while enabling schema validation via a documented DatabaseSchema utility.

External integrations: Media data retrieval relies on established provider APIs (TMDb, Spotify, Google Books) and a cache layer to control external dependency latency and cost. The insights generator is designed to operate with either a cloud LLM or an on-premise model depending on configuration.

## Pipelines and Data Flow (Conceptual)

Entry processing pipeline: On entry creation, the system writes the raw text to storage and concurrently executes three inference tasks: emotion detection, abstractive summarization, and embedding generation. Analytic artifacts are persisted in separate collections to support reanalysis and efficient querying.

Recommendation pipeline: The recommendation process constructs a context vector by blending a long-term taste vector with recent journal-derived embeddings. Candidate items are retrieved from a cache, then filtered and ranked using a hybrid scoring function integrating cosine similarity, MMR-based diversity, temporal decay and interaction signals.

Insight synthesis pipeline: For a requested date range, the system aggregates summaries and mood distributions, constructs a structured prompt and invokes an LLM backend to produce a JSON-structured insight document. Results are validated and stored with mapping to the contributing entries.

## Design Considerations and Trade-offs

Modularity versus latency: Eager model loading reduces request latency but increases startup time and memory footprint. The design permits lazy loading where necessary to balance resource constraints.

Privacy versus utility: Storing analysis outputs as separate documents improves retrieval but requires careful security rules to maintain per-user isolation. The system enforces uid-based checks at both application and storage levels.

Quality versus availability: LLM-backed insight generation provides higher-quality synthesis but is dependent on external availability and cost; a local model provides an offline fallback at the cost of increased latency.

## Operational and Extensibility Notes

- Configuration-driven model selection enables reproducible experiments and controlled comparisons across model variants.
- The document-oriented data model improves iteration speed for research but requires explicit index planning to satisfy performance constraints for large-scale queries.
- The service abstraction facilitates unit testing and the substitution of mock components for controlled evaluation.

