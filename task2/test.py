import os
import pandas as pd

from app import BASE

DATA_DIR = os.path.join(BASE, "data") 
filename = 'combined_corpus.csv'
path = os.path.join(DATA_DIR, filename)

if not os.path.exists(path):
    print(f"❌ File not found: {path}")
else:
    print(f"✅ File found: {path}")
    df = pd.read_csv(path)
    print("\n📋 Columns in the CSV file:")
    print(df.columns.tolist())

    print(f"\n🔢 Number of rows: {len(df)}")
    print("\n🧪 Sample data:")
    print(df.head())