import asyncio
import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'vnstock_data.db')
SECTORS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'sectors.json')

async def seed_sectors():
    print(f"Reading sectors from {SECTORS_PATH}...")
    with open(SECTORS_PATH, 'r', encoding='utf-8') as f:
        sectors_map = json.load(f)
    
    print(f"Updating database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    updated_count = 0
    for sector, symbols in sectors_map.items():
        print(f"  Processing {sector} ({len(symbols)} stocks)...")
        for symbol in symbols:
            # Update sector for this stock
            cursor.execute("UPDATE stocks SET sector = ? WHERE symbol = ?", (sector, symbol))
            if cursor.rowcount > 0:
                updated_count += 1
            else:
                # print(f"    Stock {symbol} not found in DB")
                pass
                
    conn.commit()
    conn.close()
    print(f"✅ Updated {updated_count} stocks with sector data")

if __name__ == '__main__':
    asyncio.run(seed_sectors())
