"""
Schema Retrieval Tool for AI SQL Query Assistant.
Supports dynamic database schema introspection and per-database caching.
Inspects database tables, columns, data types, primary keys, and foreign keys.
Provides formatted schema context for the LLM agent and cached metadata.
"""

import sys
import os
from typing import Dict, Any, List, Optional
from sqlalchemy import inspect
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_connection import get_sqlalchemy_engine, get_available_databases

load_dotenv()

# Global cache for schema information per database: {db_name: schema_dict}
_SCHEMA_CACHE: Dict[str, Dict[str, Any]] = {}


def _resolve_db_name(db_name: Optional[str] = None) -> str:
    """Helper to resolve database name to active target or environment default."""
    if db_name:
        return db_name
    return os.getenv("MYSQL_DATABASE", "ai_sql_assistant")


def clear_schema_cache(db_name: Optional[str] = None):
    """Clears the cached schema for a specific database, or all if db_name is None."""
    global _SCHEMA_CACHE
    if db_name:
        _SCHEMA_CACHE.pop(db_name, None)
    else:
        _SCHEMA_CACHE.clear()


def get_raw_database_schema(
    db_name: Optional[str] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Introspects MySQL for the given database using SQLAlchemy Inspector.
    Extracts all tables, columns, data types, PKs, and FKs.
    Caches results per database in memory.
    """
    global _SCHEMA_CACHE
    target_db = _resolve_db_name(db_name)

    if not force_refresh and target_db in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[target_db]

    engine = get_sqlalchemy_engine(as_admin=False, database=target_db)
    inspector = inspect(engine)

    schema_info: Dict[str, Any] = {
        "database": target_db,
        "tables": {},
        "relationships": [],
    }

    try:
        all_table_names = inspector.get_table_names()
    except Exception as e:
        print(f"Error inspecting table names for database '{target_db}': {e}")
        all_table_names = []

    approved_tables_set = set(t.lower() for t in all_table_names)

    for table_name in all_table_names:
        columns = []
        try:
            pk_constraint = inspector.get_pk_constraint(table_name)
            pk_cols = set(pk_constraint.get("constrained_columns", [])) if pk_constraint else set()
        except Exception:
            pk_cols = set()

        try:
            table_cols = inspector.get_columns(table_name)
        except Exception:
            table_cols = []

        for col in table_cols:
            col_name = col["name"]
            col_type = str(col["type"])
            columns.append({
                "name": col_name,
                "type": col_type,
                "nullable": col.get("nullable", True),
                "is_primary_key": col_name in pk_cols,
            })

        fks = []
        try:
            raw_fks = inspector.get_foreign_keys(table_name)
        except Exception:
            raw_fks = []

        for fk in raw_fks:
            referred_table = fk.get("referred_table")
            if referred_table and referred_table.lower() in approved_tables_set:
                fk_info = {
                    "constrained_columns": fk["constrained_columns"],
                    "referred_table": referred_table,
                    "referred_columns": fk["referred_columns"],
                }
                fks.append(fk_info)
                schema_info["relationships"].append({
                    "from_table": table_name,
                    "from_columns": fk["constrained_columns"],
                    "to_table": referred_table,
                    "to_columns": fk["referred_columns"],
                })

        schema_info["tables"][table_name] = {
            "columns": columns,
            "foreign_keys": fks,
            "primary_keys": list(pk_cols),
        }

    _SCHEMA_CACHE[target_db] = schema_info
    return schema_info


def get_database_schema_summary(db_name: Optional[str] = None) -> str:
    """
    Returns a human-readable and LLM-friendly description of the database schema
    for the selected database. Used by the agent prompt and schema tool.
    """
    target_db = _resolve_db_name(db_name)
    schema = get_raw_database_schema(db_name=target_db)
    lines = [f"Database Schema (MySQL Database: `{target_db}`):"]

    if not schema["tables"]:
        lines.append("- (No user tables found or accessible in this database)")
        return "\n".join(lines)

    for table_name, details in schema["tables"].items():
        col_strs = []
        for col in details["columns"]:
            pk_tag = " [PK]" if col["is_primary_key"] else ""
            col_strs.append(f"{col['name']} ({col['type']}){pk_tag}")
        lines.append(f"- Table: `{table_name}`")
        lines.append(f"  Columns: {', '.join(col_strs)}")

    lines.append("\nForeign Key Relationships:")
    if schema["relationships"]:
        for rel in schema["relationships"]:
            from_col = ", ".join(rel["from_columns"])
            to_col = ", ".join(rel["to_columns"])
            lines.append(f"- `{rel['from_table']}.{from_col}` -> `{rel['to_table']}.{to_col}`")
    else:
        lines.append("- None")

    return "\n".join(lines)


def get_approved_table_names(db_name: Optional[str] = None) -> List[str]:
    """Returns the list of valid table names for the specified database."""
    target_db = _resolve_db_name(db_name)
    schema = get_raw_database_schema(db_name=target_db)
    return list(schema["tables"].keys())


def get_approved_columns_by_table(db_name: Optional[str] = None) -> Dict[str, List[str]]:
    """Returns a dictionary of table_name -> list of approved column names."""
    target_db = _resolve_db_name(db_name)
    schema = get_raw_database_schema(db_name=target_db)
    return {
        tbl: [c["name"] for c in details["columns"]]
        for tbl, details in schema["tables"].items()
    }


if __name__ == "__main__":
    print(get_database_schema_summary("ai_sql_assistant"))
    print("\n" + "=" * 50 + "\n")
    print(get_database_schema_summary("bike_store"))
