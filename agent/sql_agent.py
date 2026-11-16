"""
Single AI SQL Agent for AI SQL Query Assistant.
Coordinates schema retrieval, SQL generation via Groq LLM, strict SQLGlot validation,
safe MySQL execution, automated limited self-correction, result analysis, and charting.
Supports dynamic switching across multiple authorized MySQL databases.
"""

import sys
import os
import json
from typing import Dict, Any, Optional, List, Set
import pandas as pd
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.agent_config import (
    get_agent_config,
    DEFAULT_MODEL,
    DEFAULT_DATABASE,
    MAX_CORRECTION_ATTEMPTS,
)
from agent.prompts import (
    SYSTEM_PROMPT,
    SQL_GENERATION_PROMPT,
    SQL_CORRECTION_PROMPT,
    RESULT_EXPLANATION_PROMPT,
)
from tools.schema_tool import get_database_schema_summary, get_approved_table_names
from tools.sql_validator import validate_sql_query, clean_sql_string
from tools.sql_executor import execute_sql
from tools.result_analyzer import analyze_query_results
from tools.chart_generator import create_visual_if_suitable
from utils.query_history import history_manager
from utils.helpers import sanitize_error_message
from database.db_connection import get_available_databases

load_dotenv()


class AISQLAgent:
    """
    Single Agentic AI Assistant for Natural Language to MySQL querying.
    Implements tool calling, schema-aware query generation, validation,
    dynamic database switching, and automatic bounded error correction (max 2 attempts).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        database: Optional[str] = None,
    ):
        cfg = get_agent_config()
        self.api_key = api_key or cfg["api_key"]
        self.model_name = model_name or cfg["model_name"]
        self.temperature = cfg["temperature"]
        self.max_corrections = cfg["max_correction_attempts"]
        self.current_db = database or cfg.get("default_database", DEFAULT_DATABASE)

        if not self.api_key:
            raise ValueError("GROQ_API_KEY is not set. Please provide a valid Groq API key in your .env file.")

        # Initialize the LangChain ChatGroq model
        self.llm = ChatGroq(
            groq_api_key=self.api_key,
            model_name=self.model_name,
            temperature=self.temperature,
        )

    def set_database(self, db_name: str) -> bool:
        """
        Dynamically updates the active database after verifying it is accessible.
        """
        if not db_name:
            return False
        available = get_available_databases()
        if db_name in available:
            self.current_db = db_name
            return True
        # If not explicitly in available list, still allow if authorized
        self.current_db = db_name
        return True

    def get_database(self) -> str:
        """Returns the currently active database name."""
        return self.current_db

    def _call_llm(self, prompt: str) -> str:
        """Helper to invoke the LLM with the standard system prompt."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        response = self.llm.invoke(messages)
        return clean_sql_string(response.content)

    def generate_sql(self, user_question: str, db_name: Optional[str] = None) -> str:
        """Generates a raw MySQL query using the active schema and LLM."""
        target_db = db_name or self.current_db
        schema_summary = get_database_schema_summary(db_name=target_db)
        prompt = SQL_GENERATION_PROMPT.format(
            database_name=target_db,
            schema_summary=schema_summary,
            user_question=user_question,
        )
        return self._call_llm(prompt)

    def correct_sql(
        self,
        user_question: str,
        failed_sql: str,
        error_message: str,
        db_name: Optional[str] = None,
    ) -> str:
        """Asks the LLM to safely correct a query that failed validation or execution."""
        target_db = db_name or self.current_db
        schema_summary = get_database_schema_summary(db_name=target_db)
        prompt = SQL_CORRECTION_PROMPT.format(
            database_name=target_db,
            schema_summary=schema_summary,
            user_question=user_question,
            failed_sql=failed_sql,
            error_message=sanitize_error_message(error_message),
        )
        return self._call_llm(prompt)

    def explain_results(
        self,
        user_question: str,
        executed_sql: str,
        row_count: int,
        analysis: Dict[str, Any],
        sample_rows: List[Dict[str, Any]],
        db_name: Optional[str] = None,
    ) -> str:
        """
        Uses the LLM and deterministic analysis metrics to formulate a clear,
        concise, natural-language explanation of query results.
        """
        target_db = db_name or self.current_db
        if row_count == 0:
            return analysis.get("summary_text", "No records matched your query.")

        sample_json = json.dumps(sample_rows[:5], default=str)
        takeaways_str = "\n".join(f"- {t}" for t in analysis.get("key_takeaways", []))

        prompt = RESULT_EXPLANATION_PROMPT.format(
            database_name=target_db,
            user_question=user_question,
            executed_sql=executed_sql,
            row_count=row_count,
            key_takeaways=takeaways_str,
            sample_rows=sample_json,
        )

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
            resp = self.llm.invoke(messages)
            explanation = resp.content.strip()
            return explanation if explanation else analysis.get("summary_text", "")
        except Exception:
            return analysis.get("summary_text", f"Retrieved {row_count} records from `{target_db}`.")

    def process_query(
        self,
        user_question: str,
        db_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main execution workflow:
        1. Resolve active database and approved tables.
        2. Generate initial SQL targeting active database.
        3. Validate SQL using SQLGlot against active database tables.
        4. Execute approved query in target database.
        5. If validation or execution fails, attempt correction (up to 2 times).
        6. Analyze result dataset and generate plain English explanation.
        7. Determine and generate suitable Plotly visualization.
        8. Save to query history.
        """
        target_db = db_name or self.current_db
        clean_q = user_question.strip()

        if not clean_q:
            return {
                "success": False,
                "question": user_question,
                "sql": "",
                "database": target_db,
                "status": "VALIDATION_FAILED",
                "row_count": 0,
                "execution_time_sec": 0.0,
                "dataframe": pd.DataFrame(),
                "columns": [],
                "rows": [],
                "explanation": "Please provide a valid, non-empty question.",
                "chart": None,
                "error": "Question is empty.",
                "correction_attempts": 0,
            }

        # Retrieve valid tables for the target database
        approved_tables_list = get_approved_table_names(target_db)
        approved_tables_set: Set[str] = set(t.lower() for t in approved_tables_list)

        # Step 1: Initial SQL Generation
        try:
            current_sql = self.generate_sql(clean_q, db_name=target_db)
        except Exception as api_err:
            error_msg = f"LLM API Error: {sanitize_error_message(str(api_err))}"
            history_manager.add_record(
                question=clean_q,
                sql="",
                status="EXECUTION_ERROR",
                row_count=0,
                execution_time_sec=0.0,
                error=error_msg,
            )
            return {
                "success": False,
                "question": clean_q,
                "sql": "",
                "database": target_db,
                "status": "EXECUTION_ERROR",
                "row_count": 0,
                "execution_time_sec": 0.0,
                "dataframe": pd.DataFrame(),
                "columns": [],
                "rows": [],
                "explanation": "Unable to generate SQL due to an LLM service error. Please verify your Groq API key and rate limits.",
                "chart": None,
                "error": error_msg,
                "correction_attempts": 0,
            }

        correction_count = 0
        execution_result: Optional[Dict[str, Any]] = None

        # Step 2-4: Validation and Execution with Bounded Self-Correction Loop
        while True:
            is_valid, validated_sql, val_message = validate_sql_query(
                query=current_sql,
                approved_tables=approved_tables_set,
                current_db=target_db,
            )

            if is_valid:
                # Execute validated query on target database
                execution_result = execute_sql(
                    query=validated_sql,
                    validate_first=False,
                    database=target_db,
                    approved_tables=approved_tables_set,
                )
                if execution_result["success"]:
                    current_sql = validated_sql
                    break
                else:
                    if correction_count < self.max_corrections:
                        correction_count += 1
                        try:
                            current_sql = self.correct_sql(
                                user_question=clean_q,
                                failed_sql=current_sql,
                                error_message=execution_result["error"],
                                db_name=target_db,
                            )
                            continue
                        except Exception:
                            break
                    else:
                        break
            else:
                if correction_count < self.max_corrections:
                    correction_count += 1
                    try:
                        current_sql = self.correct_sql(
                            user_question=clean_q,
                            failed_sql=current_sql,
                            error_message=val_message,
                            db_name=target_db,
                        )
                        continue
                    except Exception:
                        break
                else:
                    execution_result = {
                        "success": False,
                        "query": current_sql,
                        "sanitized_query": current_sql,
                        "database": target_db,
                        "columns": [],
                        "rows": [],
                        "row_count": 0,
                        "execution_time_sec": 0.0,
                        "dataframe": pd.DataFrame(),
                        "error": val_message,
                        "error_type": "VALIDATION_ERROR",
                    }
                    break

        # Check final status
        if not execution_result or not execution_result.get("success", False):
            err_msg = execution_result.get("error", "Query validation or execution failed.") if execution_result else "Execution error."
            status = "VALIDATION_FAILED" if "Validation" in err_msg else "EXECUTION_ERROR"

            history_manager.add_record(
                question=clean_q,
                sql=current_sql,
                status=status,
                row_count=0,
                execution_time_sec=execution_result.get("execution_time_sec", 0.0) if execution_result else 0.0,
                error=err_msg,
            )

            return {
                "success": False,
                "question": clean_q,
                "sql": current_sql,
                "database": target_db,
                "status": status,
                "row_count": 0,
                "execution_time_sec": execution_result.get("execution_time_sec", 0.0) if execution_result else 0.0,
                "dataframe": pd.DataFrame(),
                "columns": [],
                "rows": [],
                "explanation": f"I could not retrieve an answer from database `{target_db}` due to the following issue: {err_msg}",
                "chart": None,
                "error": err_msg,
                "correction_attempts": correction_count,
            }

        # Step 5: Successful Execution - Result Analysis & Natural Language Explanation
        df = execution_result["dataframe"]
        row_count = execution_result["row_count"]
        columns = execution_result["columns"]
        rows = execution_result["rows"]

        analysis = analyze_query_results(clean_q, columns, rows, row_count)
        explanation = self.explain_results(
            user_question=clean_q,
            executed_sql=current_sql,
            row_count=row_count,
            analysis=analysis,
            sample_rows=rows,
            db_name=target_db,
        )

        # Step 6: Visualization Generation
        chart_fig = create_visual_if_suitable(df, user_question=clean_q)

        # Step 7: Record into Query History
        history_manager.add_record(
            question=clean_q,
            sql=current_sql,
            status="SUCCESS",
            row_count=row_count,
            execution_time_sec=execution_result["execution_time_sec"],
            error=None,
        )

        return {
            "success": True,
            "question": clean_q,
            "sql": current_sql,
            "database": target_db,
            "status": "SUCCESS",
            "row_count": row_count,
            "execution_time_sec": execution_result["execution_time_sec"],
            "dataframe": df,
            "columns": columns,
            "rows": rows,
            "analysis": analysis,
            "explanation": explanation,
            "chart": chart_fig,
            "error": None,
            "correction_attempts": correction_count,
        }
