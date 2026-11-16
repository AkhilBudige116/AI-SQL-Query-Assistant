"""
Tools package for AI SQL Query Assistant.
Exports all individual agent tools:
- schema_tool: retrieve database schema
- sql_validator: parse and validate safe MySQL queries
- sql_executor: execute read-only queries with timeouts
- result_analyzer: analyze result DataFrames and key metrics
- chart_generator: create Plotly visualizations
"""

from .schema_tool import (
    get_raw_database_schema,
    get_database_schema_summary,
    get_approved_table_names,
    get_approved_columns_by_table,
)
from .sql_validator import validate_sql_query, clean_sql_string
from .sql_executor import execute_sql
from .result_analyzer import analyze_query_results
from .chart_generator import detect_chart_suitability, generate_chart, create_visual_if_suitable

__all__ = [
    "get_raw_database_schema",
    "get_database_schema_summary",
    "get_approved_table_names",
    "get_approved_columns_by_table",
    "validate_sql_query",
    "clean_sql_string",
    "execute_sql",
    "analyze_query_results",
    "detect_chart_suitability",
    "generate_chart",
    "create_visual_if_suitable",
]
