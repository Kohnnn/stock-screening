
import sqlite3
import os

db_path = r'c:\Users\Admin\Desktop\PersonalWebsite\stockscreen\vnstock-screener\backend\data\vnstock_data.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
    exit(1)

con = sqlite3.connect(db_path)
cursor = con.cursor()
tables = ['stocks', 'stock_prices', 'stock_metrics', 'financial_metrics', 'market_indices', 'screener_metrics']
print("Database Check Results:")
for t in tables:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {t}")
        count = cursor.fetchone()[0]
        print(f"{t}: {count}")
    except Exception as e:
        print(f"{t}: Error {e}")

try:
    cursor.execute("SELECT COUNT(*) FROM stocks WHERE sector IS NOT NULL AND sector != ''")
    sector_count = cursor.fetchone()[0]
    print(f"stocks with sector: {sector_count}")
except Exception as e:
    print(f"stocks with sector: Error {e}")

con.close()
