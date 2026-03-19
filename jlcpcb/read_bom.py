import pandas as pd
import sys

try:
    df = pd.read_excel('bom.xls')
    print("Columns:", df.columns.tolist())
    print("\nFirst 3 rows:")
    print(df.head(3).to_dict(orient='records'))
except Exception as e:
    print("Error:", e)
