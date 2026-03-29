# app.py
import os
import warnings

# Load environment variables first
from dotenv import load_dotenv
load_dotenv()

# Load configuration
from config_loader import get_config
_CFG = get_config()

# Ensure HF opt-out set before any Hugging Face imports
os.environ.setdefault("HF_HUB_DISABLE_XET", str(int(_CFG["app"]["hf_hub_disable_xet"])))

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = str(_CFG["app"]["tf_cpp_min_log_level"])
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="tensorflow")

from flask import Flask, request, jsonify
from functools import wraps
import logging
from utils.log_formatter import ColoredFormatter

# -------------------- Logging --------------------
LOG_LEVEL = _CFG["logging"]["app_level"].upper()
log_fmt = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
logging.basicConfig(level=LOG_LEVEL, format=log_fmt)
logger = logging.getLogger()

# Apply colored formatter to root logger
handler = logger.handlers[0] if logger.handlers else None
if handler:
    handler.setFormatter(ColoredFormatter(log_fmt))

pj_logger = logging.getLogger("pocket_journal")
# Lower specific external loggers
logging.getLogger("werkzeug").setLevel(_CFG["logging"]["werkzeug_level"])
logging.getLogger("firebase_admin").setLevel(_CFG["logging"]["firebase_level"])

# Lower noisy external loggers early (keep minimal)
import logging as _logging
for noisy in ("httpx", "huggingface_hub", "sentence_transformers", "urllib3"):
    try:
        _logging.getLogger(noisy).setLevel(_logging.WARNING)
    except Exception:
        pass

# -------------------- Firebase --------------------
import firebase_admin
from firebase_admin import credentials, auth

# Initialize Firebase at startup (deterministic, fail-fast)
FIREBASE_JSON = os.getenv("FIREBASE_CREDENTIALS_PATH")
if not FIREBASE_JSON:
    raise RuntimeError(
        "FIREBASE_CREDENTIALS_PATH is not set. The application requires a path to the Firebase service account JSON file."
    )

# Resolve relative paths: allow the env var to be either absolute or relative to this file
if not os.path.isabs(FIREBASE_JSON):
    # Candidate relative to this module's directory (Backend/)
    module_relative = os.path.join(os.path.dirname(__file__), FIREBASE_JSON)
    # Candidate relative to the current working directory
    cwd_relative = os.path.abspath(FIREBASE_JSON)
    if os.path.exists(module_relative):
        FIREBASE_JSON = os.path.abspath(module_relative)
    elif os.path.exists(cwd_relative):
        FIREBASE_JSON = cwd_relative
    else:
        raise RuntimeError(
            f"Firebase credentials file not found. Checked: {module_relative} and {cwd_relative}"
        )
else:
    FIREBASE_JSON = os.path.abspath(FIREBASE_JSON)

try:
    cred = credentials.Certificate(FIREBASE_JSON)
    firebase_admin.initialize_app(cred)
    logger.info("Initialized Firebase app using credentials from %s", FIREBASE_JSON)
except Exception as e:
    logger.exception("Failed to initialize Firebase: %s", str(e))
    # Crash fast on startup so misconfiguration is visible immediately
    raise

# -------------------- NEW ARCH IMPORTS (FIXED) --------------------
from services import (
    journal_entries,
    media_recommendations,
    health_service,
)

# New package-backed service imports (keep existing variable names for compatibility)
# Note: export/insights/stats are available via the services package binding below; avoid duplicate imports

# Bind to the names used in app.py directly from services package
import services as _services_pkg
insights_service = _services_pkg.insights_service
export_service = _services_pkg.export_service
stats_service = _services_pkg.stats_service

from persistence.db_manager import DBManager
from services.embeddings import get_embedding_service
from services.media_recommender.cache_store import MediaCacheStore
from ml.utils.model_loader import resolve_model_path

from ml.inference.mood_detection.roberta.predictor import SentencePredictor
from ml.inference.summarization.bart.predictor import SummarizationPredictor
from ml.inference.insight_generation.qwen2.predictor import InsightsPredictor


# -------------------- Lazy singletons --------------------
_db = None
_predictor = None
_summarizer = None
_insights_predictor = None


def get_db():
    global _db
    if _db is None:
        FIREBASE_JSON = os.getenv("FIREBASE_CREDENTIALS_PATH")
        _db = DBManager(firebase_json_path=FIREBASE_JSON)
    return _db


# Initialize cache store once after Firebase is initialized (via DBManager).
cache_store = MediaCacheStore(get_db().db)


def get_predictor():
    global _predictor
    if _predictor is None:
        model_dir = resolve_model_path("mood_detection", "roberta", "v2")
        _predictor = SentencePredictor(model_dir)
    return _predictor


