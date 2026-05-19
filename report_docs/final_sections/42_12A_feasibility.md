# 12A Feasibility

This feasibility note summarizes technical, operational and ethical feasibility conclusions.

Technical feasibility
- Models: All required models (RoBERTa, BART, MPNet) are compatible with HuggingFace and PyTorch; local inference is viable on GPU instances.
- Data: Firestore supports the document model and per-user queries required by the system.

Operational feasibility
- Deployment: Containerization via Docker and `docker-compose` supports reproducible deployments; orchestration via Kubernetes recommended for production.
- Cost: Cloud LLM usage should be budgeted; local LLMs provide cost control at higher latency/resource expense.

Ethical feasibility
- Privacy: Per-user isolation and opt-in for LLMs reduce risk; clinical use requires controlled studies and consent.

Conclusion: The technical stack and design are feasible for prototype and research deployments with planned mitigations for cost, privacy and scalability.
