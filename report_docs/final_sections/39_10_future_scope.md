# 10 Future Scope

This section outlines concrete extensions and research directions grounded in the existing implementation.

1. Multimodal fusion
   - Integrate audio (voice journaling) and images with text embeddings; update inference wrappers and storage schema.

2. Vector search infrastructure
   - Integrate FAISS or Milvus for scalable nearest-neighbour retrieval of embeddings stored in `journal_embeddings`.

3. Model serving
   - Deploy models via dedicated serving (Triton, Ray Serve) to improve latency and monitoring.

4. Online personalization
   - Implement safe continual learning techniques to update `user_vectors` incrementally using interaction signals while preserving privacy.

5. Explainability
   - Provide local explanations for mood predictions (e.g., attention highlights) and recommendation rationales to increase user trust.

6. Controlled clinical evaluations
   - Design longitudinal studies to validate extracted signals against clinical instruments under IRB-approved protocols.

Each item maps to components in the current codebase, facilitating progressive extension and empirical validation.
