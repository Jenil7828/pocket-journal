# services package init
# Re-export commonly used service facades for backward compatibility
from . import journal_entries as journal_entries
from .export_service import export_data as export_data
from . import export_service as export_service
from . import insights_service as insights_service
from . import stats_service as stats_service

# New user profile management services
from . import preferences_service as preferences_service
from . import settings_service as settings_service
from . import notification_service as notification_service
from . import user_service as user_service

# Phase 4: Personalization & Advanced Features (reorganized)
from .media_recommender import cold_start_handler as cold_start_handler
from .media_recommender import search_service as search_service
from .media_recommender import media_recommendations as media_recommendations
from .personalization import interaction_service as interaction_service
from .personalization import taste_vector_service as taste_vector_service

# Analytics services
from .analytics import calculate_streak as calculate_streak

# Embeddings service
from .embeddings import embedding_service as embedding_service
from .embeddings import get_embedding_service as get_embedding_service

# System services
from .system import health_service as health_service

# Also expose function-level shortcuts if needed
from .journal_entries import (
    process_entry,
    update_entry,
    delete_entry,
    delete_entries_batch,
    reanalyze_entry,
    get_single_entry,
    get_entry_analysis,
    get_entries_filtered,
)

__all__ = [
    "journal_entries",
    "export_service",
    "export_data",
    "insights_service",
    "stats_service",
    # New services
    "preferences_service",
    "settings_service",
    "notification_service",
    "user_service",
    # Phase 4: Personalization (reorganized)
    "cold_start_handler",
    "search_service",
    "media_recommendations",
    "interaction_service",
    "taste_vector_service",
    # Analytics
    "calculate_streak",
    # Embeddings
    "embedding_service",
    "get_embedding_service",
    # System
    "health_service",
    # Functions
    "process_entry",
    "update_entry",
    "delete_entry",
    "delete_entries_batch",
    "reanalyze_entry",
    "get_single_entry",
    "get_entry_analysis",
    "get_entries_filtered",
]
