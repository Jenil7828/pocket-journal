import copy
import logging
import os
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)

_CONFIG: Dict[str, Any] | None = None


def _env_to_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _set_in_dict(cfg: Dict[str, Any], path: List[str], value: Any) -> None:
    cursor: Dict[str, Any] = cfg
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value


def _load_config_once() -> Dict[str, Any]:
    backend_dir = os.path.dirname(__file__)
    config_path = os.path.join(backend_dir, "config.yml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if not isinstance(cfg, dict):
        raise ValueError("Invalid config.yml: expected top-level mapping")

    # Only these scalar keys are overridable via env vars (as documented in config.yml comments).
    # Complex structures (language_buckets / supported_media_types) are intentionally not overridden here.
    overrides: List[Tuple[List[str], str, str]] = [

        # Server
        (["server", "port"], "PORT", "int"),
        (["server", "flask_debug"], "FLASK_DEBUG", "bool"),
        (["server", "disable_reloader"], "DISABLE_RELOADER", "bool"),

        # App
        (["app", "enable_llm"], "ENABLE_LLM", "bool"),
        (["app", "enable_insights"], "ENABLE_INSIGHTS", "bool"),
        (["app", "force_color"], "FORCE_COLOR", "bool"),
        (["app", "hf_hub_disable_xet"], "HF_HUB_DISABLE_XET", "bool"),
        (["app", "tf_cpp_min_log_level"], "TF_CPP_MIN_LOG_LEVEL", "str"),
        (["app", "timezone"], "APP_TIMEZONE", "str"),
        (["app", "mood_tracking_enabled_default"], "APP_MOOD_TRACKING_ENABLED_DEFAULT", "bool"),
        (["app", "summary_fallback_length"], "APP_SUMMARY_FALLBACK_LENGTH", "int"),

        # Logging
        (["logging", "app_level"], "APP_LOG_LEVEL", "str"),
        (["logging", "werkzeug_level"], "WERKZEUG_LOG_LEVEL", "str"),
        (["logging", "firebase_level"], "FIREBASE_LOG_LEVEL", "str"),

        # API — general
        (["api", "request_timeout"], "API_REQUEST_TIMEOUT", "int"),
        (["api", "request_max_retries"], "API_REQUEST_MAX_RETRIES", "int"),
        (["api", "default_limit"], "API_DEFAULT_LIMIT", "int"),
        (["api", "max_limit"], "API_MAX_LIMIT", "int"),
        (["api", "entries_max_limit"], "API_ENTRIES_MAX_LIMIT", "int"),

        # API — Google Books
        (["api", "google_books", "page_size"], "API_GOOGLE_BOOKS_PAGE_SIZE", "int"),

        # API — TMDb
        (["api", "tmdb", "max_pages"], "API_TMDB_MAX_PAGES", "int"),
        (["api", "tmdb", "results_per_page"], "API_TMDB_RESULTS_PER_PAGE", "int"),
        (["api", "tmdb", "default_max_results"], "API_TMDB_DEFAULT_MAX_RESULTS", "int"),
        (["api", "tmdb", "mood_movies_limit"], "API_TMDB_MOOD_MOVIES_LIMIT", "int"),
        (["api", "tmdb", "filtered_limit"], "API_TMDB_FILTERED_LIMIT", "int"),

        # ML — mood detection
        (["ml", "mood_detection", "model_version"], "MOOD_MODEL_VERSION", "str"),
        (["ml", "mood_detection", "model_name"], "MOOD_MODEL_NAME", "str"),
        (["ml", "mood_detection", "max_length"], "MOOD_MAX_LENGTH", "int"),
        (["ml", "mood_detection", "prediction_threshold"], "MOOD_PREDICTION_THRESHOLD", "float"),

        # ML — summarization
        (["ml", "summarization", "model_version"], "SUMMARIZATION_MODEL_VERSION", "str"),
        (["ml", "summarization", "model_name"], "SUMMARIZATION_MODEL_NAME", "str"),
        (["ml", "summarization", "max_input_length"], "SUMMARIZATION_MAX_INPUT_LENGTH", "int"),
        (["ml", "summarization", "max_summary_length"], "SUMMARIZATION_MAX_SUMMARY_LENGTH", "int"),
        (["ml", "summarization", "min_summary_length"], "SUMMARIZATION_MIN_SUMMARY_LENGTH", "int"),
        (["ml", "summarization", "num_beams"], "SUMMARIZATION_NUM_BEAMS", "int"),

        # ML — embedding
        (["ml", "embedding", "model_name"], "EMBEDDING_MODEL_NAME", "str"),
        (["ml", "embedding", "journal_blend_weight"], "JOURNAL_BLEND_WEIGHT", "float"),
        (["ml", "embedding", "taste_blend_weight"], "TASTE_BLEND_WEIGHT", "float"),

        # ML — insight generation
        (["ml", "insight_generation", "use_gemini"], "INSIGHTS_USE_GEMINI", "bool"),
        (["ml", "insight_generation", "backend"], "INSIGHTS_BACKEND", "str"),
        (["ml", "insight_generation", "model_version"], "INSIGHTS_MODEL_VERSION", "str"),
        (["ml", "insight_generation", "hf_model_name"], "INSIGHTS_HF_MODEL_NAME", "str"),
        (["ml", "insight_generation", "hf_model_dir"], "INSIGHTS_HF_MODEL_DIR", "str"),
        (["ml", "insight_generation", "ollama_model"], "INSIGHTS_OLLAMA_MODEL", "str"),
        (["ml", "insight_generation", "ollama_base_url"], "INSIGHTS_OLLAMA_BASE_URL", "str"),
        (["ml", "insight_generation", "temperature"], "INSIGHTS_TEMPERATURE", "float"),
        (["ml", "insight_generation", "batch_size"], "INSIGHTS_BATCH_SIZE", "int"),
        (["ml", "insight_generation", "max_new_tokens"], "INSIGHTS_MAX_NEW_TOKENS", "int"),
        (["ml", "insight_generation", "gemini_model_name"], "INSIGHTS_GEMINI_MODEL_NAME", "str"),
        (["ml", "insight_generation", "gemini_max_retries"], "INSIGHTS_GEMINI_MAX_RETRIES", "int"),

        # ML — model store
        (["ml", "model_store", "source"], "MODEL_SOURCE", "str"),
        (["ml", "model_store", "local_path"], "MODEL_STORE_PATH", "str"),
        (["ml", "model_store", "cache_dir"], "MODEL_CACHE_DIR", "str"),
        (["ml", "model_store", "gcs_bucket"], "MODEL_GCS_BUCKET", "str"),
        (["ml", "model_store", "s3_bucket"], "MODEL_S3_BUCKET", "str"),
        (["ml", "model_store", "s3_region"], "MODEL_S3_REGION", "str"),
        (["ml", "model_store", "download_on_startup"], "MODEL_DOWNLOAD_ON_STARTUP", "bool"),
        (["ml", "model_store", "models", "roberta", "version"], "MODEL_ROBERTA_VERSION", "str"),
        (["ml", "model_store", "models", "bart", "version"], "MODEL_BART_VERSION", "str"),
        (["ml", "model_store", "models", "qwen2", "version"], "MODEL_QWEN2_VERSION", "str"),
        (["ml", "model_store", "models", "embedding", "version"], "MODEL_EMBEDDING_VERSION", "str"),

        # Recommendation
        (["recommendation", "fetch_limit"], "RECOMMENDATION_FETCH_LIMIT", "int"),
        (["recommendation", "refine_top"], "RECOMMENDATION_REFINE_TOP", "int"),
        (["recommendation", "top_k"], "RECOMMENDATION_TOP_K", "int"),
        (["recommendation", "ranking", "similarity_weight"], "RANKING_SIMILARITY_WEIGHT", "float"),
        (["recommendation", "ranking", "popularity_weight"], "RANKING_POPULARITY_WEIGHT", "float"),
        (["recommendation", "ranking", "low_std_threshold"], "RANKING_LOW_STD_THRESHOLD", "float"),
        (["recommendation", "intent", "beta_min"], "INTENT_BETA_MIN", "float"),
        (["recommendation", "intent", "beta_boost"], "INTENT_BETA_BOOST", "float"),
        (["recommendation", "intent", "beta_max"], "INTENT_BETA_MAX", "float"),
        (["recommendation", "intent", "journal_embedding_fetch_limit"], "INTENT_JOURNAL_EMBEDDING_FETCH_LIMIT", "int"),
        (["recommendation", "candidate", "min_title_length"], "CANDIDATE_MIN_TITLE_LENGTH", "int"),
        (["recommendation", "candidate", "min_popularity"], "CANDIDATE_MIN_POPULARITY", "float"),
        (["recommendation", "concurrency", "intent_builder_max_workers"], "INTENT_BUILDER_MAX_WORKERS", "int"),

        # Recommendation Phase 5
        (["recommendation", "ranking", "use_phase5"], "RANKING_USE_PHASE5", "bool"),
        (["recommendation", "ranking", "use_mmr"], "RANKING_USE_MMR", "bool"),
        (["recommendation", "ranking", "use_hybrid_scoring"], "RANKING_USE_HYBRID_SCORING", "bool"),
        (["recommendation", "ranking", "use_temporal_decay"], "RANKING_USE_TEMPORAL_DECAY", "bool"),
        (["recommendation", "ranking", "mmr_lambda"], "RANKING_MMR_LAMBDA", "float"),
        (["recommendation", "ranking", "temporal_decay_rate"], "RANKING_TEMPORAL_DECAY_RATE", "float"),
        (["recommendation", "ranking", "max_candidates_for_ranking"], "RANKING_MAX_CANDIDATES", "int"),
        (["recommendation", "ranking", "target_response_time_ms"], "RANKING_TARGET_RESPONSE_TIME_MS", "int"),

        # Interactions
        (["interactions", "signal_weights", "click"], "INTERACTION_WEIGHT_CLICK", "float"),
        (["interactions", "signal_weights", "save"], "INTERACTION_WEIGHT_SAVE", "float"),
        (["interactions", "signal_weights", "skip"], "INTERACTION_WEIGHT_SKIP", "float"),
        (["interactions", "rate_limit_per_hour"], "INTERACTION_RATE_LIMIT_PER_HOUR", "int"),
        (["interactions", "rate_limit_check_window_minutes"], "INTERACTION_RATE_LIMIT_WINDOW_MIN", "int"),

        # Search
        (["search", "fuzzy_threshold_relevance"], "SEARCH_FUZZY_THRESHOLD_RELEVANCE", "int"),
        (["search", "fuzzy_threshold_dedup"], "SEARCH_FUZZY_THRESHOLD_DEDUP", "int"),
        (["search", "max_cache_results_per_type"], "SEARCH_MAX_CACHE_RESULTS", "int"),
        (["search", "default_search_limit"], "SEARCH_DEFAULT_LIMIT", "int"),
        (["search", "max_search_limit"], "SEARCH_MAX_LIMIT", "int"),
        (["search", "fallback_to_provider"], "SEARCH_FALLBACK_TO_PROVIDER", "bool"),
        (["search", "min_cache_results_for_success"], "SEARCH_MIN_CACHE_RESULTS", "int"),
        (["search", "search_timeout_seconds"], "SEARCH_TIMEOUT_SECONDS", "int"),
        (["search", "concurrent_providers"], "SEARCH_CONCURRENT_PROVIDERS", "int"),

        # Providers
        (["providers", "default_timeout_seconds"], "PROVIDER_TIMEOUT_SECONDS", "int"),
        (["providers", "max_retries"], "PROVIDER_MAX_RETRIES", "int"),
        (["providers", "default_max_results"], "PROVIDER_DEFAULT_MAX_RESULTS", "int"),
        (["providers", "tmdb", "timeout_seconds"], "TMDB_TIMEOUT_SECONDS", "int"),
        (["providers", "tmdb", "popularity_threshold"], "TMDB_POPULARITY_THRESHOLD", "float"),
        (["providers", "spotify", "market_default"], "SPOTIFY_MARKET_DEFAULT", "str"),
        (["providers", "google_books", "page_size"], "GOOGLE_BOOKS_PAGE_SIZE", "int"),

        # Embedding
        (["ml", "embedding", "embedding_dimension"], "EMBEDDING_DIMENSION", "int"),
        (["ml", "embedding", "device"], "EMBEDDING_DEVICE", "str"),
        (["ml", "embedding", "use_half_precision"], "EMBEDDING_USE_HALF_PRECISION", "bool"),

        # System limits
        (["system", "limits", "default_top_k"], "SYSTEM_DEFAULT_TOP_K", "int"),
        (["system", "limits", "max_top_k"], "SYSTEM_MAX_TOP_K", "int"),
        (["system", "limits", "batch_size_default"], "SYSTEM_BATCH_SIZE_DEFAULT", "int"),
        (["system", "limits", "batch_size_embedding"], "SYSTEM_BATCH_SIZE_EMBEDDING", "int"),
        (["system", "limits", "batch_size_inference"], "SYSTEM_BATCH_SIZE_INFERENCE", "int"),
        (["system", "limits", "max_concurrent_requests"], "SYSTEM_MAX_CONCURRENT_REQUESTS", "int"),
        (["system", "limits", "request_timeout_seconds"], "SYSTEM_REQUEST_TIMEOUT_SECONDS", "int"),
        (["system", "text", "normalize_before_search"], "SYSTEM_NORMALIZE_BEFORE_SEARCH", "bool"),

        # Firestore
        (["firestore", "query_batch_size"], "FIRESTORE_QUERY_BATCH_SIZE", "int"),
        (["firestore", "max_write_batch_size"], "FIRESTORE_MAX_WRITE_BATCH_SIZE", "int"),
    ]

    for path, env_name, cast in overrides:
        if env_name not in os.environ:
            continue
        raw = os.environ.get(env_name)
        if raw is None:
            continue

        if cast == "bool":
            value = _env_to_bool(raw)
        elif cast == "int":
            value = int(raw.strip())
        elif cast == "str":
            value = str(raw)
        else:
            raise ValueError(f"Unsupported cast type: {cast}")

        _set_in_dict(cfg, path, value)
        logger.debug("Config override via env: %s=%r", env_name, value)

    return cfg


# Load exactly once at import time.
_CONFIG = _load_config_once()


def get_config() -> Dict[str, Any]:
    """
    Return a merged config dict (YAML values overridden by matching env vars).
    The returned dict is a deep copy so callers can't mutate shared config state.
    """

    # Defensive: if something mutates _CONFIG internally, we always return a clean copy.
    return copy.deepcopy(_CONFIG)  # type: ignore[arg-type]


def get(path: str, default: Any = None) -> Any:
    """
    Get a config value using dot notation (e.g., 'recommendation.ranking.mmr_lambda').
    
    Args:
        path: Dot-separated path to config value (e.g., "ml.mood_detection.max_length")
        default: Default value if path not found
    
    Returns:
        Config value or default
    """
    cfg = get_config()
    parts = path.split(".")
    value = cfg
    
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            logger.debug("Config path not found: %s, using default: %r", path, default)
            return default
    
    return value


def get_int(path: str, default: int = 0) -> int:
    """Get integer config value."""
    val = get(path, default)
    return int(val) if val is not None else default


def get_float(path: str, default: float = 0.0) -> float:
    """Get float config value."""
    val = get(path, default)
    return float(val) if val is not None else default


def get_str(path: str, default: str = "") -> str:
    """Get string config value."""
    val = get(path, default)
    return str(val) if val is not None else default


def get_bool(path: str, default: bool = False) -> bool:
    """Get boolean config value."""
    val = get(path, default)
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return _env_to_bool(val)
    return bool(val) if val is not None else default


def get_list(path: str, default: List[Any] | None = None) -> List[Any]:
    """Get list config value."""
    if default is None:
        default = []
    val = get(path, default)
    return list(val) if val is not None else default


def get_dict(path: str, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Get dictionary config value."""
    if default is None:
        default = {}
    val = get(path, default)
    return dict(val) if isinstance(val, dict) else default


def validate_required_keys(required_paths: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that required config keys exist.
    
    Args:
        required_paths: List of dot-notation paths to validate
    
    Returns:
        (is_valid, list_of_missing_paths)
    """
    cfg = get_config()
    missing = []
    
    for path in required_paths:
        parts = path.split(".")
        value = cfg
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                missing.append(path)
                break
    
    return len(missing) == 0, missing


def validate_and_log_config() -> bool:
    """
    Validate critical config on startup.
    Logs warnings for missing optional configs.
    Returns False if any critical configs are missing.
    """
    # Critical paths that must exist
    critical_paths = [
        "server.port",
        "api.request_timeout",
        "ml.mood_detection.model_version",
        "ml.summarization.model_version",
        "ml.embedding.model_name",
        "recommendation.top_k",
        "cache.max_age_hours",
    ]
    
    is_valid, missing = validate_required_keys(critical_paths)
    
    if not is_valid:
        logger.error("Critical config keys missing: %s", missing)
        return False
    
    # Optional paths to check
    optional_paths = [
        "ml.insight_generation.use_gemini",
        "recommendation.ranking.use_phase5",
        "search.fuzzy_threshold_relevance",
    ]
    
    _, missing_optional = validate_required_keys(optional_paths)
    if missing_optional:
        logger.warning("Optional config keys missing (using defaults): %s", missing_optional)
    
    logger.info("Config validation: OK (critical keys present, optional: %d missing)", len(missing_optional))
    return True


