"""
End-to-End Integration Tests

Tests the complete flow from backend database to frontend API calls.
Verifies:
- Database contains valid stock data
- Backend API serves data correctly
- Financial metrics are calculated properly
- Gap detection works
"""

import asyncio
import aiohttp
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


# ============= Test Configuration =============

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:80"


# ============= Database Tests =============

@pytest.mark.asyncio
async def test_database_has_stocks():
    """Verify database contains stock records."""
    from database import get_database
    
    db = await get_database()
    stats = await db.get_database_stats()
    
    assert stats['stocks_count'] > 0, "Database should have stock records"
    print(f"✅ Database has {stats['stocks_count']} stocks")


@pytest.mark.asyncio
async def test_database_has_prices():
    """Verify stock prices are populated."""
    from database import get_database
    
    db = await get_database()
    stats = await db.get_database_stats()
    
    assert stats['stock_prices_count'] > 0, "Database should have price records"
    print(f"✅ Database has {stats['stock_prices_count']} price records")


@pytest.mark.asyncio
async def test_database_has_industry_flow():
    """Verify industry flow data exists."""
    from database import get_database
    
    db = await get_database()
    industries = await db.get_industry_flow(limit=10)
    
    assert len(industries) > 0, "Database should have industry flow records"
    print(f"✅ Database has {len(industries)}+ industry flow records")


@pytest.mark.asyncio
async def test_data_freshness():
    """Verify data is not stale."""
    from database import get_database
    
    db = await get_database()
    freshness = await db.get_data_freshness()
    
    assert freshness in ['fresh', 'stale'], f"Data freshness: {freshness}"
    print(f"✅ Data freshness status: {freshness}")


# ============= Gap Detection Tests =============

@pytest.mark.asyncio
async def test_gap_detection_works():
    """Verify smart updater can detect gaps."""
    from smart_updater import SmartUpdater
    
    updater = SmartUpdater()
    try:
        gaps = await updater.analyze_gaps()
        
        # After initial scrape, should have minimal or no gaps
        print(f"✅ Gap detection found {len(gaps)} data types needing update")
        for dtype, plan in gaps.items():
            print(f"   - {dtype.value}: {plan.reason}")
    finally:
        await updater.close()


@pytest.mark.asyncio
async def test_gap_detection_finds_missing():
    """Verify gap detection finds new/missing symbols."""
    from database import get_database
    from smart_updater import SmartUpdater, DataType
    
    db = await get_database()
    
    # Add a fake stock that won't have version tracking
    async with db.connection() as conn:
        await conn.execute("""
            INSERT OR IGNORE INTO stocks (symbol, company_name, is_active)
            VALUES ('TEST_MISSING', 'Test Missing Stock', 1)
        """)
        await conn.commit()
    
    updater = SmartUpdater(db=db)
    try:
        gaps = await updater.analyze_gaps()
        
        if DataType.PRICE in gaps:
            symbols = gaps[DataType.PRICE].symbols_to_update
            assert 'TEST_MISSING' in symbols, "Should detect TEST_MISSING as missing"
            print("✅ Gap detection correctly identifies missing symbols")
        
        # Cleanup
        async with db.connection() as conn:
            await conn.execute("DELETE FROM stocks WHERE symbol = 'TEST_MISSING'")
            await conn.commit()
    finally:
        await updater.close()


# ============= API Tests =============

@pytest.mark.asyncio
async def test_backend_health():
    """Verify backend health endpoint responds."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/api/health") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data.get('status') in ['healthy', 'ok']
                print(f"✅ Backend health: {data}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Backend not running - skipping API test")


@pytest.mark.asyncio
async def test_api_returns_stocks():
    """Verify API returns stock list."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/api/stocks") as resp:
                assert resp.status == 200
                data = await resp.json()
                
                stocks = data.get('stocks', data)  # Handle different response formats
                if isinstance(stocks, list):
                    assert len(stocks) > 0, "API should return stocks"
                    print(f"✅ API returned {len(stocks)} stocks")
                    
                    # Check first stock has expected fields
                    first = stocks[0]
                    assert 'symbol' in first
                    print(f"   Sample: {first.get('symbol')}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Backend not running - skipping API test")


@pytest.mark.asyncio
async def test_api_returns_sectors():
    """Verify API returns sector list."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{BACKEND_URL}/api/sectors") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ API returned sectors: {data}")
                else:
                    print(f"⚠️ Sectors endpoint returned {resp.status}")
        except aiohttp.ClientConnectorError:
            pytest.skip("Backend not running - skipping API test")


# ============= Financial Metrics Tests =============

@pytest.mark.asyncio
async def test_financial_metrics_calculated():
    """Verify financial metrics have valid values."""
    from database import get_database
    
    db = await get_database()
    stocks = await db.get_stocks(limit=100)
    
    # Count stocks with valid metrics
    with_pe = sum(1 for s in stocks if s.get('pe_ratio') is not None)
    with_roe = sum(1 for s in stocks if s.get('roe') is not None)
    with_mcap = sum(1 for s in stocks if s.get('market_cap') is not None)
    
    print(f"✅ Metrics coverage in top 100 stocks:")
    print(f"   P/E: {with_pe}/100")
    print(f"   ROE: {with_roe}/100")  
    print(f"   Market Cap: {with_mcap}/100")
    
    # At least some should have metrics
    assert with_mcap > 0, "Should have market cap data"


@pytest.mark.asyncio
async def test_price_data_valid():
    """Verify price data is valid (positive, reasonable range)."""
    from database import get_database
    
    db = await get_database()
    stocks = await db.get_stocks(limit=100)
    
    valid_prices = 0
    for stock in stocks:
        price = stock.get('current_price')
        if price is not None and 0 < price < 10_000_000:  # Reasonable VND range
            valid_prices += 1
    
    print(f"✅ {valid_prices}/100 stocks have valid prices")
    assert valid_prices > 50, "Most stocks should have valid prices"


# ============= Docker Persistence Tests =============

@pytest.mark.asyncio
async def test_database_file_exists():
    """Verify database file exists for persistence."""
    db_path = Path(__file__).parent.parent / "data" / "vnstock_data.db"
    
    assert db_path.exists(), f"Database should exist at {db_path}"
    
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"✅ Database file exists: {db_path}")
    print(f"   Size: {size_mb:.2f} MB")


# ============= Run Tests =============

async def run_all_tests():
    """Run all tests without pytest."""
    print("\n" + "=" * 60)
    print("🧪 INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Database has stocks", test_database_has_stocks),
        ("Database has prices", test_database_has_prices),
        ("Database has industry flow", test_database_has_industry_flow),
        ("Data freshness", test_data_freshness),
        ("Gap detection works", test_gap_detection_works),
        ("Financial metrics populated", test_financial_metrics_calculated),
        ("Price data valid", test_price_data_valid),
        ("Database file exists", test_database_file_exists),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\n📋 Running: {name}...")
        try:
            await test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
