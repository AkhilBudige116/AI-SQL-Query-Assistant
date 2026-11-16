"""
SQL Validator Tool for AI SQL Query Assistant.
Uses SQLGlot to parse and validate MySQL queries against strict security rules:
- Only read-only SELECT statements (including JOINs, aggregations, subqueries, CTEs)
- Strictly blocks DDL and DML (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, etc.)
- Strictly blocks multi-statement queries (SQL injection prevention)
- Enforces approved table access dynamically based on currently selected database
- Blocks cross-database references to prevent unauthorized database access
- Enforces safe row limits (max 1000, default 100 if none provided)
"""

import os
import re
from typing import Tuple, List, Optional, Set
import sqlglot
from sqlglot import exp

from tools.schema_tool import get_approved_table_names

# Disallowed expression types
FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.TruncateTable,
    exp.Command,
    exp.Set,
    exp.Grant,
    exp.Pragma,
    exp.Kill,
)

DEFAULT_ROW_LIMIT = 100
MAX_ROW_LIMIT = 1000


def clean_sql_string(raw_sql: str) -> str:
    """
    Strips markdown code fences, trailing semicolons, and surrounding whitespace.
    """
    if not raw_sql:
        return ""
    cleaned = raw_sql.strip()
    # Remove markdown code blocks if the LLM wrapped it in ```sql ... ```
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:sql|mysql)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    # Remove single trailing semicolon for cleaner parser handling
    cleaned = cleaned.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    return cleaned


def validate_sql_query(
    query: str,
    approved_tables: Optional[Set[str]] = None,
    current_db: Optional[str] = None,
) -> Tuple[bool, str, str]:
    """
    Validates a generated SQL query using SQLGlot parser.

    Parameters:
        query: The raw SQL string to validate.
        approved_tables: Set of lowercase valid table names for the active database.
        current_db: Name of currently connected database.

    Returns:
        (is_valid: bool, validated_sql: str, message: str)
        If valid: (True, validated_sql_with_limit, "Query is valid and safe to execute.")
        If invalid: (False, original_sql, failure_reason)
    """
    cleaned_sql = clean_sql_string(query)

    if not cleaned_sql:
        return False, query, "Query is empty."

    # Resolve approved tables if not explicitly passed
    if approved_tables is None:
        table_list = get_approved_table_names(current_db)
        valid_tables: Set[str] = set(t.lower() for t in table_list)
    else:
        valid_tables = set(t.lower() for t in approved_tables)

    # 1. Parse using SQLGlot MySQL dialect
    try:
        parsed_statements = sqlglot.parse(cleaned_sql, read="mysql")
    except Exception as parse_err:
        return False, cleaned_sql, f"SQL Syntax Error: Unable to parse query. Details: {str(parse_err)}"

    # 2. Check for multi-statement execution
    if len(parsed_statements) == 0:
        return False, cleaned_sql, "No valid SQL statement found."
    if len(parsed_statements) > 1:
        return False, cleaned_sql, "Validation Rejected: Multiple SQL statements are strictly forbidden."

    statement = parsed_statements[0]
    if statement is None:
        return False, cleaned_sql, "Failed to parse SQL statement."

    # 3. Check statement type - must be SELECT or UNION (including CTEs)
    if not isinstance(statement, (exp.Select, exp.Union)):
        return (
            False,
            cleaned_sql,
            f"Validation Rejected: Only read-only SELECT queries are allowed. Found: {statement.key.upper()}",
        )

    # 4. Check for any forbidden destructive or administrative AST nodes
    for forbidden_type in FORBIDDEN_EXPRESSIONS:
        if statement.find(forbidden_type):
            type_name = forbidden_type.__name__.upper()
            return (
                False,
                cleaned_sql,
                f"Validation Rejected: Destructive or unauthorized operation '{type_name}' is forbidden.",
            )

    # 5. Extract and validate all referenced tables and database qualifiers
    cte_names = [cte.alias.lower() for cte in statement.find_all(exp.CTE)]

    for table_node in statement.find_all(exp.Table):
        tbl_name = table_node.name.lower()
        if not tbl_name or tbl_name in cte_names:
            continue

        # Prevent cross-database querying (e.g., SELECT * FROM other_db.table)
        db_qualifier = table_node.db.lower() if table_node.db else None
        if db_qualifier and current_db:
            if db_qualifier != current_db.lower():
                return (
                    False,
                    cleaned_sql,
                    f"Validation Rejected: Cross-database queries are not allowed. You are connected to '{current_db}', cannot access '{db_qualifier}'.",
                )

        if valid_tables and tbl_name not in valid_tables:
            allowed_preview = ", ".join(sorted(valid_tables)[:8])
            if len(valid_tables) > 8:
                allowed_preview += f" ... ({len(valid_tables)} total)"
            return (
                False,
                cleaned_sql,
                f"Validation Rejected: Access to table '{tbl_name}' is not authorized in database '{current_db or 'current'}'. Allowed tables: {allowed_preview}.",
            )

    # 6. Check and enforce row limit
    limit_node = statement.find(exp.Limit)
    if limit_node:
        try:
            limit_val = int(limit_node.expression.this)
            if limit_val > MAX_ROW_LIMIT:
                limit_node.set("expression", exp.Literal.number(MAX_ROW_LIMIT))
        except (ValueError, AttributeError):
            pass
    else:
        statement = statement.limit(DEFAULT_ROW_LIMIT)

    final_sql = statement.sql(dialect="mysql")
    return True, final_sql, "Query is valid and safe to execute."
