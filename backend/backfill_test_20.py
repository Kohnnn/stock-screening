
import asyncio
from database import Database
from vnstock import Vnstock
import pandas as pd

async def backfill_top_20():
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    # Get top 20 stocks (e.g. VN30 or randomly)
    async with db.connection() as conn:
        async with conn.execute("SELECT symbol FROM stocks LIMIT 20") as cursor:
            rows = await cursor.fetchall()
            symbols = [row[0] for row in rows]
            
    print(f"Backfilling {len(symbols)} stocks...")
    
    vn = Vnstock()
    updates = []
    
    for symbol in symbols:
        try:
            print(f"Fetching {symbol}...")
            stock = vn.stock(symbol=symbol, source='VCI')
            overview = stock.company.overview()
            
            if overview is not None and not overview.empty:
                row = overview.iloc[0]
                sector = row.get('icb_name2')
                if sector:
                    print(f"  -> Found sector: {sector}")
                    updates.append((sector, symbol))
                else:
                    print("  -> No sector found")
            else:
                print("  -> No overview data")
                
        except Exception as e:
            print(f"  -> Error: {e}")
            
    if updates:
        print(f"Updating {len(updates)} records in DB...")
        async with db.connection() as conn:
            await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
            await conn.commit()
        print("Done.")
    else:
        print("No updates found.")

if __name__ == "__main__":
    asyncio.run(backfill_top_20())
