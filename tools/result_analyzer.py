"""
Result Analysis Tool for AI SQL Query Assistant.
Analyzes SQL execution results, computes summary metrics, and generates
grounded, natural-language explanations based strictly on actual query results.
"""

from typing import Dict, Any, List, Optional
import pandas as pd


def analyze_query_results(
    question: str,
    columns: List[str],
    rows: List[Dict[str, Any]],
    row_count: int,
) -> Dict[str, Any]:
    """
    Produces deterministic analysis and insights from the SQL query results.
    Does not hallucinate or extrapolate beyond the returned dataset.
    """
    if row_count == 0 or not rows:
        return {
            "has_data": False,
            "summary_text": "The query executed successfully, but returned no matching records in the database.",
            "metrics": {},
            "key_takeaways": ["No records found matching the query criteria."]
        }

    df = pd.DataFrame(rows)
    metrics: Dict[str, Any] = {
        "total_rows": row_count,
        "column_count": len(columns),
        "columns": columns,
    }

    key_takeaways: List[str] = []

    # Single-value queries (e.g., SELECT COUNT(*), SELECT MAX(salary))
    if row_count == 1 and len(columns) == 1:
        col = columns[0]
        val = rows[0][col]
        # Format if numeric
        if isinstance(val, (int, float)):
            val_str = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
        else:
            val_str = str(val)
        summary = f"The result for '{question}' is **{val_str}** (from column `{col}`)."
        key_takeaways.append(f"Value: {val_str}")
        return {
            "has_data": True,
            "summary_text": summary,
            "metrics": metrics,
            "key_takeaways": key_takeaways,
        }

    # Identify numeric columns for aggregated metrics
    numeric_cols = [c for c in columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical_cols = [c for c in columns if c not in numeric_cols]

    for num_col in numeric_cols:
        col_series = pd.to_numeric(df[num_col], errors="coerce").dropna()
        if not col_series.empty:
            metrics[f"{num_col}_avg"] = round(float(col_series.mean()), 2)
            metrics[f"{num_col}_max"] = float(col_series.max())
            metrics[f"{num_col}_min"] = float(col_series.min())
            metrics[f"{num_col}_sum"] = round(float(col_series.sum()), 2)

    # Generate grounded takeaway points
    if row_count == 1:
        row_details = ", ".join([f"{c}: {rows[0][c]}" for c in columns[:4]])
        key_takeaways.append(f"Retrieved 1 record: {row_details}.")
    else:
        key_takeaways.append(f"Retrieved {row_count} total records across {len(columns)} attributes.")

        # If there's a primary numeric column and a categorical column, identify top and bottom
        if numeric_cols and categorical_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            try:
                sorted_df = df.sort_values(by=num_col, ascending=False)
                top_item = sorted_df.iloc[0]
                bottom_item = sorted_df.iloc[-1]
                key_takeaways.append(
                    f"Highest {num_col}: '{top_item[cat_col]}' ({top_item[num_col]:,})."
                )
                if row_count > 1:
                    key_takeaways.append(
                        f"Lowest {num_col}: '{bottom_item[cat_col]}' ({bottom_item[num_col]:,})."
                    )
            except Exception:
                pass

    summary = f"Found {row_count} record(s). " + " ".join(key_takeaways)

    return {
        "has_data": True,
        "summary_text": summary,
        "metrics": metrics,
        "key_takeaways": key_takeaways,
    }


if __name__ == "__main__":
    sample_rows = [
        {"department_name": "Engineering", "avg_salary": 115000.50},
        {"department_name": "Data Science", "avg_salary": 112000.00},
        {"department_name": "Human Resources", "avg_salary": 65000.00},
    ]
    analysis = analyze_query_results("What is average salary by department?", ["department_name", "avg_salary"], sample_rows, len(sample_rows))
    print("Summary:", analysis["summary_text"])
    print("Takeaways:", analysis["key_takeaways"])
