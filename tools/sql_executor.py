"""
SQL Execution Tool for AI SQL Query Assistant.
Safely executes validated MySQL queries using read-only database credentials.
Supports dynamic database targeting, enforces execution timeouts, structures results via Pandas,
and handles errors safely.
"""

import sys
import os
import time
from typing import Dict, Any, List, Optional, Set
import pandas as pd
import mysql.connector
from mysql.connector import Error as MySQLError
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_connection import get_mysql_connection
from tools.sql_validator import validate_sql_query

load_dotenv()

# Execution timeout in seconds
QUERY_TIMEOUT_SECONDS = 5


def execute_sql(
    query: str,
    validate_first: bool = True,
    database: Optional[str] = None,
    approved_tables: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Executes a read-only SQL query against the specified MySQL database.
    Mandatory validation ensures that destructive queries, unauthorized tables,
    or cross-database attacks are blocked.

    Parameters:
        query: SQL string to execute.
        validate_first: Whether to enforce SQLGlot AST validation.
        database: Target MySQL database name (defaults to configured MYSQL_DATABASE).
        approved_tables: Optional set of allowed table names.

    Returns a structured dictionary:
    {
        "success": bool,
        "query": str,
        "sanitized_query": str,
        "database": str,
        "columns": List[str],
        "rows": List[Dict[str, Any]],
        "row_count": int,
        "execution_time_sec": float,
        "dataframe": Optional[pd.DataFrame],
        "error": Optional[str],
        "error_type": Optional[str]
    }
    """
    start_time = time.time()
    target_db = database or os.getenv("MYSQL_DATABASE", "ai_sql_assistant")

    # 1. Mandatory Validation
    sanitized_sql = query
    if validate_first:
        is_valid, validated_sql, val_message = validate_sql_query(
            query=query,
            approved_tables=approved_tables,
            current_db=target_db,
        )
        if not is_valid:
            return {
                "success": False,
                "query": query,
                "sanitized_query": query,
                "database": target_db,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_sec": round(time.time() - start_time, 4),
                "dataframe": pd.DataFrame(),
                "error": val_message,
                "error_type": "VALIDATION_ERROR",
            }
        sanitized_sql = validated_sql

    # 2. Database Connection and Execution
    conn = None
    cursor = None
    try:
        # Connect to the target database using read-only credentials
        conn = get_mysql_connection(
            as_admin=False,
            database=target_db,
            connect_timeout=QUERY_TIMEOUT_SECONDS,
        )
        cursor = conn.cursor(dictionary=True)

        # Set MySQL server-side query timeout (in milliseconds)
        try:
            cursor.execute(f"SET SESSION max_execution_time = {QUERY_TIMEOUT_SECONDS * 1000};")
        except Exception:
            pass

        # Execute query
        cursor.execute(sanitized_sql)
        records = cursor.fetchall()

        # Build DataFrame
        df = pd.DataFrame(records)
        columns = list(df.columns) if not df.empty else (cursor.column_names if cursor.column_names else [])

        # Convert Decimals/Dates to JSON/Pandas friendly formats if needed
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                df[col] = pd.to_numeric(df[col], errors="coerce")

        elapsed = round(time.time() - start_time, 4)

        return {
            "success": True,
            "query": query,
            "sanitized_query": sanitized_sql,
            "database": target_db,
            "columns": list(columns),
            "rows": df.to_dict(orient="records"),
            "row_count": len(df),
            "execution_time_sec": elapsed,
            "dataframe": df,
            "error": None,
            "error_type": None,
        }

    except MySQLError as err:
        elapsed = round(time.time() - start_time, 4)
        return {
            "success": False,
            "query": query,
            "sanitized_query": sanitized_sql,
            "database": target_db,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_sec": elapsed,
            "dataframe": pd.DataFrame(),
            "error": f"Database Error ({err.errno}): {err.msg}",
            "error_type": "DATABASE_ERROR",
        }
    except Exception as ex:
        elapsed = round(time.time() - start_time, 4)
        return {
            "success": False,
            "query": query,
            "sanitized_query": sanitized_sql,
            "database": target_db,
            "columns": [],
            "rows": [],
            "row_count": 0,
            "execution_time_sec": elapsed,
            "dataframe": pd.DataFrame(),
            "error": f"Execution Error: {str(ex)}",
            "error_type": "SYSTEM_ERROR",
        }
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    # Test query on ai_sql_assistant
    res1 = execute_sql("SELECT count(*) as cnt FROM employees", database="ai_sql_assistant")
    print("ai_sql_assistant count:", res1["rows"])

    # Test query on bike_store
    res2 = execute_sql("SELECT count(*) as cnt FROM products", database="bike_store")
    print("bike_store products count:", res2["rows"])
