"""
Database connection manager for MySQL.
Loads configuration from environment variables and provides both
mysql-connector-python connections and SQLAlchemy engines.
Supports dynamic database selection and engine lifecycle management.
"""

import os
from typing import Dict, Any, Tuple, List, Optional
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import Error as MySQLError
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

# Ensure environment variables are loaded
load_dotenv()

# System schemas to filter out from user selection
SYSTEM_DATABASES = {"information_schema", "mysql", "performance_schema", "sys"}

# Active engine cache by database name: {db_name: Engine}
_ENGINE_CACHE: Dict[str, Engine] = {}


def get_db_config(as_admin: bool = False, database: Optional[str] = None) -> Dict[str, Any]:
    """
    Get MySQL connection parameters from environment variables.
    If database is provided, overrides the default MYSQL_DATABASE.
    If as_admin is True, uses admin credentials for migration/seeding.
    Otherwise uses the read-only credentials for safe query execution.
    """
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    default_db = os.getenv("MYSQL_DATABASE", "ai_sql_assistant")
    target_database = database if database is not None else default_db

    if as_admin:
        user = os.getenv("MYSQL_ADMIN_USER", os.getenv("MYSQL_USER", "root"))
        password = os.getenv("MYSQL_ADMIN_PASSWORD", os.getenv("MYSQL_PASSWORD", ""))
    else:
        user = os.getenv("MYSQL_USER", "sql_reader")
        password = os.getenv("MYSQL_PASSWORD", "")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": target_database,
    }


def get_mysql_connection(
    as_admin: bool = False,
    database: Optional[str] = None,
    connect_timeout: int = 5,
):
    """
    Establish and return a raw mysql.connector connection.
    Supports dynamic database selection and execution timeouts.
    """
    cfg = get_db_config(as_admin=as_admin, database=database)
    conn_kwargs = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "password": cfg["password"],
        "connection_timeout": connect_timeout,
    }
    if cfg["database"]:
        conn_kwargs["database"] = cfg["database"]

    return mysql.connector.connect(**conn_kwargs)


def get_sqlalchemy_engine(
    as_admin: bool = False,
    database: Optional[str] = None,
) -> Engine:
    """
    Create and return a SQLAlchemy engine using pymysql dialect.
    Caches engine per database name and safely encodes user credentials.
    """
    cfg = get_db_config(as_admin=as_admin, database=database)
    db_name = cfg["database"] or ""
    cache_key = f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{db_name}"

    if cache_key in _ENGINE_CACHE:
        return _ENGINE_CACHE[cache_key]

    db_url = URL.create(
        drivername="mysql+pymysql",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=db_name if db_name else None,
    )
    engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)
    _ENGINE_CACHE[cache_key] = engine
    return engine


def dispose_engines():
    """Properly disposes of all cached SQLAlchemy connection pool engines."""
    global _ENGINE_CACHE
    for engine in _ENGINE_CACHE.values():
        try:
            engine.dispose()
        except Exception:
            pass
    _ENGINE_CACHE.clear()


def get_available_databases(as_admin: bool = False) -> List[str]:
    """
    Queries the connected MySQL server for all databases accessible
    by the configured account, filtering out internal system schemas.
    The default database (ai_sql_assistant) is guaranteed to appear first.
    """
    try:
        conn = get_mysql_connection(as_admin=as_admin, database=None, connect_timeout=3)
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES;")
        raw_dbs = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        # Filter out system databases
        user_dbs = [db for db in raw_dbs if db.lower() not in SYSTEM_DATABASES]

        # Prioritize ai_sql_assistant as the default
        default_db = os.getenv("MYSQL_DATABASE", "ai_sql_assistant")
        if default_db in user_dbs:
            user_dbs.remove(default_db)
            user_dbs.sort()
            return [default_db] + user_dbs
        else:
            user_dbs.sort()
            return user_dbs

    except Exception as e:
        print(f"Error fetching accessible databases: {e}")
        # Fallback to configured default database
        default_db = os.getenv("MYSQL_DATABASE", "ai_sql_assistant")
        return [default_db]


def test_connection(as_admin: bool = False, database: Optional[str] = None) -> Tuple[bool, str]:
    """
    Test connectivity to the MySQL database.
    Returns (True, "Connected successfully") or (False, error_message).
    """
    try:
        conn = get_mysql_connection(as_admin=as_admin, database=database, connect_timeout=3)
        if conn.is_connected():
            server_info = getattr(conn, "server_info", None) or conn.get_server_info()
            conn.close()
            target_db = database or os.getenv("MYSQL_DATABASE", "ai_sql_assistant")
            return True, f"Connected to MySQL {server_info} (Database: {target_db})."
        return False, "Failed to connect to MySQL."
    except MySQLError as err:
        return False, f"MySQL Error ({err.errno}): {err.msg}"
    except Exception as ex:
        return False, f"Connection Error: {str(ex)}"
