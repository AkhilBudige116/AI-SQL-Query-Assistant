"""
Agent Configuration for AI SQL Query Assistant.
Stores configurable parameters, LLM model choices, and agent runtime constraints.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Active Groq models that support tool calling and SQL generation
SUPPORTED_GROQ_MODELS: List[str] = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

DEFAULT_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
DEFAULT_DATABASE: str = os.getenv("MYSQL_DATABASE", "ai_sql_assistant")
DEFAULT_TEMPERATURE: float = 0.0
MAX_CORRECTION_ATTEMPTS: int = 2
DEFAULT_ROW_LIMIT: int = 100
MAX_ROW_LIMIT: int = 1000


def get_agent_config() -> dict:
    """Returns the current runtime agent configuration."""
    api_key = os.getenv("GROQ_API_KEY", "")
    model_name = os.getenv("GROQ_MODEL", DEFAULT_MODEL)
    if model_name not in SUPPORTED_GROQ_MODELS and not model_name:
        model_name = SUPPORTED_GROQ_MODELS[0]

    return {
        "api_key": api_key,
        "model_name": model_name,
        "default_database": DEFAULT_DATABASE,
        "temperature": DEFAULT_TEMPERATURE,
        "max_correction_attempts": MAX_CORRECTION_ATTEMPTS,
        "default_row_limit": DEFAULT_ROW_LIMIT,
        "max_row_limit": MAX_ROW_LIMIT,
        "supported_models": SUPPORTED_GROQ_MODELS,
    }
