"""
Initial Database Builder for VnStock Screener

This script builds the initial persistent database from cophieu68.vn data.
The database is meant to be committed to git as a baseline.

Usage:
    python build_initial_database.py

Features:
- Collects all stock data from cophieu68.vn (super politely)
- Stores in persistent SQLite database
- Tracks data freshness per stock using data_versions table
- Creates a manifest file for version tracking
- Skips already up-to-date data

Output:
- backend/data/initial_database.db  (git-committed baseline)
- backend/data/data_manifest.json   (metadata about what's included)
"""

import asyncio
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from loguru import logger
from cophieu68_collector import Cophieu68Collector
from database import Database
from data_freshness import DataFreshnessChecker

# Configure logging
LOG_PATH = Path(__file__).parent / "logs"
LOG_PATH.mkdir(exist_ok=True)
logger.add(LOG_PATH / "database_builder.log", rotation="10 MB", level="INFO")


class DatabaseBuilder:
    """
    Builds and maintains the initial stock database.
    
    Data freshness rules:
    - Price data: Update daily (after market close)
    - Financial ratios: Update weekly
    - Balance sheet: Update quarterly
    """
    
    # Freshness thresholds in hours
    PRICE_FRESHNESS_HOURS = 24
    FINANCIALS_FRESHNESS_HOURS = 7 * 24  # 1 week
    BALANCE_SHEET_FRESHNESS_HOURS = 90 * 24  # ~1 quarter
    
    def __init__(self, db_path: Optional[str] = None):
        self.db = Database(db_path)
        self.collector = Cophieu68Collector()
        
    async def initialize(self):
        """Initialize database with schema."""
        await self.db.initialize()
        logger.info("✅ Database initialized")
    
    async def close(self):
        """Clean up resources."""
        await self.collector.close()
    
    async def check_data_freshness(self) -> Dict[str, Any]:
        """
        Check how fresh our data is.
        Returns status for each data type.
        """
        async with self.db.connection() as db:
            # Check last update time for stock prices
            cursor = await db.execute(
                "SELECT MAX(updated_at) as last_update FROM stock_prices"
            )
            row = await cursor.fetchone()
            last_price_update = row['last_update'] if row else None
            
            # Check stocks count
            cursor = await db.execute("SELECT COUNT(*) as count FROM stocks")
            row = await cursor.fetchone()
            stocks_count = row['count'] if row else 0
            
            # Check stocks with prices
            cursor = await db.execute(
                "SELECT COUNT(*) as count FROM stock_prices WHERE current_price IS NOT NULL"
            )
            row = await cursor.fetchone()
            stocks_with_prices = row['count'] if row else 0
        
        status = {
            'stocks_count': stocks_count,
            'stocks_with_prices': stocks_with_prices,
            'last_price_update': last_price_update,
            'price_fresh': False,
            'needs_full_update': True
        }
        
        if last_price_update:
            try:
                last_update_dt = datetime.fromisoformat(last_price_update)
                hours_old = (datetime.now() - last_update_dt).total_seconds() / 3600
                status['price_fresh'] = hours_old < self.PRICE_FRESHNESS_HOURS
                status['needs_full_update'] = hours_old > self.BALANCE_SHEET_FRESHNESS_HOURS
            except:
                pass
        
        return status
    
    async def should_update(self) -> bool:
        """Check if database needs updating."""
        freshness = await self.check_data_freshness()
        
        logger.info(f"📊 Data freshness status:")
        logger.info(f"   Stocks: {freshness['stocks_count']}")
        logger.info(f"   With prices: {freshness['stocks_with_prices']}")
        logger.info(f"   Last update: {freshness['last_price_update']}")
        logger.info(f"   Price fresh: {freshness['price_fresh']}")
        
        # Always update if no data
        if freshness['stocks_count'] == 0:
            logger.info("⚠️ No data found - full update required")
            return True
        
        # Update if prices are stale
        if not freshness['price_fresh']:
            logger.info("⚠️ Price data stale - update required")
            return True
        
        logger.info("✅ Data is fresh - no update needed")
        return False
    
    async def build_database(self, force: bool = False) -> int:
        """
        Build or update the database from cophieu68.vn.
        
        Args:
            force: If True, update even if data is fresh
            
        Returns:
            Number of stocks updated
        """
        if not force and not await self.should_update():
            return 0
        
        logger.info("🚀 Starting database build from cophieu68.vn...")
        logger.info("⏳ This will take several minutes due to polite rate limiting...")
        
        try:
            # Collect all stock data (politely)
            stocks_data = await self.collector.collect_all_stocks_data()
            
            if not stocks_data:
                logger.error("❌ No data collected!")
                return 0
            
            logger.info(f"📊 Collected data for {len(stocks_data)} stocks")
            
            # Prepare data for database
            stocks_list = []
            prices_list = []
            
            for symbol, data in stocks_data.items():
                # Extract stock listing info
                stock_record = {
                    'symbol': symbol,
                    'company_name': data.get('company_name'),
                    'exchange': self._detect_exchange(symbol),
                    'sector': None,  # cophieu68 doesn't provide this directly
                    'industry': None,
                }
                stocks_list.append(stock_record)
                
                # Extract price and metrics
                price_record = {
                    'symbol': symbol,
                    'current_price': data.get('current_price'),
                    'volume': data.get('volume'),
                    'market_cap': data.get('market_cap'),
                    'pe_ratio': data.get('pe_ratio'),
                    'pb_ratio': data.get('pb_ratio'),
                    'eps': data.get('eps'),
                    'roe': data.get('roe'),
                    'roa': data.get('roa'),
                    # Additional metrics from cophieu68
                    'book_value': data.get('book_value'),
                    'ps_ratio': data.get('ps_ratio'),
                    'total_debt': data.get('total_debt'),
                    'owner_equity': data.get('owner_equity'),
                    'total_assets': data.get('total_assets'),
                    'debt_to_equity': data.get('debt_to_equity'),
                    'cash': data.get('cash'),
                    'foreign_ownership': data.get('foreign_ownership'),
                    'data_source': 'cophieu68',
                }
                prices_list.append(price_record)
            
            # Save to database
            await self.db.upsert_stocks(stocks_list)
            await self.db.upsert_stock_prices(prices_list)
            
            logger.info(f"✅ Database updated with {len(stocks_list)} stocks")
            
            # Save raw data as JSON backup
            backup_path = Path(__file__).parent / "data" / "cophieu68_backup.json"
            backup_path.parent.mkdir(exist_ok=True)
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'updated_at': datetime.now().isoformat(),
                    'stocks_count': len(stocks_data),
                    'data': stocks_data
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Backup saved to {backup_path}")
            
            return len(stocks_list)
            
        except Exception as e:
            logger.error(f"❌ Error building database: {e}")
            raise
    
    def _detect_exchange(self, symbol: str) -> str:
        """
        Detect exchange based on symbol characteristics.
        This is a basic heuristic - cophieu68 doesn't explicitly provide exchange.
        """
        # Major HOSE stocks (simplified list)
        hose_stocks = {
            'VNM', 'VCB', 'VIC', 'VHM', 'HPG', 'FPT', 'MWG', 'TCB', 'VPB', 
            'MBB', 'ACB', 'CTG', 'BID', 'GAS', 'SAB', 'PLX', 'SSI', 'POW'
        }
        
        if symbol in hose_stocks:
            return 'HOSE'
        
        # Default to HOSE for now - can be improved with better data
        return 'HOSE'


