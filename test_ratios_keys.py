
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from vnstock_collector import VnStockCollector
from config import settings

async def main():
    print("Testing VnStockCollector Screener Data (TCBS 84 metrics)...")
    collector = VnStockCollector()
    
    try:
        # Test collect_screener_full
        print("Calling collect_screener_full (limit 50)...")
        # Modify the method header in verification or just trust it defaults to 2000? 
        # The method in file creates a new vnstock instance.
        
        data = await collector.collect_screener_full()
        
        if data:
            print(f"\n✅ Got {len(data)} screener records.")
            # Find HPG or just take first
            sample = next((x for x in data if x.get('symbol') == 'HPG'), data[0])
            
            print(f"\nKeys in sample record ({sample.get('symbol')}):")
            for k in sorted(sample.keys()):
                print(f"  - {k}: {sample[k]}")
                
            # Check for keys mapped in database
            # screener_metrics table columns: gross_margin, net_margin, revenue_growth_1y
            # TCBS usually returns camelCase: grossMargin, netMargin, revenueGrowth1Year (or similar)
            expected_map = {
                'gross_margin': ['grossMargin', 'gross_margin'],
                'net_margin': ['netMargin', 'net_margin', 'netProfitMargin'],
                'revenue_growth_1y': ['revenueGrowth1Year', 'revenueGrowth']
            }
            
            print("\nChecking for mappable keys:")
            for db_col, candidates in expected_map.items():
                found = False
                for c in candidates:
                    if c in sample:
                        print(f"  [MATCH] {db_col} -> {c}: {sample[c]}")
                        found = True
                        break
                if not found:
                     print(f"  [MISSING] {db_col}")
        else:
            print("❌ No screener data returned.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
