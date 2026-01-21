import pandas as pd
import os

# Get the directory where data.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
excel_path = os.path.join(current_dir, "BOT AI.xlsx")

try:
    inventory_df = pd.read_excel(excel_path)
    # Ensure all columns are converted to string to avoid issues in the prompt
    inventory_df = inventory_df.astype(str)
except Exception as e:
    print(f"Error reading Excel file: {e}")
    # Fallback empty DF if file missing
    inventory_df = pd.DataFrame()

# Warehouse and Online Prices are no longer relevant for this dataset, 
# but keeping empty DFs to prevent import errors if they are referenced elsewhere temporarily.
warehouse_df = pd.DataFrame()
online_prices_df = pd.DataFrame()
