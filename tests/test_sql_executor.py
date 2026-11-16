"""
Integration tests for SQL Executor Tool.
Tests safe execution of valid SELECT queries and error handling for invalid queries.
"""

import pytest
from tools.sql_executor import execute_sql


class TestSQLExecutor:

    def test_execute_valid_count(self):
        result = execute_sql("SELECT COUNT(*) AS total FROM employees")
        assert result["success"] is True
        assert result["row_count"] == 1
        assert result["rows"][0]["total"] >= 50
        assert result["execution_time_sec"] >= 0.0

    def test_execute_valid_order_by_limit(self):
        result = execute_sql("SELECT employee_id, employee_name, salary FROM employees ORDER BY salary DESC LIMIT 5")
        assert result["success"] is True
        assert result["row_count"] == 5
        assert len(result["columns"]) == 3
        # Check ordering
        salaries = [r["salary"] for r in result["rows"]]
        assert salaries == sorted(salaries, reverse=True)

    def test_execute_invalid_column_handling(self):
        # Query with non-existent column
        result = execute_sql("SELECT nonexistent_column_xyz FROM employees")
        assert result["success"] is False
        assert result["error_type"] == "DATABASE_ERROR"
        assert "Unknown column" in result["error"] or "1054" in result["error"]

    def test_execute_blocks_unauthorized_table(self):
        # Validation blocks query before database execution
        result = execute_sql("SELECT * FROM non_existent_secret_table")
        assert result["success"] is False
        assert result["error_type"] == "VALIDATION_ERROR"
        assert "not authorized" in result["error"]

    def test_execute_blocks_destructive_query(self):
        result = execute_sql("DELETE FROM customers WHERE customer_id = 1")
        assert result["success"] is False
        assert result["error_type"] == "VALIDATION_ERROR"
