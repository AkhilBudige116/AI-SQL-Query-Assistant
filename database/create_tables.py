"""
Database initialization script for MySQL.
Creates the ai_sql_assistant database, tables, relationships, indexes,
and read-only execution user if they do not exist.
"""

import sys
import os
import mysql.connector
from dotenv import load_dotenv

# Add parent directory to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import get_db_config

load_dotenv()


def init_database_and_tables():
    """
    Creates the database, tables, foreign keys, and indexes.
    Uses admin credentials to perform schema setup.
    """
    cfg = get_db_config(as_admin=True)

    # 1. Connect to MySQL server without selecting a database first
    conn = mysql.connector.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
    )
    cursor = conn.cursor()

    db_name = cfg["database"]
    print(f"Creating database '{db_name}' if not exists...")
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    cursor.execute(f"USE `{db_name}`;")

    # 2. Create tables
    tables = {
        "departments": """
            CREATE TABLE IF NOT EXISTS departments (
                department_id INT AUTO_INCREMENT PRIMARY KEY,
                department_name VARCHAR(100) NOT NULL,
                location VARCHAR(100) NOT NULL
            ) ENGINE=InnoDB;
        """,
        "employees": """
            CREATE TABLE IF NOT EXISTS employees (
                employee_id INT AUTO_INCREMENT PRIMARY KEY,
                employee_name VARCHAR(100) NOT NULL,
                department_id INT NULL,
                salary DECIMAL(10,2) NOT NULL,
                joining_date DATE NOT NULL,
                job_title VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                CONSTRAINT fk_employee_department
                    FOREIGN KEY (department_id) REFERENCES departments(department_id)
                    ON DELETE SET NULL
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB;
        """,
        "customers": """
            CREATE TABLE IF NOT EXISTS customers (
                customer_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_name VARCHAR(100) NOT NULL,
                city VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL
            ) ENGINE=InnoDB;
        """,
        "orders": """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                customer_id INT NOT NULL,
                order_amount DECIMAL(10,2) NOT NULL,
                order_date DATE NOT NULL,
                order_status VARCHAR(50) NOT NULL,
                CONSTRAINT fk_order_customer
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE
            ) ENGINE=InnoDB;
        """
    }

    for table_name, ddl in tables.items():
        print(f"Creating table '{table_name}' if not exists...")
        cursor.execute(ddl)

    # 3. Create indexes for performance optimization
    indexes = [
        ("idx_employees_dept", "employees", "department_id"),
        ("idx_employees_salary", "employees", "salary"),
        ("idx_orders_customer", "orders", "customer_id"),
        ("idx_orders_date", "orders", "order_date"),
        ("idx_customers_city", "customers", "city"),
    ]

    for idx_name, table, column in indexes:
        try:
            # Check if index exists
            cursor.execute(f"""
                SELECT COUNT(1) FROM information_schema.statistics
                WHERE table_schema = '{db_name}' AND table_name = '{table}' AND index_name = '{idx_name}'
            """)
            if cursor.fetchone()[0] == 0:
                print(f"Creating index '{idx_name}' on {table}({column})...")
                cursor.execute(f"CREATE INDEX `{idx_name}` ON `{table}` (`{column}`);")
        except Exception as e:
            print(f"Index creation note for {idx_name}: {e}")

    # 4. Ensure read-only user exists and has SELECT permission
    ro_user = os.getenv("MYSQL_USER", "sql_reader")
    ro_pass = os.getenv("MYSQL_PASSWORD", "Reader@2025")
    try:
        print(f"Configuring read-only MySQL user '{ro_user}'...")
        cursor.execute(f"CREATE USER IF NOT EXISTS '{ro_user}'@'localhost' IDENTIFIED BY '{ro_pass}';")
        cursor.execute(f"ALTER USER '{ro_user}'@'localhost' IDENTIFIED BY '{ro_pass}';")
        cursor.execute(f"GRANT SELECT ON `{db_name}`.* TO '{ro_user}'@'localhost';")
        cursor.execute("FLUSH PRIVILEGES;")
        print(f"Granted SELECT permissions to '{ro_user}'@'localhost'.")
    except Exception as e:
        print(f"Note on creating/updating read-only user '{ro_user}': {e}")

    conn.commit()
    cursor.close()
    conn.close()
    print("Database and tables initialized successfully!")


if __name__ == "__main__":
    init_database_and_tables()
