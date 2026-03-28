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

        # Media cache
        (["cache", "max_age_hours"], "MEDIA_CACHE_MAX_AGE_HOURS", "int"),
        (["cache", "fetch_limit"], "MEDIA_CACHE_FETCH_LIMIT", "int"),
        (["cache", "batch_size"], "MEDIA_CACHE_BATCH_SIZE", "int"),
        (["cache", "schema_version"], "MEDIA_CACHE_SCHEMA_VERSION", "str"),
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

