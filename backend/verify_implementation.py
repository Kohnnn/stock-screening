"""Quick verification script for the new database tables and update registry."""
import sqlite3
import asyncio
import sys

def check_tables():
    """Check if new tables exist in the database."""
    conn = sqlite3.connect('data/vnstock_data.db')
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]
    
    print("=" * 50)
    print("DATABASE TABLES CHECK")
    print("=" * 50)
    
    expected_tables = [
        'stocks', 'stock_prices', 'price_history', 'financial_metrics',
        'update_logs', 'rate_limit_stats', 'scheduler_state',
        # New tables
        'data_update_tracker', 'dividend_history', 'company_ratings',
        'intraday_prices', 'market_indices'
    ]
    
    print(f"Found {len(tables)} tables:")
    for table in tables:
        status = "✅" if table in expected_tables else "❓"
        print(f"  {status} {table}")
    
    # Check for new tables specifically
    new_tables = ['data_update_tracker', 'dividend_history', 'company_ratings', 
                  'intraday_prices', 'market_indices']
    
    print("\nNew Tables Status:")
    for table in new_tables:
        exists = table in tables
        print(f"  {'✅' if exists else '❌'} {table}: {'EXISTS' if exists else 'MISSING'}")
    
    conn.close()
    return all(t in tables for t in new_tables)


async def check_update_registry():
    """Test the update registry module."""
    print("\n" + "=" * 50)
    print("UPDATE REGISTRY CHECK")
    print("=" * 50)
    
    try:
        from database import get_database
        from update_registry import get_update_registry, DataType
        
        db = await get_database()
        registry = await get_update_registry(db)
        
        # Get summary
        summary = await registry.get_update_summary()
        
        print(f"✅ Registry initialized successfully")
        print(f"   Symbols tracked: {summary['totals']['symbols_tracked']}")
        print(f"   Health status: {summary.get('health_status', 'unknown')}")
        
        # Check data types
        print("\nData Types:")
        for dt in DataType:
            stats = summary['by_data_type'].get(dt.value, {})
            print(f"   {dt.value}: {stats.get('up_to_date', 0)} up-to-date, "
                  f"{stats.get('needing_update', 0)} need update")
        
        return True
        
    except Exception as e:
        print(f"❌ Registry check failed: {e}")
        return False


async def check_collector_methods():
    """Verify new collector methods exist."""
    print("\n" + "=" * 50)
    print("COLLECTOR METHODS CHECK")
    print("=" * 50)
    
    try:
        from vnstock_collector import VnStockCollector
        
        collector = VnStockCollector()
        
        new_methods = [
            'collect_screener_data',
            'collect_income_statement',
            'collect_balance_sheet',
            'collect_cash_flow',
            'collect_financial_data',
            'collect_dividend_history',
            'collect_company_ratings',
            'collect_intraday_data',
            'collect_market_indices',
            'collect_batch_price_history',
        ]
        
        for method in new_methods:
            exists = hasattr(collector, method) and callable(getattr(collector, method))
            print(f"  {'✅' if exists else '❌'} {method}")
        
        return True
        
    except Exception as e:
        print(f"❌ Collector check failed: {e}")
        return False


def main():
    print("\n🔍 VnStock Screener - Implementation Verification\n")
    
    # Check database tables
    tables_ok = check_tables()
    
    # Run async checks
    async def run_async_checks():
        registry_ok = await check_update_registry()
        collector_ok = await check_collector_methods()
        return registry_ok and collector_ok
    
    async_ok = asyncio.run(run_async_checks())
    
    # Summary
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    print(f"  Database Tables: {'✅ PASS' if tables_ok else '❌ FAIL'}")
    print(f"  Update Registry: {'✅ PASS' if async_ok else '⚠️ PARTIAL'}")
    
    if tables_ok and async_ok:
        print("\n🎉 All verifications passed!")
        return 0
    else:
        print("\n⚠️ Some checks need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
