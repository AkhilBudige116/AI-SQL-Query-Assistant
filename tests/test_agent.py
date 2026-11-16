"""
End-to-End tests for Single AI SQL Agent.
Tests natural language translation, query execution, and result explanation.
"""

import pytest
from agent.sql_agent import AISQLAgent


@pytest.fixture(scope="module")
def agent():
    return AISQLAgent()


class TestAISQLAgent:

    def test_count_all_employees(self, agent):
        res = agent.process_query("Count all employees")
        assert res["success"] is True
        assert res["status"] == "SUCCESS"
        assert res["row_count"] == 1
        assert "employees" in res["sql"].lower()
        assert len(res["explanation"]) > 10

    def test_find_employees_earning_above_threshold(self, agent):
        res = agent.process_query("Find employees earning above 100000")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "salary" in res["sql"].lower()

    def test_top_5_highest_paid_employees(self, agent):
        res = agent.process_query("Show the top 5 highest-paid employees")
        assert res["success"] is True
        assert res["row_count"] <= 5
        assert "salary" in res["sql"].lower()
        assert "order by" in res["sql"].lower()

    def test_average_salary_by_department(self, agent):
        res = agent.process_query("Calculate average salary by department")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "group by" in res["sql"].lower()
        assert "avg" in res["sql"].lower()

    def test_find_customers_from_hyderabad(self, agent):
        res = agent.process_query("Find customers from Hyderabad")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "hyderabad" in res["sql"].lower()

    def test_count_orders_by_status(self, agent):
        res = agent.process_query("Count orders by status")
        assert res["success"] is True
        assert res["row_count"] > 0
        assert "status" in res["sql"].lower()
        assert "group by" in res["sql"].lower()

    def test_highest_order_amount(self, agent):
        res = agent.process_query("Find the highest order amount")
        assert res["success"] is True
        assert res["row_count"] == 1
        assert "max" in res["sql"].lower() or "order by" in res["sql"].lower()

    def test_destructive_request_rejection(self, agent):
        res = agent.process_query("Drop the employees table now")
        assert res["success"] is False
        assert res["status"] in ("VALIDATION_FAILED", "EXECUTION_ERROR")
