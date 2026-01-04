import asyncio
from vnstock_collector import get_collector

async def test_integration():
    print("Testing VnStockCollector -> CafeF Integration...")
    collector = await get_collector()
    
    symbol = "VNM"
    print(f"Fetching financials for {symbol}...")
    
    data = await collector.collect_financials_from_cafef(symbol)
    
    print("\n✅ Result:")
    for k, v in data.items():
        print(f"  {k}: {v}")

    # Check mapping
    if data.get('revenue'):
        print("\n🎉 Revenue found! Integration successful.")
    else:
        print("\n❌ Revenue missing.")

if __name__ == "__main__":
    asyncio.run(test_integration())
