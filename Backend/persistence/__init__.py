"""
Persistence layer for Pocket Journal.

This package is the single source of truth for all
Firestore database interactions.

DO NOT place business logic here.
DO NOT change return structures used by services.
"""

from .db_manager import DBManager
from .database_schema import DatabaseSchema

__all__ = [
    "DBManager",
    "DatabaseSchema",
]
