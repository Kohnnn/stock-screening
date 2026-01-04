
import asyncio
import sys
import os
import aiosqlite

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from vnstock_collector import VnStockCollector
from database import Database
from fireant_collector import FireAntCollector

async def main():
    print("--- Sync Test FireAnt ---")
    
    # 1. Setup DB
    db_path = "./backend/data/vnstock_data.db"
    if not os.path.exists(db_path):
        print(f"❌ DB not found: {db_path}")
        return
    
    db = Database(db_path)
    await db.initialize()
    
    # 2. Setup Collector
    fireant = FireAntCollector(db)
    print(f"Collector Source: {fireant.collector.default_source}")
    
    # 3. Test ONE stock manually logic
    symbol = 'HPG'
    print(f"Fetching Income Statement for {symbol}...")
    
    income_stmts = await fireant.collector.collect_income_statement(symbol, period='year', limit=2)
    
    if not income_stmts:
        print("❌ No income statements returned.")
    else:
        print(f"✅ Got {len(income_stmts)} statements.")
        latest = income_stmts[0]
        print(f"Latest Year: {latest.get('period')}")
        print(f"Revenue: {latest.get('revenue')}")
        print(f"Gross Profit: {latest.get('gross_profit')}")
        print(f"Net Profit: {latest.get('net_profit')}")
        
        # Calculate manually
        revenue = latest.get('revenue', 0) or 0
        gross_profit = latest.get('gross_profit', 0) or 0
        net_profit = latest.get('net_profit', 0) or 0
        
        updates = {}
        if revenue and revenue != 0:
            updates['gross_margin'] = (gross_profit / revenue) * 100
            updates['net_margin'] = (net_profit / revenue) * 100
            print(f"Calculated GM: {updates['gross_margin']}%")
            print(f"Calculated NM: {updates['net_margin']}%")
            
            # Try Single DB Update
            print("Attempting single DB update...")
            async with db.connection() as conn:
                keys = list(updates.keys())
                placeholders = ["?"] * len(keys)
                query = f"""
                    INSERT INTO screener_metrics (symbol, updated_at, {', '.join(keys)})
                    VALUES (?, datetime('now'), {', '.join(placeholders)})
                    ON CONFLICT(symbol) DO UPDATE SET
                        updated_at = excluded.updated_at,
                        {', '.join([f"{k} = excluded.{k}" for k in keys])}
                """
                query_values = [symbol] + list(updates.values())
                await conn.execute(query, query_values)
                await conn.commit()
            print("✅ DB Update executed.")
        else:
            print("❌ Revenue is 0/None")
            
    # DEBUG: Check RAW columns
    print("\n--- RAW DATAFRAME COLUMNS (VCI) ---")
    try:
        from vnstock import Vnstock
        stock = Vnstock().stock(symbol='HPG', source='VCI')
        df = stock.finance.income_statement(period='year', lang='vi')
        if df is not None:
             cols = list(df.columns)
             print("Columns:", cols)
             # Print first row details
             row = df.iloc[0].to_dict()
             print("\nSample Row Data:")
             for k, v in row.items():
                 print(f"  {k}: {v}")
    except Exception as e:
        print(f"Error fetching raw: {e}")

if __name__ == "__main__":
    asyncio.run(main())