async def main():
    """Main entry point for database building."""
    logger.info("=" * 60)
    logger.info("VnStock Screener - Initial Database Builder")
    logger.info("=" * 60)
    
    # Paths
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    runtime_db_path = data_dir / "vnstock_data.db"
    initial_db_path = data_dir / "initial_database.db"
    manifest_path = data_dir / "data_manifest.json"
    
    builder = DatabaseBuilder(str(runtime_db_path))
    
    try:
        await builder.initialize()
        
        # Check current status
        freshness = await builder.check_data_freshness()
        logger.info(f"\n📊 Current database status:")
        logger.info(f"   Total stocks: {freshness['stocks_count']}")
        logger.info(f"   Stocks with prices: {freshness['stocks_with_prices']}")
        logger.info(f"   Last update: {freshness['last_price_update']}")
        
        # Build/update database
        count = await builder.build_database(force=True)  # Force first time
        
        logger.info(f"\n🎉 Database build complete!")
        logger.info(f"   Updated {count} stocks")
        
        # Record freshness for all collected stocks
        if count > 0:
            freshness_checker = DataFreshnessChecker(str(runtime_db_path))
            
            # Get all symbols
            async with builder.db.connection() as db:
                cursor = await db.execute("SELECT symbol FROM stocks")
                rows = await cursor.fetchall()
                symbols = [row['symbol'] for row in rows]
            
            # Record updates
            freshness_checker.record_bulk_update(symbols, 'price', 'cophieu68')
            freshness_checker.record_bulk_update(symbols, 'financials', 'cophieu68')
            freshness_checker.record_bulk_update(symbols, 'balance_sheet', 'cophieu68')
            
            logger.info(f"📝 Recorded freshness for {len(symbols)} symbols")
            
            # Create manifest
            manifest = {
                'created_at': datetime.now().isoformat(),
                'version': '1.0',
                'source': 'cophieu68.vn',
                'stocks_count': count,
                'data_types': ['price', 'financials', 'balance_sheet'],
                'freshness_summary': freshness_checker.get_update_summary(),
                'description': 'Initial database baseline for VnStock Screener'
            }
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)
            
            logger.info(f"📄 Manifest saved to {manifest_path}")
            
            # Copy to initial_database.db for git commit
            shutil.copy2(runtime_db_path, initial_db_path)
            logger.info(f"💾 Initial database saved to {initial_db_path}")
            
            # Print final summary
            print("\n" + "="*60)
            print("✅ INITIAL DATABASE BUILD COMPLETE")
            print("="*60)
            print(f"\nFiles created:")
            print(f"  - {initial_db_path} (commit this to git)")
            print(f"  - {manifest_path}")
            print(f"\nTo use with Docker, copy initial_database.db to runtime location.")
            print("="*60 + "\n")
        
    finally:
        await builder.close()


if __name__ == "__main__":
    asyncio.run(main())
