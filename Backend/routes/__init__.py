# routes/__init__.py
# Central registry for route modules. Each module exposes a `register(app, deps)` function.

def register_all(app, deps: dict):
    """Register all route modules with the Flask app.

    deps: a dict containing dependencies required by route handlers, e.g.
      {
        "login_required": login_required,
        "get_db": get_db,
        "journal_entries": journal_entries,
        "insights_service": insights_service,
        "export_service": export_service,
        "stats_service": stats_service,
        "media_recommendations": media_recommendations,
        "health_service": health_service,
        "PREDICTOR": PREDICTOR,
        "SUMMARIZER": SUMMARIZER,
      }
    """
    # Import route modules lazily to avoid import-time side effects / circular imports
    from . import process_entry as _process_entry
    from . import entries as _entries
    from . import insights as _insights
    from . import media as _media
    from . import export_route as _export_route
    from . import stats as _stats
    from . import health as _health
    from . import home as _home
    from . import auth as _auth
    from . import user as _user
    from . import app_meta as _app_meta

    _process_entry.register(app, deps)
    _entries.register(app, deps)
    _insights.register(app, deps)
    _media.register(app, deps)
    _export_route.register(app, deps)
    _stats.register(app, deps)
    _health.register(app, deps)
    _home.register(app, deps)
    _auth.register(app, deps)
    _user.register(app, deps)
    _app_meta.register(app, deps)
