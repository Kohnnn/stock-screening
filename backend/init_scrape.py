"""
Initial Database Scrape Script

Performs a complete data collection from all web sources to populate
the initial database. This creates a baseline dataset for Git commits.

Usage:
    python init_scrape.py              # Full scrape
    python init_scrape.py --quick      # Quick test (10 stocks)
    python init_scrape.py --industry   # Industry flow only
"""

import asyncio
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from database import get_database
from data_aggregator import DataAggregator
from cophieu68_collector import Cophieu68Collector
from sieucophieu_scraper import SieucophieuScraper

# Configure logging
logger.add(
    Path(__file__).parent / "logs" / "init_scrape.log",
    rotation="50 MB",
    retention="7 days",
    level="INFO"
)


async def run_full_scrape(quick_mode: bool = False, industry_only: bool = False):
    """
    Run complete data collection from all sources.
    
    Args:
        quick_mode: If True, only scrape first page (for testing)
        industry_only: If True, only scrape industry flow
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 Starting Initial Database Scrape")
    logger.info(f"   Mode: {'Quick Test' if quick_mode else 'Full Collection'}")
    logger.info(f"   Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Initialize database
    db = await get_database()
    
    results: Dict[str, Any] = {
        'started_at': start_time.isoformat(),
        'stocks_collected': 0,
        'industries_collected': 0,
        'errors': []
    }
    
    try:
        # ============= Industry Flow (Fast) =============
        logger.info("\n📊 Phase 1: Collecting Industry Flow from SieuCoPhieu API...")
        
        async with SieucophieuScraper() as scraper:
            industry_data = await scraper.collect_industry_cashflow()
            
            if industry_data:
                await db.upsert_industry_flow(industry_data)
                results['industries_collected'] = len(industry_data)
                logger.info(f"   ✅ Collected {len(industry_data)} industries")
            else:
                logger.warning("   ⚠️ No industry data collected")
        
        if industry_only:
            logger.info("Industry-only mode - skipping stock collection")
            return results
        
        # ============= Stock Data (Multi-Exchange) =============
        logger.info("\n📈 Phase 2: Collecting Stock Data from Cophieu68...")
        logger.info("   Collecting from all exchanges: HOSE, HNX, UPCOM")
        logger.info("   This will take 2-5 minutes...")
        
        collector = Cophieu68Collector()
        
        try:
            if quick_mode:
                # Quick mode: just one exchange, one vt type
                logger.info("   [Quick mode: HOSE only]")
                all_stocks = {}
                vt1_data = await collector.collect_market_data(vt_type=1, exchange_id='^vnindex')
                for stock in vt1_data:
                    symbol = stock.get('symbol')
                    if symbol:
                        all_stocks[symbol] = stock
                logger.info(f"   Got {len(all_stocks)} stocks in quick mode")
            else:
                # Full mode: all exchanges, all vt types
                all_stocks = await collector.collect_all_stocks_data()
            
            results['stocks_collected'] = len(all_stocks)
            logger.info(f"   ✅ Total: {len(all_stocks)} unique stocks")
            
            # ============= Save to Database =============
            logger.info("\n💾 Phase 3: Saving to Database...")
            
            # Prepare records for database
            stock_records = []
            price_records = []
            
            for symbol, data in all_stocks.items():
                stock_records.append({
                    'symbol': symbol,
                    'company_name': data.get('company_name'),
                    'exchange': data.get('exchange'),
                })
                
                price_records.append({
                    'symbol': symbol,
                    'current_price': data.get('current_price'),
                    'volume': data.get('volume'),
                    'market_cap': data.get('market_cap'),
                    'pe_ratio': data.get('pe_ratio'),
                    'pb_ratio': data.get('pb_ratio'),
                    'eps': data.get('eps'),
                    'roe': data.get('roe'),
                    'roa': data.get('roa'),
                    'ps_ratio': data.get('ps_ratio'),
                    'book_value': data.get('book_value'),
                    'total_debt': data.get('total_debt'),
                    'owner_equity': data.get('owner_equity'),
                    'total_assets': data.get('total_assets'),
                    'debt_to_equity': data.get('debt_to_equity'),
                    'equity_to_assets': data.get('equity_to_assets'),
                    'cash': data.get('cash'),
                    'foreign_ownership': data.get('foreign_ownership'),
                    'avg_volume_52w': data.get('avg_volume_52w'),
                    'listed_shares': data.get('listed_shares'),
                    'data_source': 'cophieu68',
                })
            
            # Batch save
            await db.upsert_stocks(stock_records)
            await db.upsert_stock_prices(price_records)
            
            # Record data versions for gap detection
            await _record_data_versions(db, list(all_stocks.keys()))
            
            logger.info(f"   ✅ Saved {len(stock_records)} stocks")
            logger.info(f"   ✅ Saved {len(price_records)} price records")
            
        finally:
            await collector.close()
        
    except Exception as e:
        logger.error(f"❌ Scrape failed: {e}")
        results['errors'].append(str(e))
        raise
    
    # ============= Summary =============
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results['completed_at'] = end_time.isoformat()
    results['duration_seconds'] = duration
    
    logger.info("\n" + "=" * 60)
    logger.info("🎉 Initial Scrape Complete!")
    logger.info(f"   Duration: {duration/60:.1f} minutes")
    logger.info(f"   Stocks: {results['stocks_collected']}")
    logger.info(f"   Industries: {results['industries_collected']}")
    logger.info(f"   Errors: {len(results['errors'])}")
    logger.info("=" * 60)
    
    # Print database path for Git
    db_path = Path(__file__).parent / "data" / "vnstock_data.db"
    logger.info(f"\n📁 Database saved to: {db_path}")
    logger.info("   Add to Git: git add backend/data/vnstock_data.db")
    
    return results


async def _record_data_versions(db, symbols: list):
    """Record data version timestamps for gap detection."""
    now = datetime.now().isoformat()
    
    # Use raw SQL for batch insert
    async with db.connection() as conn:
        for symbol in symbols:
            await conn.execute("""
                INSERT OR REPLACE INTO data_versions 
                (symbol, data_type, last_updated, source, record_count)
                VALUES (?, 'price', ?, 'cophieu68', 1)
            """, (symbol, now))
        await conn.commit()


def main():
    parser = argparse.ArgumentParser(description='Initial database scrape')
    parser.add_argument('--quick', action='store_true', help='Quick test mode (10 stocks)')
    parser.add_argument('--industry', action='store_true', help='Industry flow only')
    args = parser.parse_args()
    
    asyncio.run(run_full_scrape(
        quick_mode=args.quick,
        industry_only=args.industry
    ))


if __name__ == "__main__":
    main()
