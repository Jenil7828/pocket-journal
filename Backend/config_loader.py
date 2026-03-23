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
        # Recommendation settings
        (["recommendation", "fetch_limit"], "RECOMMENDATION_FETCH_LIMIT", "int"),
        (["recommendation", "refine_top"], "RECOMMENDATION_REFINE_TOP", "int"),
        (["recommendation", "top_k"], "RECOMMENDATION_TOP_K", "int"),
        (["recommendation", "ranking", "similarity_weight"], "RANKING_SIMILARITY_WEIGHT", "float"),
        (["recommendation", "ranking", "popularity_weight"], "RANKING_POPULARITY_WEIGHT", "float"),
        (["recommendation", "ranking", "low_std_threshold"], "RANKING_LOW_STD_THRESHOLD", "float"),
        (["recommendation", "intent", "beta_min"], "INTENT_BETA_MIN", "float"),
        (["recommendation", "intent", "beta_boost"], "INTENT_BETA_BOOST", "float"),
        (["recommendation", "intent", "beta_max"], "INTENT_BETA_MAX", "float"),
        (["recommendation", "candidate", "min_title_length"], "CANDIDATE_MIN_TITLE_LENGTH", "int"),
        (["recommendation", "candidate", "min_popularity"], "CANDIDATE_MIN_POPULARITY", "float"),
        # Embedding settings
        (["embedding", "model_name"], "EMBEDDING_MODEL_NAME", "str"),
        (["embedding", "journal_blend_weight"], "JOURNAL_BLEND_WEIGHT", "float"),
        (["embedding", "taste_blend_weight"], "TASTE_BLEND_WEIGHT", "float"),
        # ML settings
        (["ml", "mood_detection", "model_version"], "MOOD_MODEL_VERSION", "str"),
        (["ml", "mood_detection", "model_name"], "MOOD_MODEL_NAME", "str"),
        (["ml", "mood_detection", "max_length"], "MOOD_MAX_LENGTH", "int"),
        (["ml", "mood_detection", "prediction_threshold"], "MOOD_PREDICTION_THRESHOLD", "float"),
        (["ml", "summarization", "model_version"], "SUMMARIZATION_MODEL_VERSION", "str"),
        (["ml", "summarization", "model_name"], "SUMMARIZATION_MODEL_NAME", "str"),
        (["ml", "summarization", "max_input_length"], "SUMMARIZATION_MAX_INPUT_LENGTH", "int"),
        (["ml", "summarization", "max_summary_length"], "SUMMARIZATION_MAX_SUMMARY_LENGTH", "int"),
        (["ml", "summarization", "min_summary_length"], "SUMMARIZATION_MIN_SUMMARY_LENGTH", "int"),
        (["ml", "summarization", "num_beams"], "SUMMARIZATION_NUM_BEAMS", "int"),
        # API settings
        (["api", "default_limit"], "API_DEFAULT_LIMIT", "int"),
        (["api", "max_limit"], "API_MAX_LIMIT", "int"),
        (["api", "request_timeout"], "API_REQUEST_TIMEOUT", "int"),
        (["api", "request_max_retries"], "API_REQUEST_MAX_RETRIES", "int"),
        (["api", "google_books_page_size"], "API_GOOGLE_BOOKS_PAGE_SIZE", "int"),
        (["api", "tmdb_max_pages"], "API_TMDB_MAX_PAGES", "int"),
        (["api", "tmdb_results_per_page"], "API_TMDB_RESULTS_PER_PAGE", "int"),
        (["api", "tmdb_default_max_results"], "API_TMDB_DEFAULT_MAX_RESULTS", "int"),
        (["api", "tmdb_mood_movies_limit"], "API_TMDB_MOOD_MOVIES_LIMIT", "int"),
        (["api", "tmdb_filtered_limit"], "API_TMDB_FILTERED_LIMIT", "int"),
        # App/Server/Logging settings (from previous step)
        (["app", "timezone"], "APP_TIMEZONE", "str"),
        (["app", "enable_llm"], "ENABLE_LLM", "bool"),
        (["app", "enable_insights"], "ENABLE_INSIGHTS", "bool"),
        (["app", "force_color"], "FORCE_COLOR", "bool"),
        (["app", "hf_hub_disable_xet"], "HF_HUB_DISABLE_XET", "bool"),
        (["app", "tf_cpp_min_log_level"], "TF_CPP_MIN_LOG_LEVEL", "str"),
        (["server", "port"], "PORT", "int"),
        (["server", "flask_debug"], "FLASK_DEBUG", "bool"),
        (["server", "disable_reloader"], "DISABLE_RELOADER", "bool"),
        (["logging", "app_level"], "APP_LOG_LEVEL", "str"),
        (["logging", "werkzeug_level"], "WERKZEUG_LOG_LEVEL", "str"),
        (["logging", "firebase_level"], "FIREBASE_LOG_LEVEL", "str"),
        # Processing settings
        (["processing", "summary_fallback_length"], "PROCESSING_SUMMARY_FALLBACK_LENGTH", "int"),
        # Features settings
        (["features", "mood_tracking_enabled_default"], "FEATURES_MOOD_TRACKING_ENABLED_DEFAULT", "bool"),
        # Concurrency settings
        (["concurrency", "intent_builder_max_workers"], "CONCURRENCY_INTENT_BUILDER_MAX_WORKERS", "int"),
        # Cache settings
        (["cache", "max_age_hours"], "MEDIA_CACHE_MAX_AGE_HOURS", "int"),
        (["cache", "fetch_limit"], "MEDIA_CACHE_FETCH_LIMIT", "int"),
        (["cache", "batch_size"], "MEDIA_CACHE_BATCH_SIZE", "int"),
        (["cache", "schema_version"], "MEDIA_CACHE_SCHEMA_VERSION", "str"),
        # Insights settings
        (["insights", "use_gemini"], "INSIGHTS_USE_GEMINI", "bool"),
        (["insights", "gemini_model_name"], "INSIGHTS_GEMINI_MODEL_NAME", "str"),
        (["insights", "gemini_max_retries"], "INSIGHTS_GEMINI_MAX_RETRIES", "int"),
        (["insights", "backend"], "INSIGHTS_BACKEND", "str"),
        (["insights", "ollama_model"], "INSIGHTS_OLLAMA_MODEL", "str"),
        (["insights", "ollama_base_url"], "INSIGHTS_OLLAMA_BASE_URL", "str"),
        (["insights", "hf_model_name"], "INSIGHTS_HF_MODEL_NAME", "str"),
        (["insights", "hf_model_dir"], "INSIGHTS_HF_MODEL_DIR", "str"),
        (["insights", "temperature"], "INSIGHTS_TEMPERATURE", "float"),
        (["insights", "batch_size"], "INSIGHTS_BATCH_SIZE", "int"),
        (["insights", "max_new_tokens"], "INSIGHTS_MAX_NEW_TOKENS", "int"),
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