def get_summarizer():
    global _summarizer
    if _summarizer is None:
        try:
            model_dir = resolve_model_path("summarization", "bart", "v2")
            _summarizer = SummarizationPredictor(model_path=model_dir)
        except Exception:
            _summarizer = None
    return _summarizer


def get_insights_predictor():
    global _insights_predictor
    if _insights_predictor is None:
        model_dir = resolve_model_path("insight_generation", "qwen2", "v1")
        _insights_predictor = InsightsPredictor(model_path=model_dir)
    return _insights_predictor

# -------------------- Eager model loading at startup --------------------
try:
    # Load models once at process start so they aren't reloaded per-request
    _predictor = get_predictor()
    _summarizer = get_summarizer()
    # Eagerly initialize embedding service (safe no-op if sentence-transformers missing)
    try:
        _embedding_service = get_embedding_service()
        logger.debug("Eagerly initialized embedding service at startup (device info suppressed)")
    except Exception as ee:
        _embedding_service = None
        logger.warning("Embedding service not available at startup: %s", str(ee))
    logger.info("Eagerly loaded predictor and summarizer at startup")
except Exception as e:
    # Do not fail startup if models unavailable; keep server running and degrade gracefully
    logger.warning("Failed to eagerly load models at startup: %s", str(e))

# Only eagerly load insights predictor if NOT using Gemini backend
# If use_gemini=true, the predictor will be lazily loaded on-demand (if ever needed)
use_gemini = bool(_CFG["ml"]["insight_generation"].get("use_gemini", False))

_insights_predictor = None
if not use_gemini:
    try:
        _insights_predictor = get_insights_predictor()
        logger.info("Eagerly loaded insights predictor at startup (Gemini disabled)")
    except Exception as e:
        logger.warning("Failed to load insights predictor at startup: %s", str(e))
        _insights_predictor = None
else:
    logger.info("Skipping eager load of insights predictor (Gemini enabled)")

# NEW: expose module-level cached references for route handlers to use
PREDICTOR = _predictor
SUMMARIZER = _summarizer
INSIGHTS_PREDICTOR = _insights_predictor

# -------------------- Flask App --------------------
app = Flask(__name__)

ENABLE_LLM = bool(_CFG["app"]["enable_llm"])
ENABLE_INSIGHTS = bool(_CFG["app"]["enable_insights"])


# -------------------- Auth Decorator --------------------
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization")
        if not header or not header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401

        try:
            # Parse Authorization header safely: "Bearer <token>"
            token = header[len("Bearer ") :]
            if not token:
                return jsonify({"error": "Missing or invalid token"}), 401
            decoded_token = auth.verify_id_token(token)
            # Attach only the allowed user fields to request.user (uid and email)
            request.user = {
                "uid": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
            }
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401

        return f(*args, **kwargs)

    return decorated


# -------------------- ROUTES (UNCHANGED LOGIC) --------------------
# Replace manual route definitions with modular route registration
from routes import register_all as register_routes

# Prepare dependency bag for routes
deps = {
    "login_required": login_required,
    "get_db": get_db,
    "db": get_db(),  # Direct reference for services that need DBManager instance
    "cache_store": cache_store,
    "journal_entries": journal_entries,
    "insights_service": insights_service,
    "export_service": export_service,
    "stats_service": stats_service,
    "media_recommendations": media_recommendations,
    "health_service": health_service,
    # Phase 4: Personalization & Advanced Features
    "cold_start_handler": _services_pkg.cold_start_handler,
    "search_service": _services_pkg.search_service,
    "interaction_service": _services_pkg.interaction_service,
    # ML Models & Accessors
    "PREDICTOR": PREDICTOR,
    "SUMMARIZER": SUMMARIZER,
    "INSIGHTS_PREDICTOR": INSIGHTS_PREDICTOR,
    "get_predictor": get_predictor,
    "get_summarizer": get_summarizer,
    "get_insights_predictor": get_insights_predictor,
    "get_embedding_service": get_embedding_service,
    "ENABLE_LLM": ENABLE_LLM,
    "ENABLE_INSIGHTS": ENABLE_INSIGHTS,
}

register_routes(app, deps)


# -------------------- Home Page --------------------
# Home route is registered via routes.home

# -------------------- Run --------------------
if __name__ == "__main__":
    # Default: disable Flask reloader to avoid duplicate model initialization.
    FLASK_DEBUG = bool(_CFG["server"]["flask_debug"])
    DISABLE_RELOADER = bool(_CFG["server"]["disable_reloader"])
    use_reloader = False
    # Allow enabling reloader only if explicitly requested and in debug mode
    if FLASK_DEBUG and not DISABLE_RELOADER:
        use_reloader = True
    app.run(
        host="0.0.0.0",
        port=int(_CFG["server"]["port"]),
        debug=FLASK_DEBUG,
        use_reloader=use_reloader,
    )