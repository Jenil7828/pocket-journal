# routes/__init__.py
# Central registry for route modules. Each module exposes a `register(app, deps)` function.

def register_all(app, deps: dict):
    """Register all route modules with the Flask app.

    DOMAIN-BASED STRUCTURE - DEPRECATED APIS REMOVED

    ==================== DOMAIN-BASED ROUTES (PRIMARY) ====================
    - journal_domain.py    → /api/v1/journal/... (11 endpoints)
    - insights_domain.py   → /api/v1/insights/... (4 endpoints)
    - media_domain.py      → /api/v1/{media}/... (6+ endpoints)

    ==================== SYSTEM ROUTES (MAINTAINED) ====================
    - auth.py              → /api/v1/auth/... (2 endpoints)
    - user.py              → /api/v1/user/... (3 endpoints)
    - health.py            → /api/v1/health (1 endpoint)
    - stats.py             → /api/v1/stats/... (4 endpoints)
    - export_route.py      → /api/v1/export/... (2 endpoints)
    - home.py              → / (1 endpoint)
    - app_meta.py          → /api/v1/app-meta/... (1+ endpoint)
    - dashboard.py         → /api/v1/dashboard (1 endpoint - BFF)
    - jobs.py              → /job/v1/... (8+ endpoints)

    DEPRECATED ENDPOINTS REMOVED: 12 endpoints
    - 6 journal deprecated (process_entry, entries/...)
    - 1 insights deprecated (generate_insights)
    - 5 media deprecated (media/recommend, movie/recommend, song/recommend, book/recommend, podcast/recommend)
    
    TOTAL: 12 route modules, 45+ endpoints
    
    deps: dependencies dict with all required services
    """
    # Import route modules
    
    # ==================== DOMAIN-BASED ROUTES ====================
    from . import journal_domain as _journal_domain
    from . import insights_domain as _insights_domain
    from . import media_domain as _media_domain

    # ==================== SYSTEM ROUTES ====================
    from . import auth as _auth
    from . import user as _user
    from . import health as _health
    from . import stats as _stats
    from . import export_route as _export_route
    from . import home as _home
    from . import app_meta as _app_meta
    from . import dashboard as _dashboard
    from . import jobs as _jobs
    
    # ==================== REGISTER ROUTES ====================
    
    # 1. DOMAIN-BASED ROUTES (Primary)
    _journal_domain.register(app, deps)
    _insights_domain.register(app, deps)
    _media_domain.register(app, deps)

    # 2. SYSTEM ROUTES
    _auth.register(app, deps)
    _user.register(app, deps)
    _health.register(app, deps)
    _stats.register(app, deps)
    _export_route.register(app, deps)
    _home.register(app, deps)
    _app_meta.register(app, deps)
    _dashboard.register(app, deps)
    _jobs.register(app, deps)
