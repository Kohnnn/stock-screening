
import asyncio
import sys
import os
import aiosqlite

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from vnstock_collector import VnStockCollector

async def main():
    print("--- Diagnostics ---")
    
    # 1. Check screener_metrics count
    db_path = "./backend/data/vnstock_data.db"
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM screener_metrics") as cursor:
            count = (await cursor.fetchone())[0]
            print(f"screener_metrics rows: {count}")

    # 2. Test Income Statement Fetch
    print("\nTesting collect_income_statement for HPG...")
    collector = VnStockCollector()
    try:
        data = await collector.collect_income_statement('HPG', period='year')
        if data:
            print(f"✅ HPG Income Statement ({len(data)} periods):")
            print(f"  Latest Revenue: {data[0].get('revenue')}")
        else:
            print("❌ HPG Income Statement returned empty.")
    except Exception as e:
        print(f"❌ Error fetching income statement: {e}")

if __name__ == "__main__":
    asyncio.run(main())
