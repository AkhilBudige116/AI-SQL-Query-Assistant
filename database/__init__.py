"""
Database package for AI SQL Assistant.
Provides database connection management, table creation, and sample data population.
"""

from .db_connection import (
    get_db_config,
    get_mysql_connection,
    get_sqlalchemy_engine,
    get_available_databases,
    dispose_engines,
    test_connection,
)

__all__ = [
    "get_db_config",
    "get_mysql_connection",
    "get_sqlalchemy_engine",
    "get_available_databases",
    "dispose_engines",
    "test_connection",
]
