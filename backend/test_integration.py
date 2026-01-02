"""Test new vnstock integration features."""
import sqlite3
import asyncio
from pathlib import Path

def test_tables():
    """Check that new tables exist."""
    db_path = Path(__file__).parent / "data" / "vnstock_data.db"
    
    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cursor.fetchall()]
    
    print("📋 Existing tables:")
    for t in tables:
        print(f"  - {t}")
    
    required_tables = ['screener_metrics', 'shareholders', 'officers', 'price_board']
    missing = [t for t in required_tables if t not in tables]
    
    if missing:
        print(f"\n⚠️ Missing tables: {missing}")
        print("Running schema to create them...")
        
        schema_path = Path(__file__).parent / "database_schema.sql"
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()
            print("✅ Schema applied!")
            
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cursor.fetchall()]
            print("\n📋 Tables after schema update:")
            for t in tables:
                print(f"  - {t}")
        return False
    
    print("\n✅ All required tables exist!")
    conn.close()
    return True


async def test_screener():
    """Test Screener API import and basic call."""
    try:
        from vnstock import Screener
        print("\n📊 Testing Screener API...")
        
        screener = Screener()
        df = screener.stock(params={"exchangeName": "HOSE"}, limit=5)
        
        print(f"✅ Screener works! Got {len(df)} stocks with {len(df.columns)} columns")
        print(f"   Columns: {list(df.columns[:10])}...")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Screener test error: {e}")
        return False


async def test_collector():
    """Test VnStockCollector new methods."""
    try:
        from vnstock_collector import VnStockCollector
        print("\n🔧 Testing VnStockCollector...")
        
        collector = VnStockCollector()
        
        # Check new methods exist
        methods = ['collect_screener_full', 'collect_shareholders', 
                   'collect_officers', 'collect_price_board', 'collect_industries']
        
        for method in methods:
            if hasattr(collector, method):
                print(f"  ✅ {method}")
            else:
                print(f"  ❌ {method} not found!")
        
        return True
    except Exception as e:
        print(f"❌ Collector test error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Testing VnStock Integration")
    print("=" * 50)
    
    # Test 1: Check tables
    test_tables()
    
    # Test 2: Check collector methods
    asyncio.run(test_collector())
    
    # Test 3: Check Screener API (optional - requires vnstock)
    try:
        asyncio.run(test_screener())
    except:
        print("\n⚠️ Skipping Screener API test (vnstock not configured)")
    
    print("\n" + "=" * 50)
    print("🎉 Testing complete!")
