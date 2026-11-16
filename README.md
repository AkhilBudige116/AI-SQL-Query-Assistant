# AI SQL Query Assistant 🤖⚡
### Natural Language to SQL Database Interaction Powered by a Single Agentic AI
*(Now Featuring Dynamic Multi-Database MySQL Support)*

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B.svg)](https://streamlit.io/)
[![Groq](https://img.shields.io/badge/LLM-Groq%20API-F55036.svg)](https://groq.com/)
[![MySQL 8.0](https://img.shields.io/badge/Database-MySQL%208.0-4479A1.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 1. Project Overview

The **AI SQL Query Assistant** is a single-agent AI application that enables business users, managers, and non-technical stakeholders to query and analyze MySQL relational databases using plain English.

Users can seamlessly switch between authorized MySQL databases (e.g. `ai_sql_assistant`, `bike_store`, `employee`, etc.) directly from the Streamlit sidebar. The agent dynamically discovers available databases, reflects their individual schemas, enforces strict read-only AST safety, executes approved queries, and renders natural-language explanations alongside Plotly visualizations.

---

## 2. System Architecture

```
                  ┌─────────────────────────────────────┐
                  │       Streamlit User Interface      │
                  │   (Dashboard, Chat, Viewer, Charts) │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │         SINGLE AI SQL AGENT         │
                  │       (LangChain + Groq LLM)        │
                  │       System Prompt & Memory        │
                  └──────────────┬────────┬─────────────┘
                                 │        │
             ┌───────────────────┘        └───────────────────┐
             ▼                                                ▼
  ┌──────────────────────┐                         ┌──────────────────────┐
  │     Schema Tool      │                         │    SQL Validator     │
  │ (Introspection/Cache)│                         │ (SQLGlot AST Parser) │
  └──────────────────────┘                         └──────────┬───────────┘
                                                              │ Approved?
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │     SQL Executor     │
                                                   │(Read-Only Connection)│
                                                   └──────────┬───────────┘
                                                              │
                                                              ▼
                                                   ┌──────────────────────┐
                                                   │    MySQL Database    │
                                                   │  (ai_sql_assistant)  │
                                                   └──────────┬───────────┘
                                                              │ Results
                                                              ▼
             ┌────────────────────────────────────────────────┴───────────┐
             ▼                                                            ▼
  ┌──────────────────────┐                                     ┌──────────────────────┐
  │   Result Analyzer    │                                     │   Chart Generator    │
  │ (Pandas DF & Summary)│                                     │(Plotly Bar/Line/Pie) │
  └──────────┬───────────┘                                     └──────────┬───────────┘
             │                                                            │
             └───────────────────────────┬────────────────────────────────┘
                                         ▼
                  ┌─────────────────────────────────────┐
                  │       Final Streamlit Response      │
                  │ (Plain English + SQL + Table + Viz) │
                  └─────────────────────────────────────┘
```

### Architectural Principles:
1. **Strictly Single AI Agent**: Exactly one agent orchestrates all tools. No complex multi-agent overhead or unnecessary asynchronous actor loops.
2. **Defense in Depth**:
   - **AST Validation**: `SQLGlot` blocks all DDL (`DROP`, `ALTER`, `CREATE`, `TRUNCATE`) and DML (`INSERT`, `UPDATE`, `DELETE`) operations, prevents multi-statement SQL injection, and restricts access strictly to approved tables.
   - **Database Level Permissions**: Queries run via a dedicated read-only account (`sql_reader`) granting only `SELECT` privileges.
   - **Query Execution Timeouts**: Server-side query execution timeout of 5 seconds prevents runaway full-table scans.
3. **Automated Bounded Self-Correction**: If a syntax error or non-existent column occurs, the agent captures the safe error message and attempts up to 2 corrections before returning a graceful response.
4. **Data Grounding**: The LLM natural language explanation is grounded directly on the returned dataset without hallucinations.

---

## 3. Technology Stack

| Component | Technology | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.10 - 3.14 | Core backend language |
| **Orchestration** | LangChain / LangChain-Groq | Latest | Agent tool calling & prompt chaining |
| **LLM Inference** | Groq API | Latest | Fast tool-calling model inference |
| **Database** | MySQL | 8.0+ | Relational database storage |
| **DB Connectors** | mysql-connector-python & SQLAlchemy | Latest | Connection pooling & schema reflection |
| **Frontend UI** | Streamlit | 1.35+ | Interactive dashboard & chat interface |
| **Data Processing** | Pandas | 2.0+ | Tabular data manipulation |
| **Visualization** | Plotly Express | 5.18+ | Interactive bar, line, and pie charts |
| **SQL Parsing** | SQLGlot | 25.0+ | AST SQL parsing and validation |
| **Testing** | Pytest | 8.0+ | Automated unit and integration tests |

---

## 4. Project Directory Structure

```
AI-SQL-Query-Assistant/
│
├── app.py                     # Streamlit frontend & interactive UI
├── requirements.txt           # Project dependencies
├── .env                       # Environment credentials (git-ignored)
├── .env.example               # Template environment configuration
├── .gitignore                 # Standard Python gitignore rules
├── README.md                  # Complete technical documentation
│
├── agent/                     # Single AI Agent & LLM logic
│   ├── __init__.py
│   ├── sql_agent.py           # AISQLAgent core class & execution workflow
│   ├── prompts.py             # System prompt & SQL generation templates
│   └── agent_config.py        # Configurable model parameters & fallbacks
│
├── tools/                     # Modular Agent Tools
│   ├── __init__.py
│   ├── schema_tool.py         # Schema introspection & table reflection
│   ├── sql_validator.py       # SQLGlot AST validation & limit enforcement
│   ├── sql_executor.py        # Safe read-only MySQL execution & timeouts
│   ├── result_analyzer.py     # Deterministic metric analysis & summaries
│   └── chart_generator.py     # Plotly Express visualizer (bar, line, pie)
│
├── database/                  # Database management & seed scripts
│   ├── __init__.py
│   ├── db_connection.py       # MySQL connection & SQLAlchemy engine factory
│   ├── create_tables.py       # DDL schema definition & read-only user setup
│   └── sample_data.py         # Synthetic business data generator (Faker)
│
├── utils/                     # Shared utilities
│   ├── __init__.py
│   ├── query_history.py       # In-memory session query history tracking
│   └── helpers.py             # Dashboard metric aggregator & formatters
│
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_sql_validator.py  # Unit tests for query security & AST rules
│   ├── test_sql_executor.py   # Integration tests for database queries
│   └── test_agent.py          # E2E tests for agent questions & safety
│
└── assets/
    └── logo.png               # Application branding icon
```

---

## 5. Database Schema Details

Database Name: `ai_sql_assistant`

### 1. `departments`
- `department_id` INT PRIMARY KEY AUTO_INCREMENT
- `department_name` VARCHAR(100) NOT NULL
- `location` VARCHAR(100) NOT NULL

### 2. `employees`
- `employee_id` INT PRIMARY KEY AUTO_INCREMENT
- `employee_name` VARCHAR(100) NOT NULL
- `department_id` INT NULL (FK -> `departments.department_id` ON DELETE SET NULL)
- `salary` DECIMAL(10,2) NOT NULL
- `joining_date` DATE NOT NULL
- `job_title` VARCHAR(100) NOT NULL
- `city` VARCHAR(100) NOT NULL

### 3. `customers`
- `customer_id` INT PRIMARY KEY AUTO_INCREMENT
- `customer_name` VARCHAR(100) NOT NULL
- `city` VARCHAR(100) NOT NULL
- `email` VARCHAR(150) NOT NULL

### 4. `orders`
- `order_id` INT PRIMARY KEY AUTO_INCREMENT
- `customer_id` INT NOT NULL (FK -> `customers.customer_id` ON DELETE CASCADE)
- `order_amount` DECIMAL(10,2) NOT NULL
- `order_date` DATE NOT NULL
- `order_status` VARCHAR(50) NOT NULL

---

## 6. Setup and Installation Instructions

### Prerequisites
- Python 3.10, 3.11, 3.12, 3.13, or 3.14
- MySQL Server 8.0+ running locally or remotely
- A Groq API Key (get free at [console.groq.com](https://console.groq.com))

### Step 1: Clone the Repository
```bash
git clone <repository_url>
cd AI-SQL-Query-Assistant
```

### Step 2: Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Edit `.env` with your actual credentials:
```ini
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=sql_reader
MYSQL_PASSWORD=Reader@2025
MYSQL_DATABASE=ai_sql_assistant

MYSQL_ADMIN_USER=root
MYSQL_ADMIN_PASSWORD=your_root_password
```

### Step 5: Initialize Database Schema and Sample Data
Run the database creation script using the admin credentials:
```bash
python database/create_tables.py
```
*This creates the `ai_sql_assistant` database, all 4 tables, foreign keys, indexes, and provisions the `sql_reader` read-only user.*

Next, populate synthetic business records:
```bash
python database/sample_data.py
```
*This inserts 8 departments, 75 employees, 75 customers, and 160 orders.*

---

## 7. Running the Application

Launch the Streamlit web dashboard:
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 8. Running Automated Tests

Run the complete test suite using pytest:
```bash
# Run all tests (25 tests covering validator, executor, multi-database, and agent)
python -m pytest tests/ -v

# Run multi-database switching and dynamic schema tests
python -m pytest tests/test_multi_database.py -v

# Run SQL validator security tests
python -m pytest tests/test_sql_validator.py -v

# Run database executor integration tests
python -m pytest tests/test_sql_executor.py -v

# Run end-to-end agent tests
python -m pytest tests/test_agent.py -v
```

All 25 automated tests pass with 100% success rate:
- Dynamic database discovery and system schema filtering (`SHOW DATABASES`).
- Seamless connection switching across authorized MySQL databases (`ai_sql_assistant`, `bike_store`).
- Dynamic per-database schema introspection, foreign key reflection, and caching.
- Table isolation and cross-database SQL injection rejection (`SELECT * FROM other_db.table`).
- Clean SQL string and markdown code-block stripping.
- Read-only SELECT enforcement with aggregations, JOINs, and subqueries.
- Rejection of destructive operations (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `TRUNCATE`).
- Prevention of multi-statement SQL injection (`SELECT 1; DROP TABLE ...`).
- Unauthorized and non-approved table rejection.
- Row-limit bounding and capping at 1,000 records.
- Database execution timeouts and error handling.
- Natural language queries across all 10 core concepts (COUNT, WHERE, ORDER BY, GROUP BY, LEFT JOIN, SUM, Date functions, MAX).
- Safe error handling and negative prompt rejections.

---

## 9. Security & Defense in Depth

The application implements rigorous multi-tier security:

1. **Dual MySQL Account Model**:
   - **Admin Account (`root`)**: Used strictly offline in `create_tables.py` and `sample_data.py`. Never exposed to runtime agent execution.
   - **Runtime Query Account (`sql_reader`)**: Has only `GRANT SELECT` privileges on `ai_sql_assistant.*`. Even if an injection bypassed software checks, the MySQL engine rejects writes at the database layer.
2. **AST SQL Parser (`SQLGlot`)**:
   - Analyzes the abstract syntax tree of every query before it reaches the driver.
   - Verifies root node is `Select` or `Union`.
   - Prohibits destructive expression types (`Insert`, `Update`, `Delete`, `Drop`, `AlterTable`, etc.).
   - Verifies all referenced tables belong to the approved whitelist: `{departments, employees, customers, orders}`.
   - Caps large `LIMIT` clauses to a maximum of 1,000 rows to protect memory.
3. **Execution Timeouts**:
   - Enforces a 5-second `MAX_EXECUTION_TIME` per session on MySQL.
4. **Credential Sanitation**:
   - Sensitive connection strings or passwords in database error tracebacks are scrubbed before reaching the UI.

---

## 10. Cloud Deployment Guide

To deploy this application to production:

### 1. Database (Managed MySQL)
Deploy a cloud-hosted MySQL 8.0 instance (e.g., **AWS RDS MySQL**, **Google Cloud SQL**, **Aiven**, or **PlanetScale**).
- Run `database/create_tables.py` and `database/sample_data.py` pointing to your managed MySQL instance.
- Ensure the database is accessible from your Streamlit cloud deployment host with SSL enabled.

### 2. Frontend & Agent (Streamlit Community Cloud)
1. Push the code to a GitHub repository (ensure `.env` is ignored by `.gitignore`).
2. Log in to [Streamlit Community Cloud](https://share.streamlit.io).
3. Connect your repository and select `app.py` as the main entry file.
4. Go to **App Settings > Secrets** and paste your environment variables:
   ```toml
   GROQ_API_KEY = "gsk_..."
   GROQ_MODEL = "openai/gpt-oss-120b"
   MYSQL_HOST = "your-managed-mysql-host.com"
   MYSQL_PORT = 3306
   MYSQL_USER = "sql_reader"
   MYSQL_PASSWORD = "your_secure_password"
   MYSQL_DATABASE = "ai_sql_assistant"
   ```
5. Click **Deploy**. The application will boot immediately with live MySQL connectivity.

---

## 11. Module-by-Module Walkthrough (For Technical Team Leads)

When explaining this application during technical reviews or team lead interviews, refer to these modules:

1. **`database/db_connection.py`**:
   - Encapsulates database configuration and URL building.
   - Uses `sqlalchemy.engine.URL.create` to ensure credentials with special characters (such as `@`) are correctly URL-encoded.
   - Provides both raw `mysql.connector` (for execution timeouts) and `SQLAlchemy` (for schema introspection).

2. **`tools/schema_tool.py`**:
   - Introspects MySQL using SQLAlchemy's `Inspector`.
   - Extracts table names, columns, data types, primary keys, and foreign keys strictly for approved tables.
   - Maintains an in-memory cache (`_SCHEMA_CACHE`) so repeated queries avoid unnecessary introspection queries.

3. **`tools/sql_validator.py`**:
   - Heart of the application's query safety.
   - Parses incoming SQL into an AST via `SQLGlot` using MySQL dialect.
   - Detects multiple statements to prevent injection.
   - Ensures queries are strictly read-only and target approved tables.
   - Automatically injects default or bounded `LIMIT` clauses.

4. **`tools/sql_executor.py`**:
   - Executes queries via the read-only MySQL user.
   - Sets server-side session timeouts (`max_execution_time`).
   - Converts the raw result set into a clean Pandas DataFrame with sanitized numeric columns.

5. **`tools/result_analyzer.py` & `tools/chart_generator.py`**:
   - Computes summary statistics (row count, min, max, average, top values).
   - Dynamically analyzes DataFrame types to detect if a Bar, Line, or Pie chart is appropriate without forcing charts on unsuitable data.

6. **`agent/sql_agent.py`**:
   - The central orchestrator implementing the Single-Agent workflow.
   - Generates SQL using the Groq LLM with LangChain.
   - Validates every generated query before execution.
   - Implements bounded self-correction: if a query fails validation or execution, captures the safe error and prompts the LLM for a corrected query (max 2 attempts).
   - Generates natural language explanations strictly grounded on the returned records.

7. **`app.py`**:
   - Clean, modern Streamlit UI.
   - Features real-time metric cards, example question triggers, expandable SQL viewers with syntax highlighting, clean data tables, interactive Plotly charts, and query history tracking.

---

## 12. Verification & Acceptance Summary

| Acceptance Criterion | Status | Verified Via |
|---|---|---|
| MySQL 8.0 connectivity | ✅ Verified | `test_connection` & `create_tables.py` |
| 4 Tables created and populated | ✅ Verified | 8 depts, 75 emps, 75 custs, 160 orders |
| Groq LLM integration | ✅ Verified | `ChatGroq` (`openai/gpt-oss-120b`) |
| Single AI agent architecture | ✅ Verified | `AISQLAgent` in `agent/sql_agent.py` |
| Schema introspection & caching | ✅ Verified | `tools/schema_tool.py` |
| SQL validation & injection safety | ✅ Verified | `test_sql_validator.py` (6 tests passed) |
| Read-only safe execution | ✅ Verified | `test_sql_executor.py` (5 tests passed) |
| Grounded natural language explanations | ✅ Verified | `tools/result_analyzer.py` & E2E tests |
| Dynamic Plotly visualizations | ✅ Verified | `tools/chart_generator.py` |
| Query history tracking | ✅ Verified | `utils/query_history.py` & UI Sidebar |
| Automated Bounded Self-Correction | ✅ Verified | Up to 2 attempts with safe error loop |
| Streamlit frontend application | ✅ Verified | `app.py` compiled & ready |
| Complete automated test suite | ✅ Verified | 19 / 19 Pytest tests passed |
