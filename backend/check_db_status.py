
import sqlite3
con = sqlite3.connect(r'c:/Users/Admin/Desktop/PersonalWebsite/stockscreen/vnstock-screener/backend/data/vnstock_data.db')
cursor = con.cursor()
print('Total stocks:', cursor.execute('SELECT COUNT(*) FROM stocks').fetchone()[0])
print('Sectors populated:', cursor.execute("SELECT COUNT(*) FROM stocks WHERE sector IS NOT NULL AND sector != ''").fetchone()[0])
print('Market indices:')
for row in cursor.execute('SELECT * FROM market_indices').fetchall():
    print(row)
