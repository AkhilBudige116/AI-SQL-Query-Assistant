"""
Unit and Integration Tests for Multiple MySQL Database Support.
Tests:
- Dynamic database discovery and system schema filtering
- Connection switching across authorized databases
- Per-database dynamic schema introspection and caching
- Dynamic SQLGlot AST validation and cross-database query isolation
- Dynamic query execution in specific databases
- Agent workflow switching between databases
"""

import pytest
from database.db_connection import get_available_databases, test_connection as check_db_connection
from tools.schema_tool import get_approved_table_names, get_database_schema_summary
from tools.sql_validator import validate_sql_query
from tools.sql_executor import execute_sql
from agent.sql_agent import AISQLAgent


class TestMultipleDatabases:

    def test_get_available_databases(self):
        dbs = get_available_databases()
        assert isinstance(dbs, list)
        assert len(dbs) >= 2
        # Default database must be first
        assert dbs[0] == "ai_sql_assistant"
        # System databases must be excluded
        system_schemas = {"information_schema", "mysql", "performance_schema", "sys"}
        for s in system_schemas:
            assert s not in dbs

    def test_dynamic_database_connections(self):
        # Default database connection
        ok1, msg1 = check_db_connection(database="ai_sql_assistant")
        assert ok1 is True
        assert "ai_sql_assistant" in msg1

        # Second database connection (bike_store)
        ok2, msg2 = check_db_connection(database="bike_store")
        assert ok2 is True
        assert "bike_store" in msg2

        # Invalid database connection
        ok3, msg3 = check_db_connection(database="non_existent_database_12345")
        assert ok3 is False

    def test_dynamic_schema_retrieval(self):
        # ai_sql_assistant tables
        tables_ai = get_approved_table_names("ai_sql_assistant")
        assert "employees" in tables_ai
        assert "departments" in tables_ai
        assert "products" not in tables_ai

        # bike_store tables
        tables_bike = get_approved_table_names("bike_store")
        assert "products" in tables_bike
        assert "categories" in tables_bike
        assert "employees" not in tables_bike

        # Summaries reflect active database
        summary_ai = get_database_schema_summary("ai_sql_assistant")
        assert "ai_sql_assistant" in summary_ai
        assert "employees" in summary_ai

        summary_bike = get_database_schema_summary("bike_store")
        assert "bike_store" in summary_bike
        assert "products" in summary_bike

    def test_dynamic_sql_validation_isolation(self):
        # Allowed in ai_sql_assistant
        v1, sql1, _ = validate_sql_query("SELECT * FROM employees", current_db="ai_sql_assistant")
        assert v1 is True
        assert "LIMIT" in sql1

        # Disallowed in ai_sql_assistant (products table belongs to bike_store)
        v2, _, msg2 = validate_sql_query("SELECT * FROM products", current_db="ai_sql_assistant")
        assert v2 is False
        assert "not authorized" in msg2

        # Allowed in bike_store
        v3, sql3, _ = validate_sql_query("SELECT * FROM products", current_db="bike_store")
        assert v3 is True

        # Disallowed in bike_store (employees belongs to ai_sql_assistant)
        v4, _, msg4 = validate_sql_query("SELECT * FROM employees", current_db="bike_store")
        assert v4 is False
        assert "not authorized" in msg4

        # Cross-database reference rejection
        v5, _, msg5 = validate_sql_query("SELECT * FROM mysql.user", current_db="ai_sql_assistant")
        assert v5 is False
        assert "Cross-database queries are not allowed" in msg5

    def test_dynamic_sql_execution(self):
        # Execute query on ai_sql_assistant
        res_ai = execute_sql("SELECT COUNT(*) AS total FROM employees", database="ai_sql_assistant")
        assert res_ai["success"] is True
        assert res_ai["database"] == "ai_sql_assistant"
        assert res_ai["rows"][0]["total"] >= 50

        # Execute query on bike_store
        res_bike = execute_sql("SELECT COUNT(*) AS total FROM products", database="bike_store")
        assert res_bike["success"] is True
        assert res_bike["database"] == "bike_store"
        assert res_bike["rows"][0]["total"] > 0

    def test_agent_dynamic_database_queries(self):
        agent = AISQLAgent(database="ai_sql_assistant")

        # 1. Query ai_sql_assistant
        res1 = agent.process_query("Count all employees", db_name="ai_sql_assistant")
        assert res1["success"] is True
        assert res1["database"] == "ai_sql_assistant"
        assert "employees" in res1["sql"].lower()

        # 2. Switch to bike_store and query
        agent.set_database("bike_store")
        assert agent.get_database() == "bike_store"

        res2 = agent.process_query("Count total products by category", db_name="bike_store")
        assert res2["success"] is True
        assert res2["database"] == "bike_store"
        assert "products" in res2["sql"].lower() or "categories" in res2["sql"].lower()
