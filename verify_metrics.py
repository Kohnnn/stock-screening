
import asyncio
import sys
import os
import aiosqlite

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

async def main():
    db_path = "./backend/data/vnstock_data.db"
    
    print(f"Checking screener_metrics in {db_path}...")
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return

    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        # Check columns of interest for a few stocks
        query = """
            SELECT symbol, gross_margin, net_margin, revenue_growth_1y 
            FROM screener_metrics 
            WHERE gross_margin IS NOT NULL 
            LIMIT 5
        """
        
        try:
            cursor = await db.execute(query)
            rows = await cursor.fetchall()
            
            if rows:
                print(f"✅ Found {len(rows)} updated records:")
                for row in rows:
                    print(f"  {row['symbol']}: GM={row['gross_margin']:.2f}%, NM={row['net_margin']:.2f}%, Growth={row['revenue_growth_1y']:.2f}%")
            else:
                print("❌ No records found with calculated margins.")
                
            # Count total updated
            count_query = "SELECT COUNT(*) as count FROM screener_metrics WHERE gross_margin IS NOT NULL"
            cursor = await db.execute(count_query)
            count = (await cursor.fetchone())['count']
            print(f"\nTotal stocks with Gross Margin: {count}")
            
        except Exception as e:
            print(f"❌ Error querying database: {e}")

if __name__ == "__main__":
    asyncio.run(main())
