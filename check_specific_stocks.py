
import asyncio
import sys
import os
import aiosqlite

async def main():
    db_path = "./backend/data/vnstock_data.db"
    
    symbols = ['HPG', 'VCB']
    print(f"Checking metrics for {symbols}...")
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        for sym in symbols:
            cursor = await db.execute("SELECT * FROM screener_metrics WHERE symbol = ?", (sym,))
            row = await cursor.fetchone()
            
            if row:
                print(f"\n[{sym}]")
                print(f"  Gross Margin: {row['gross_margin']}")
                print(f"  Net Margin: {row['net_margin']}")
                print(f"  Rev Growth: {row['revenue_growth_1y']}")
                print(f"  Updated At: {row['updated_at']}")
            else:
                print(f"\n[{sym}] ❌ No screener_metrics record found.")

if __name__ == "__main__":
    asyncio.run(main())
