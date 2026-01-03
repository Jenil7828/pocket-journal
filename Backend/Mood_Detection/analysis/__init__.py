"""Package marker for Mood_Detection.analysis

Making this a regular package (instead of relying on implicit namespace
packages) ensures imports like `Backend.Mood_Detection.analysis` work
consistently in environments such as Gunicorn, Docker builds and Windows.
"""

__all__ = ["insight_analyzer"]
