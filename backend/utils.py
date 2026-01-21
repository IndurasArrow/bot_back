import pandas as pd

def df_to_context(df: pd.DataFrame, title: str) -> str:
    """
    Converts a DataFrame to a CSV string for token-efficient LLM context.
    """
    if df.empty:
        return f"{title}: No data available."
    
    csv_data = df.to_csv(index=False)
    return f"{title} (CSV format):\n{csv_data}"