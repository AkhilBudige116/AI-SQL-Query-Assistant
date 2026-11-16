"""
Synthetic sample data generator for ai_sql_assistant database.
Populates realistic business records:
- 8 Departments
- 75 Employees (including a few with NULL department for LEFT JOIN testing)
- 75 Customers (including several in Hyderabad and other major cities)
- 160 Orders across multiple dates and statuses
"""

import sys
import os
import random
from datetime import datetime, date, timedelta
from faker import Faker
import mysql.connector

# Add parent directory to path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import get_db_config, get_mysql_connection


def seed_sample_data(force: bool = False):
    """
    Populates sample data if tables are currently empty.
    If force=True, appends records even if tables have data.
    """
    fake = Faker("en_IN")  # Realistic Indian and international business context
    Faker.seed(42)
    random.seed(42)

    # Use admin connection for inserting records
    conn = get_mysql_connection(as_admin=True)
    cursor = conn.cursor()

    # 1. Check if data already exists
    cursor.execute("SELECT COUNT(1) FROM departments;")
    dept_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(1) FROM employees;")
    emp_count = cursor.fetchone()[0]

    if not force and (dept_count > 0 or emp_count > 0):
        print(f"Sample data already present (Departments: {dept_count}, Employees: {emp_count}). Skipping seeding.")
        cursor.close()
        conn.close()
        return

    print("Populating synthetic business data...")

    # 2. Departments
    departments_data = [
        ("Engineering", "Bengaluru"),
        ("Data Science", "Hyderabad"),
        ("Human Resources", "Mumbai"),
        ("Marketing", "Delhi"),
        ("Sales", "Hyderabad"),
        ("Finance", "Mumbai"),
        ("Operations", "Pune"),
        ("Customer Support", "Chennai"),
    ]

    dept_ids = []
    for dept_name, loc in departments_data:
        cursor.execute(
            "INSERT INTO departments (department_name, location) VALUES (%s, %s)",
            (dept_name, loc)
        )
        dept_ids.append(cursor.lastrowid)

    print(f"Inserted {len(dept_ids)} departments.")

    # 3. Employees
    job_titles_by_dept = {
        "Engineering": ["Software Engineer", "Senior Software Engineer", "DevOps Engineer", "Frontend Developer", "Backend Lead"],
        "Data Science": ["Data Analyst", "Data Scientist", "ML Engineer", "BI Specialist", "AI Researcher"],
        "Human Resources": ["HR Executive", "Talent Acquisition Specialist", "HR Manager", "HR Generalist"],
        "Marketing": ["Digital Marketer", "Content Strategist", "SEO Specialist", "Marketing Lead"],
        "Sales": ["Sales Associate", "Account Executive", "Sales Manager", "Business Development Lead"],
        "Finance": ["Financial Analyst", "Accountant", "Finance Manager", "Auditor"],
        "Operations": ["Operations Manager", "Supply Chain Analyst", "Logistics Coordinator"],
        "Customer Support": ["Support Specialist", "Customer Success Lead", "Technical Support Engineer"],
    }

    cities = ["Hyderabad", "Bengaluru", "Mumbai", "Pune", "Delhi", "Chennai", "Kolkata", "Ahmedabad"]

    # Generate 75 employees
    employees = []
    base_date = date(2021, 1, 1)
    end_date = date(2025, 12, 31)
    days_range = (end_date - base_date).days

    for i in range(75):
        emp_name = fake.name()
        # Ensure a few employees have department_id as None (NULL in SQL) for LEFT JOIN testing
        if i in (12, 34, 68):
            d_id = None
            title = "Special Advisor"
        else:
            d_idx = random.randint(0, len(departments_data) - 1)
            d_id = dept_ids[d_idx]
            dept_name = departments_data[d_idx][0]
            title = random.choice(job_titles_by_dept[dept_name])

        # Salaries ranging from 42,000 to 175,000
        salary = round(random.uniform(42000, 175000), 2)
        joining = base_date + timedelta(days=random.randint(0, days_range))
        city = random.choice(cities)

        employees.append((emp_name, d_id, salary, joining, title, city))

    cursor.executemany(
        """
        INSERT INTO employees (employee_name, department_id, salary, joining_date, job_title, city)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        employees
    )
    print(f"Inserted {len(employees)} employees.")

    # 4. Customers
    # 75 customers with realistic details, including multiple in Hyderabad
    customers = []
    for i in range(75):
        cust_name = fake.name()
        city = random.choice(cities)
        # Ensure at least 15 customers are in Hyderabad for testing
        if i % 5 == 0:
            city = "Hyderabad"
        email = f"{cust_name.lower().replace(' ', '.')}.{i+100}@example.com"
        customers.append((cust_name, city, email))

    cursor.executemany(
        """
        INSERT INTO customers (customer_name, city, email)
        VALUES (%s, %s, %s)
        """,
        customers
    )
    print(f"Inserted {len(customers)} customers.")

    # Fetch customer IDs
    cursor.execute("SELECT customer_id FROM customers")
    cust_ids = [row[0] for row in cursor.fetchall()]

    # 5. Orders
    # 160 orders spread over 2024 to 2026
    orders = []
    statuses = ["Completed", "Delivered", "Processing", "Pending", "Cancelled"]
    status_weights = [0.45, 0.30, 0.12, 0.08, 0.05]

    order_base_date = date(2024, 1, 1)
    order_days_range = 750  # ~2 years of orders

    for i in range(160):
        c_id = random.choice(cust_ids)
        amount = round(random.uniform(75.0, 4850.0), 2)
        o_date = order_base_date + timedelta(days=random.randint(0, order_days_range))
        status = random.choices(statuses, weights=status_weights)[0]
        orders.append((c_id, amount, o_date, status))

    cursor.executemany(
        """
        INSERT INTO orders (customer_id, order_amount, order_date, order_status)
        VALUES (%s, %s, %s, %s)
        """,
        orders
    )
    print(f"Inserted {len(orders)} orders.")

    conn.commit()
    cursor.close()
    conn.close()
    print("Sample data populated successfully!")


if __name__ == "__main__":
    seed_sample_data(force=False)
