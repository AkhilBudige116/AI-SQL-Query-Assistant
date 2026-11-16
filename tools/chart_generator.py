"""
Chart Generation Tool for AI SQL Query Assistant.
Uses Plotly Express to generate interactive visualizations:
- Bar Charts (for categorical comparisons and rankings)
- Line Charts (for time series and trend analysis)
- Pie Charts (for composition and distribution)
Intelligently determines suitability based on data structure and user intent.
"""

from typing import Optional, Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def detect_chart_suitability(df: pd.DataFrame, user_question: str = "") -> Optional[Dict[str, Any]]:
    """
    Inspects DataFrame columns and rows to detect if a chart is appropriate.
    Returns chart configuration metadata or None if data is not chart-suitable.
    """
    if df is None or df.empty or len(df) < 2:
        return None

    # Identify numeric and categorical columns
    numeric_cols = []
    date_cols = []
    categorical_cols = []

    for col in df.columns:
        col_lower = col.lower()
        # Check for date columns
        if "date" in col_lower or "month" in col_lower or "year" in col_lower or pd.api.types.is_datetime64_any_dtype(df[col]):
            date_cols.append(col)
        elif pd.api.types.is_numeric_dtype(df[col]):
            # Ignore auto-increment ID columns for plotting values
            if col_lower.endswith("_id") and not any(k in col_lower for k in ["count", "total"]):
                continue
            numeric_cols.append(col)
        else:
            categorical_cols.append(col)

    if not numeric_cols:
        return None

    q_lower = user_question.lower() if user_question else ""

    # User explicitly asked for pie chart or distribution
    if any(k in q_lower for k in ["pie", "proportion", "percentage", "distribution", "share"]) and categorical_cols:
        cat_col = categorical_cols[0]
        val_col = numeric_cols[0]
        if df[cat_col].nunique() <= 10:
            return {
                "chart_type": "pie",
                "names": cat_col,
                "values": val_col,
                "title": f"Distribution of {val_col} by {cat_col}",
            }

    # Time series / trend query
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        val_col = numeric_cols[0]
        # Line chart for chronological trends
        return {
            "chart_type": "line",
            "x": date_col,
            "y": val_col,
            "title": f"Trend of {val_col} over {date_col}",
        }

    # Categorical comparison -> Bar chart
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        val_col = numeric_cols[0]
        return {
            "chart_type": "bar",
            "x": cat_col,
            "y": val_col,
            "title": f"{val_col} by {cat_col}",
        }

    # If only numeric columns exist (e.g., histogram or 2 numeric columns)
    if len(numeric_cols) >= 2:
        return {
            "chart_type": "bar",
            "x": numeric_cols[0],
            "y": numeric_cols[1],
            "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
        }

    return None


def generate_chart(df: pd.DataFrame, chart_config: Dict[str, Any]) -> Optional[go.Figure]:
    """
    Renders a Plotly figure using the specified chart configuration.
    Applies clean modern styling matching the application theme.
    """
    if df is None or df.empty or not chart_config:
        return None

    chart_type = chart_config.get("chart_type", "bar")
    title = chart_config.get("title", "Query Result Visualization")

    try:
        if chart_type == "bar":
            x_col = chart_config["x"]
            y_col = chart_config["y"]
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                title=title,
                text_auto=True,
                color_discrete_sequence=["#2563EB"],  # Professional blue
            )
            fig.update_layout(
                xaxis_title=x_col.replace("_", " ").title(),
                yaxis_title=y_col.replace("_", " ").title(),
                template="plotly_white",
                margin=dict(l=40, r=40, t=50, b=40),
            )
            return fig

        elif chart_type == "line":
            x_col = chart_config["x"]
            y_col = chart_config["y"]
            fig = px.line(
                df,
                x=x_col,
                y=y_col,
                title=title,
                markers=True,
                color_discrete_sequence=["#10B981"],  # Emerald green
            )
            fig.update_layout(
                xaxis_title=x_col.replace("_", " ").title(),
                yaxis_title=y_col.replace("_", " ").title(),
                template="plotly_white",
                margin=dict(l=40, r=40, t=50, b=40),
            )
            return fig

        elif chart_type == "pie":
            names_col = chart_config["names"]
            values_col = chart_config["values"]
            fig = px.pie(
                df,
                names=names_col,
                values=values_col,
                title=title,
                hole=0.3,  # Modern donut style
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            fig.update_layout(
                template="plotly_white",
                margin=dict(l=40, r=40, t=50, b=40),
            )
            return fig

    except Exception as e:
        print(f"Chart generation error: {e}")
        return None

    return None


def create_visual_if_suitable(df: pd.DataFrame, user_question: str = "") -> Optional[go.Figure]:
    """
    One-step helper: checks suitability and returns a Plotly figure if appropriate.
    """
    config = detect_chart_suitability(df, user_question)
    if config:
        return generate_chart(df, config)
    return None
