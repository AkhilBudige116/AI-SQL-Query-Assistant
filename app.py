"""
AI SQL Query Assistant - Main Streamlit Application
Natural Language to SQL Powered by a Single Agentic AI Assistant.
Supports Dynamic Selection and Querying Across Multiple Authorized MySQL Databases.
"""

import os
import sys
from typing import Optional
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# Ensure the root project directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from agent.sql_agent import AISQLAgent
from agent.agent_config import SUPPORTED_GROQ_MODELS, DEFAULT_MODEL, DEFAULT_DATABASE
from database.db_connection import get_available_databases
from tools.schema_tool import get_approved_table_names
from utils.helpers import get_dashboard_metrics, sanitize_error_message
from utils.query_history import history_manager

load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="AI SQL Query Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    /* Metric Card Styling */
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 14px 18px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.40rem;
        font-weight: 700;
        color: #1E293B;
    }
    /* Status Badges */
    .status-badge-success {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.80rem;
        font-weight: 600;
        display: inline-block;
    }
    .status-badge-error {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.80rem;
        font-weight: 600;
        display: inline-block;
    }
    .db-tag {
        background: #EFF6FF;
        color: #1D4ED8;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def get_sql_agent(model_name: str, database: str) -> Optional[AISQLAgent]:
    """Caches the single AI SQL Agent instance per model and database."""
    try:
        return AISQLAgent(model_name=model_name, database=database)
    except Exception as e:
        st.error(f"Failed to initialize AI Agent: {e}")
        return None


# Session State Initialization
if "selected_db" not in st.session_state:
    st.session_state.selected_db = DEFAULT_DATABASE

if "selected_model" not in st.session_state:
    st.session_state.selected_model = DEFAULT_MODEL

if "messages" not in st.session_state:
    st.session_state.messages = []

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    # Logo & Branding
    logo_path = os.path.join(BASE_DIR, "assets", "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, width=56)
    st.title("AI SQL Assistant")
    st.caption("Single-Agent Multi-Database MySQL Assistant")

    st.divider()

    # 1. Dynamic Database Selection
    st.subheader("🗄️ Database Selection")
    accessible_dbs = get_available_databases(as_admin=False)
    if not accessible_dbs:
        accessible_dbs = [DEFAULT_DATABASE]

    # Ensure default or selected database is valid in options
    current_db_idx = (
        accessible_dbs.index(st.session_state.selected_db)
        if st.session_state.selected_db in accessible_dbs
        else 0
    )

    chosen_db = st.selectbox(
        "Active MySQL Database",
        options=accessible_dbs,
        index=current_db_idx,
        help="Select an authorized database to inspect its schema and execute queries.",
    )

    # Detect database switch -> Clear chat and schema context
    if chosen_db != st.session_state.selected_db:
        st.session_state.selected_db = chosen_db
        st.session_state.messages.clear()
        history_manager.clear()
        st.rerun()

    # Connection Status for Selected Database
    active_db = st.session_state.selected_db
    db_metrics = get_dashboard_metrics(db_name=active_db)

    if db_metrics["db_connected"]:
        st.markdown(
            f"""
            <span class="status-badge-success">● Connected</span><br>
            <small style="color:#64748B;">Database: <b class="db-tag">{active_db}</b><br>Mode: <b>Read-Only (sql_reader)</b></small>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <span class="status-badge-error">● Disconnected</span><br>
            <small style="color:#EF4444;">{db_metrics['error'] or 'Connection Failed'}</small>
            """,
            unsafe_allow_html=True,
        )

    # Show Available Tables in Selected Database
    available_tables = get_approved_table_names(db_name=active_db)
    with st.expander(f"📋 Tables in `{active_db}` ({len(available_tables)})", expanded=True):
        if available_tables:
            for tbl in available_tables:
                st.markdown(f"- `{tbl}`")
        else:
            st.caption("No accessible tables found in this database.")

    st.divider()

    # 2. LLM Model Configuration
    st.subheader("⚙️ Model Configuration")
    model_choice = st.selectbox(
        "Groq LLM Model",
        options=SUPPORTED_GROQ_MODELS,
        index=SUPPORTED_GROQ_MODELS.index(st.session_state.selected_model)
        if st.session_state.selected_model in SUPPORTED_GROQ_MODELS
        else 0,
        help="Select a supported Groq tool-calling model.",
    )
    st.session_state.selected_model = model_choice

    st.divider()

    # 3. Contextual Example Questions
    st.subheader("💡 Example Questions")
    if active_db == "ai_sql_assistant":
        sample_queries = [
            "Count all employees",
            "Show top 5 highest-paid employees",
            "Calculate average salary by department",
            "Find customers from Hyderabad",
            "Count orders by status",
            "Show monthly revenue for 2024",
            "Find employees without a department",
        ]
    elif active_db == "bike_store":
        sample_queries = [
            "Count total products by category",
            "Show top 5 most expensive products",
            "Count orders by store",
            "List all bike brands",
            "Find customers from New York or California",
        ]
    elif active_db == "employee":
        sample_queries = [
            "Show all department details",
            "Count employees in each department",
            "Find employee details with highest salary",
        ]
    else:
        sample_queries = [f"Count records in {tbl}" for tbl in available_tables[:4]]

    for sq in sample_queries:
        if st.button(sq, key=f"ex_{active_db}_{sq}", use_container_width=True):
            st.session_state.pending_prompt = sq
            st.rerun()

    st.divider()

    # 4. Query History
    st.subheader("📜 Recent Queries")
    history_records = history_manager.get_all()
    if history_records:
        for rec in history_records[:5]:
            with st.expander(f"Q: {rec['question'][:28]}..."):
                st.caption(f"Time: {rec['timestamp']} | Status: {rec['status']}")
                if rec["sql"]:
                    st.code(rec["sql"], language="sql")
                if rec["error"]:
                    st.caption(f"Error: {rec['error']}")
    else:
        st.caption("No queries executed in this session.")

    # 5. Clear Conversation Button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages.clear()
        history_manager.clear()
        st.rerun()


# ==========================================
# MAIN DASHBOARD METRICS
# ==========================================
st.title("AI SQL Query Assistant")
st.markdown(
    f"Query MySQL database <b class='db-tag'>{active_db}</b> using natural language. "
    "The AI agent dynamically retrieves table metadata, generates validated read-only SQL, "
    "executes the query safely, and presents data-grounded insights.",
    unsafe_allow_html=True,
)

col1, col2, col3, col4 = st.columns(4)
with col1:
    status_label = "Online" if db_metrics["db_connected"] else "Offline"
    st.metric("Database Status", status_label, help=f"Active database: {active_db}")
with col2:
    st.metric("Available Tables", f"{len(available_tables)} Tables", help=", ".join(available_tables))
with col3:
    if active_db == "ai_sql_assistant":
        st.metric("Total Employees", f"{db_metrics['total_employees']:,}")
    else:
        st.metric("Active Database", active_db)
with col4:
    exec_count = history_manager.get_total_count()
    st.metric("Queries Executed", str(exec_count), help="Total queries executed for active database")

st.divider()


# ==========================================
# CHAT INTERFACE
# ==========================================
# Display previous chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            if msg.get("success"):
                st.markdown(msg["explanation"])

                # Expandable SQL Viewer
                sql_title = (
                    f"🔍 Generated SQL Query ({msg.get('database', active_db)}) — "
                    f"{msg.get('row_count', 0)} rows in {msg.get('execution_time_sec', 0):.3f}s"
                )
                with st.expander(sql_title, expanded=False):
                    st.code(msg["sql"], language="sql")
                    if msg.get("correction_attempts", 0) > 0:
                        st.info(f"Self-corrected after {msg['correction_attempts']} attempt(s).")

                # Data Table
                df_data = msg.get("dataframe")
                if df_data is not None and not df_data.empty:
                    st.dataframe(df_data, use_container_width=True, hide_index=True)
                elif msg.get("row_count", 0) == 0:
                    st.info("Query executed successfully, but returned 0 records.")

                # Visualization if suitable
                if msg.get("chart") is not None:
                    st.plotly_chart(msg["chart"], use_container_width=True)

            else:
                st.error(msg["explanation"])
                if msg.get("sql"):
                    with st.expander("Attempted SQL Query", expanded=False):
                        st.code(msg["sql"], language="sql")
                if msg.get("error"):
                    st.caption(f"Technical Details: {msg['error']}")


# Handle User Input
input_placeholder = (
    f"Ask a question about database '{active_db}' (Tables: {', '.join(available_tables[:3])})..."
    if available_tables
    else f"Ask a question about database '{active_db}'..."
)
user_prompt = st.chat_input(input_placeholder)

if st.session_state.pending_prompt:
    user_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None

if user_prompt:
    # 1. Append and display user message
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # 2. Execute query via Single AI Agent targeting active database
    with st.chat_message("assistant"):
        with st.spinner(f"Analyzing question and querying database '{active_db}'..."):
            agent = get_sql_agent(
                model_name=st.session_state.selected_model,
                database=active_db,
            )
            if not agent:
                res = {
                    "success": False,
                    "sql": "",
                    "database": active_db,
                    "explanation": "Could not initialize AI Agent. Please verify your GROQ_API_KEY.",
                    "error": "Agent initialization failed.",
                    "dataframe": pd.DataFrame(),
                    "row_count": 0,
                    "execution_time_sec": 0.0,
                    "chart": None,
                }
            else:
                res = agent.process_query(user_prompt, db_name=active_db)

            # 3. Render Assistant Response
            if res.get("success"):
                st.markdown(res["explanation"])

                sql_title = (
                    f"🔍 Generated SQL Query ({active_db}) — "
                    f"{res.get('row_count', 0)} rows in {res.get('execution_time_sec', 0):.3f}s"
                )
                with st.expander(sql_title, expanded=False):
                    st.code(res["sql"], language="sql")
                    if res.get("correction_attempts", 0) > 0:
                        st.info(f"Self-corrected after {res['correction_attempts']} attempt(s).")

                df_data = res.get("dataframe")
                if df_data is not None and not df_data.empty:
                    st.dataframe(df_data, use_container_width=True, hide_index=True)
                elif res.get("row_count", 0) == 0:
                    st.info("Query returned 0 records.")

                if res.get("chart") is not None:
                    st.plotly_chart(res["chart"], use_container_width=True)

            else:
                st.error(res["explanation"])
                if res.get("sql"):
                    with st.expander("Attempted SQL Query", expanded=False):
                        st.code(res["sql"], language="sql")
                if res.get("error"):
                    st.caption(f"Technical Details: {res['error']}")

            # 4. Save to session state
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "success": res.get("success", False),
                    "sql": res.get("sql", ""),
                    "database": active_db,
                    "explanation": res.get("explanation", ""),
                    "dataframe": res.get("dataframe"),
                    "row_count": res.get("row_count", 0),
                    "execution_time_sec": res.get("execution_time_sec", 0.0),
                    "chart": res.get("chart"),
                    "error": res.get("error"),
                    "correction_attempts": res.get("correction_attempts", 0),
                }
            )
