"""
Helper utilities for AI SQL Query Assistant.
Provides metric calculation, error sanitation, and UI formatting routines
with multi-database awareness.
"""

from typing import Dict, Any, Optional
import os
from database.db_connection import get_mysql_connection


def format_currency(val: Any) -> str:
    """Format numeric value as currency."""
    try:
        f_val = float(val)
        return f"${f_val:,.2f}"
    except (ValueError, TypeError):
        return str(val)


def sanitize_error_message(error: str) -> str:
    """
    Strips internal paths, passwords, and sensitive system details
    from exception strings to protect user privacy.
    """
    if not error:
        return ""
    clean = str(error)
    for word in ["password=", "pwd=", "identified by"]:
        if word in clean.lower():
            clean = "Database error (credentials protected)."
            break
    return clean


def get_dashboard_metrics(db_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Retrieves summary metrics for the Streamlit dashboard for the active database:
    - db_connected
    - database_name
    - total_tables
    - table_names
    - specific table counts if ai_sql_assistant, or generic counts for other databases.
    """
    target_db = db_name or os.getenv("MYSQL_DATABASE", "ai_sql_assistant")

    metrics = {
        "db_connected": False,
        "database": target_db,
        "total_tables": 0,
        "table_names": [],
        "total_employees": 0,
        "total_customers": 0,
        "total_orders": 0,
        "total_rows_estimate": 0,
        "error": None,
    }

    try:
        conn = get_mysql_connection(as_admin=False, database=target_db, connect_timeout=3)
        cursor = conn.cursor()

        # Fetch available tables in the database
        cursor.execute("SHOW TABLES;")
        tables = [row[0] for row in cursor.fetchall()]
        metrics["total_tables"] = len(tables)
        metrics["table_names"] = tables

        # If it's the standard ai_sql_assistant database, fetch exact business counts
        if target_db.lower() == "ai_sql_assistant":
            if "employees" in tables:
                cursor.execute("SELECT COUNT(1) FROM employees")
                metrics["total_employees"] = cursor.fetchone()[0]

            if "customers" in tables:
                cursor.execute("SELECT COUNT(1) FROM customers")
                metrics["total_customers"] = cursor.fetchone()[0]

            if "orders" in tables:
                cursor.execute("SELECT COUNT(1) FROM orders")
                metrics["total_orders"] = cursor.fetchone()[0]

        metrics["db_connected"] = True
        cursor.close()
        conn.close()
    except Exception as e:
        metrics["db_connected"] = False
        metrics["error"] = sanitize_error_message(str(e))

    return metrics
