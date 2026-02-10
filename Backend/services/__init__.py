# services package init
# Re-export commonly used service facades for backward compatibility
from . import journal_entries as journal_entries
from .export_service import export_data as export_data
from . import export_service as export_service
from . import insights_service as insights_service
from . import stats_service as stats_service

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
    "process_entry",
    "update_entry",
    "delete_entry",
    "delete_entries_batch",
    "reanalyze_entry",
    "get_single_entry",
    "get_entry_analysis",
    "get_entries_filtered",
]
