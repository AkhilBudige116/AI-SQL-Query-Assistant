"""
Query History Manager for AI SQL Query Assistant.
Maintains session-based and persistent in-memory history of natural language queries,
generated SQL, execution statuses, row counts, and timestamps.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime


class QueryHistoryManager:
    """Manages the history of queries executed during the session."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def add_record(
        self,
        question: str,
        sql: str,
        status: str,
        row_count: int = 0,
        execution_time_sec: float = 0.0,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adds a record to query history."""
        record = {
            "id": len(self._history) + 1,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "sql": sql,
            "status": status,  # "SUCCESS", "VALIDATION_FAILED", "EXECUTION_ERROR"
            "row_count": row_count,
            "execution_time_sec": execution_time_sec,
            "error": error,
        }
        self._history.append(record)
        return record

    def get_all(self) -> List[Dict[str, Any]]:
        """Returns the full query history, newest first."""
        return list(reversed(self._history))

    def get_total_count(self) -> int:
        """Returns total executed queries."""
        return len(self._history)

    def get_successful_count(self) -> int:
        """Returns count of successful executions."""
        return sum(1 for r in self._history if r["status"] == "SUCCESS")

    def clear(self):
        """Clears all query history."""
        self._history.clear()


# Global singleton instance for helper access
history_manager = QueryHistoryManager()
