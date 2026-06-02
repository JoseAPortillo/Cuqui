"""SQLite storage adapter — implements ``Storage`` protocol via sqlite3."""

from cuqui.adapters.storage_sqlite.adapter import SqliteTimerStore

__all__ = [
    "SqliteTimerStore",
]
