"""
Unit tests for SQL Validator Tool.
Tests validation of safe queries and rejection of dangerous / unauthorized queries.
"""

import pytest
from tools.sql_validator import validate_sql_query, clean_sql_string


class TestSQLValidator:

    def test_clean_sql_string(self):
        # Markdown cleanup
        assert clean_sql_string("```sql\nSELECT * FROM employees;\n```") == "SELECT * FROM employees"
        assert clean_sql_string("SELECT 1;") == "SELECT 1"
        assert clean_sql_string("  SELECT count(*) FROM orders  ") == "SELECT count(*) FROM orders"

    def test_valid_select_queries(self):
        # Basic SELECT
        valid, sql, msg = validate_sql_query("SELECT employee_id, employee_name FROM employees")
        assert valid is True
        assert "LIMIT" in sql

        # Aggregation with GROUP BY
        valid, sql, msg = validate_sql_query(
            "SELECT d.department_name, AVG(e.salary) FROM departments d JOIN employees e ON d.department_id = e.department_id GROUP BY d.department_name"
        )
        assert valid is True
        assert "department_name" in sql

        # Where clause with date
        valid, sql, msg = validate_sql_query(
            "SELECT * FROM orders WHERE order_date >= '2024-01-01' AND order_status = 'Completed'"
        )
        assert valid is True

        # Left Join for NULL department
        valid, sql, msg = validate_sql_query(
            "SELECT e.employee_name FROM employees e LEFT JOIN departments d ON e.department_id = d.department_id WHERE e.department_id IS NULL"
        )
        assert valid is True

    def test_reject_destructive_queries(self):
        # DROP TABLE
        valid, _, msg = validate_sql_query("DROP TABLE employees")
        assert valid is False
        assert "Only read-only SELECT" in msg or "forbidden" in msg.lower()

        # DELETE
        valid, _, msg = validate_sql_query("DELETE FROM customers WHERE customer_id = 1")
        assert valid is False

        # INSERT
        valid, _, msg = validate_sql_query("INSERT INTO departments (department_name) VALUES ('Hacking')")
        assert valid is False

        # UPDATE
        valid, _, msg = validate_sql_query("UPDATE employees SET salary = 999999 WHERE employee_id = 1")
        assert valid is False

        # TRUNCATE
        valid, _, msg = validate_sql_query("TRUNCATE TABLE orders")
        assert valid is False

        # ALTER
        valid, _, msg = validate_sql_query("ALTER TABLE employees DROP COLUMN salary")
        assert valid is False

    def test_reject_multiple_statements_sql_injection(self):
        # Multi-statement injection attempt
        query = "SELECT * FROM employees; DROP TABLE employees;"
        valid, _, msg = validate_sql_query(query)
        assert valid is False
        assert "Multiple SQL statements" in msg

        query2 = "SELECT 1; SELECT 2"
        valid, _, msg = validate_sql_query(query2)
        assert valid is False
        assert "Multiple SQL statements" in msg

    def test_reject_unauthorized_tables(self):
        # System schemas
        valid, _, msg = validate_sql_query("SELECT * FROM mysql.user")
        assert valid is False
        assert "not authorized" in msg

        # Non-approved arbitrary table
        valid, _, msg = validate_sql_query("SELECT * FROM passwords")
        assert valid is False
        assert "not authorized" in msg

    def test_row_limit_enforcement(self):
        # Unlimited query gets default LIMIT
        valid, sql, _ = validate_sql_query("SELECT * FROM customers")
        assert valid is True
        assert "LIMIT 100" in sql

        # Existing reasonable limit is preserved
        valid, sql, _ = validate_sql_query("SELECT * FROM customers LIMIT 10")
        assert valid is True
        assert "LIMIT 10" in sql

        # Excessive limit is capped to 1000
        valid, sql, _ = validate_sql_query("SELECT * FROM customers LIMIT 50000")
        assert valid is True
        assert "LIMIT 1000" in sql
