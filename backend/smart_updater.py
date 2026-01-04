"""
Smart Data Updater

Fault-tolerant updater with gap detection that:
- Inspects local database to identify stale/missing data
- Fetches only what's needed to bring database up-to-date
- Handles offline periods (days/weeks/quarters)
- Works across machine migrations

Usage:
    python smart_updater.py                 # Run update
    python smart_updater.py analyze         # Show gaps only
    python smart_updater.py --force         # Force full refresh
"""

import asyncio
import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger
from database import get_database, Database
from cophieu68_collector import Cophieu68Collector
from sieucophieu_scraper import SieucophieuScraper

# Configure logging
logger.add(
    Path(__file__).parent / "logs" / "smart_updater.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO"
)


class DataType(Enum):
    PRICE = "price"
    FINANCIALS = "financials"
    BALANCE_SHEET = "balance_sheet"
    INDUSTRY_FLOW = "industry_flow"


@dataclass
class UpdatePlan:
    """Plan for what needs updating."""
    data_type: DataType
    symbols_to_update: List[str] = field(default_factory=list)
    last_update: Optional[datetime] = None
    gap_days: int = 0
    priority: int = 3  # 1=highest, 5=lowest
    reason: str = ""


@dataclass
class UpdateResult:
    """Result of an update operation."""
    data_type: DataType
    symbols_updated: int = 0
    symbols_failed: int = 0
    duration_seconds: float = 0
    errors: List[str] = field(default_factory=list)


# Staleness thresholds (in days)
STALENESS_THRESHOLDS = {
    DataType.PRICE: 1,           # Prices stale after 1 day
    DataType.FINANCIALS: 7,       # Financial ratios stale after 7 days
    DataType.BALANCE_SHEET: 90,   # Balance sheet quarterly
    DataType.INDUSTRY_FLOW: 0.17, # Industry flow every 4 hours (0.17 days)
}


class SmartUpdater:
    """
    Fault-tolerant data updater with intelligent gap detection.
    
    Works by:
    1. Analyzing data_versions table to find stale/missing data
    2. Creating minimal update plan
    3. Fetching only what's needed
    4. Recording new versions for future gap detection
    """
    
    def __init__(self, db: Optional[Database] = None):
        self.db = db
        self._cophieu68: Optional[Cophieu68Collector] = None
        self._sieucophieu: Optional[SieucophieuScraper] = None
    
    async def initialize(self):
        """Initialize database connection."""
        if self.db is None:
            self.db = await get_database()
    
    async def close(self):
        """Close all connections."""
        if self._cophieu68:
            await self._cophieu68.close()
        if self._sieucophieu:
            await self._sieucophieu.close()
    
    async def analyze_gaps(self) -> Dict[DataType, UpdatePlan]:
        """
        Inspect database to identify what needs updating.
        
        Returns dict of DataType -> UpdatePlan
        """
        await self.initialize()
        
        gaps: Dict[DataType, UpdatePlan] = {}
        now = datetime.now()
        
        # ============= Check Price Data =============
        price_plan = await self._analyze_price_gaps(now)
        if price_plan.symbols_to_update:
            gaps[DataType.PRICE] = price_plan
        
        # ============= Check Industry Flow =============
        industry_plan = await self._analyze_industry_gaps(now)
        if industry_plan.symbols_to_update or industry_plan.gap_days > 0:
            gaps[DataType.INDUSTRY_FLOW] = industry_plan
        
        # ============= Check Financials =============
        financial_plan = await self._analyze_financial_gaps(now)
        if financial_plan.symbols_to_update:
            gaps[DataType.FINANCIALS] = financial_plan
        
        return gaps
    
    async def _analyze_price_gaps(self, now: datetime) -> UpdatePlan:
        """Find symbols with stale or missing price data."""
        threshold = STALENESS_THRESHOLDS[DataType.PRICE]
        cutoff = now - timedelta(days=threshold)
        
        async with self.db.connection() as conn:
            # Find symbols with stale prices
            cursor = await conn.execute("""
                SELECT symbol, last_updated 
                FROM data_versions
                WHERE data_type = 'price' 
                  AND last_updated < ?
            """, (cutoff.isoformat(),))
            stale = await cursor.fetchall()
            
            # Find symbols with NO price version (never updated or new)
            cursor = await conn.execute("""
                SELECT s.symbol 
                FROM stocks s
                LEFT JOIN data_versions dv 
                  ON s.symbol = dv.symbol AND dv.data_type = 'price'
                WHERE dv.symbol IS NULL AND s.is_active = 1
            """)
            missing = await cursor.fetchall()
            
            # Count total active stocks
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM stocks WHERE is_active = 1"
            )
            total_row = await cursor.fetchone()
            total_stocks = total_row[0] if total_row else 0
        
        stale_symbols = [r[0] for r in stale]
        missing_symbols = [r[0] for r in missing]
        all_symbols = list(set(stale_symbols + missing_symbols))
        
        # Calculate gap
        gap_days = 0
        if stale:
            oldest = min(datetime.fromisoformat(r[1]) for r in stale)
            gap_days = (now - oldest).days
        
        plan = UpdatePlan(
            data_type=DataType.PRICE,
            symbols_to_update=all_symbols,
            gap_days=gap_days,
            priority=1 if missing_symbols else 2,
            reason=f"{len(stale_symbols)} stale, {len(missing_symbols)} missing, {total_stocks} total"
        )
        
        return plan
    
    async def _analyze_industry_gaps(self, now: datetime) -> UpdatePlan:
        """Check if industry flow needs update."""
        threshold_hours = STALENESS_THRESHOLDS[DataType.INDUSTRY_FLOW] * 24
        
        async with self.db.connection() as conn:
            cursor = await conn.execute("""
                SELECT MAX(timestamp) as last_update
                FROM industry_flow
            """)
            row = await cursor.fetchone()
        
        last_update = None
        gap_hours = threshold_hours + 1  # Default to stale
        
        if row and row[0]:
            try:
                last_update = datetime.fromisoformat(row[0].replace('Z', '+00:00').split('+')[0])
                gap_hours = (now - last_update).total_seconds() / 3600
            except:
                pass
        
        needs_update = gap_hours > threshold_hours
        
        return UpdatePlan(
            data_type=DataType.INDUSTRY_FLOW,
            symbols_to_update=["ALL"] if needs_update else [],
            last_update=last_update,
            gap_days=gap_hours / 24,
            priority=2,
            reason=f"Last update: {gap_hours:.1f}h ago" if last_update else "Never updated"
        )
    
    async def _analyze_financial_gaps(self, now: datetime) -> UpdatePlan:
        """Find symbols with stale financial data."""
        threshold = STALENESS_THRESHOLDS[DataType.FINANCIALS]
        cutoff = now - timedelta(days=threshold)
        
        async with self.db.connection() as conn:
            cursor = await conn.execute("""
                SELECT symbol, last_updated 
                FROM data_versions
                WHERE data_type = 'financials' 
                  AND last_updated < ?
            """, (cutoff.isoformat(),))
            stale = await cursor.fetchall()
        
        stale_symbols = [r[0] for r in stale]
        
        return UpdatePlan(
            data_type=DataType.FINANCIALS,
            symbols_to_update=stale_symbols,
            gap_days=threshold if stale else 0,
            priority=3,
            reason=f"{len(stale_symbols)} symbols with stale financials"
        )
    
    async def update_missing_only(self, force: bool = False) -> List[UpdateResult]:
        """
        Fetch ONLY missing/stale data to bring database up-to-date.
        
        Args:
            force: If True, refresh everything regardless of staleness
        """
        await self.initialize()
        
        results: List[UpdateResult] = []
        start_time = datetime.now()
        
        logger.info("🔍 Analyzing data gaps...")
        gaps = await self.analyze_gaps()
        
        if not gaps and not force:
            logger.info("✅ Database is up-to-date! No gaps detected.")
            return results
        
        logger.info(f"📋 Found {len(gaps)} data types needing update:")
        for dtype, plan in gaps.items():
            logger.info(f"   - {dtype.value}: {plan.reason}")
        
        # ============= Update Industry Flow (Fast) =============
        if DataType.INDUSTRY_FLOW in gaps or force:
            result = await self._update_industry_flow()
            results.append(result)
            
            # Update missing sectors (Backfill)
            sector_result = await self._update_missing_sectors()
            if sector_result.symbols_updated > 0:
                results.append(sector_result)
        
        # ============= Update Prices =============
        if DataType.PRICE in gaps or force:
            plan = gaps.get(DataType.PRICE, UpdatePlan(data_type=DataType.PRICE))
            result = await self._update_prices(plan, force)
            results.append(result)
        
        # Log summary
        total_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"\n🎉 Update complete in {total_time:.1f}s")
        for r in results:
            status = "✅" if not r.errors else "⚠️"
            logger.info(f"   {status} {r.data_type.value}: {r.symbols_updated} updated, {r.symbols_failed} failed")
        
        return results
    
    async def _update_industry_flow(self) -> UpdateResult:
        """Update industry flow from API."""
        start = datetime.now()
        result = UpdateResult(data_type=DataType.INDUSTRY_FLOW)
        
        logger.info("🏭 Updating industry flow...")
        
        try:
            if self._sieucophieu is None:
                self._sieucophieu = SieucophieuScraper()
            
            data = await self._sieucophieu.collect_industry_cashflow()
            
            if data:
                await self.db.upsert_industry_flow(data)
                result.symbols_updated = len(data)
                logger.info(f"   ✅ Updated {len(data)} industries")
            
        except Exception as e:
            result.errors.append(str(e))
            logger.error(f"   ❌ Industry flow update failed: {e}")
        
        result.duration_seconds = (datetime.now() - start).total_seconds()
        return result
    
    async def _update_prices(self, plan: UpdatePlan, force: bool) -> UpdateResult:
        """Update stock prices - full refresh approach."""
        start = datetime.now()
        result = UpdateResult(data_type=DataType.PRICE)
        
        symbols_needed = plan.symbols_to_update if not force else []
        
        # For simplicity, do a full refresh from cophieu68
        # This is more reliable than trying to fetch individual symbols
        logger.info(f"📈 Updating prices ({len(symbols_needed)} symbols need update)...")
        logger.info("   Using full refresh strategy (most reliable)")
        
        try:
            if self._cophieu68 is None:
                self._cophieu68 = Cophieu68Collector()
            
            # Collect all data
            all_stocks = await self._cophieu68.collect_all_stocks_data()
            
            if all_stocks:
                # Prepare database records
                price_records = []
                for symbol, data in all_stocks.items():
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
                        'book_value': data.get('book_value'),
                        'total_debt': data.get('total_debt'),
                        'owner_equity': data.get('owner_equity'),
                        'total_assets': data.get('total_assets'),
                        'foreign_ownership': data.get('foreign_ownership'),
                        'data_source': 'cophieu68',
                    })
                
                await self.db.upsert_stock_prices(price_records)
                
                # Update version tracking
                await self._record_versions(list(all_stocks.keys()), 'price')
                
                result.symbols_updated = len(price_records)
                logger.info(f"   ✅ Updated {len(price_records)} stocks")
            
        except Exception as e:
            result.errors.append(str(e))
            result.symbols_failed = len(plan.symbols_to_update)
            logger.error(f"   ❌ Price update failed: {e}")
        
        result.duration_seconds = (datetime.now() - start).total_seconds()
        return result
    
    async def _record_versions(self, symbols: List[str], data_type: str):
        """Record version timestamps for gap detection."""
        now = datetime.now().isoformat()
        
        async with self.db.connection() as conn:
            for symbol in symbols:
                await conn.execute("""
                    INSERT OR REPLACE INTO data_versions 
                    (symbol, data_type, last_updated, source, record_count)
                    VALUES (?, ?, ?, 'cophieu68', 1)
                """, (symbol, data_type, now))
            await conn.commit()
    
    async def _update_missing_sectors(self) -> UpdateResult:
        """Update missing sector/industry info."""
        start = datetime.now()
        result = UpdateResult(data_type=DataType.INDUSTRY_FLOW) # Resuing enum or add new one if needed
        
        logger.info("🏭 Checking for stocks with missing sector info...")
        
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                "SELECT symbol FROM stocks WHERE sector IS NULL OR sector = ''"
            )
            rows = await cursor.fetchall()
            missing_symbols = [r['symbol'] for r in rows]
        
        if not missing_symbols:
            logger.info("   ✅ All stocks have sector info")
            return result
            
        logger.info(f"   found {len(missing_symbols)} stocks missing sector info. Improving...")
        
        from vnstock_collector import get_collector
        collector = await get_collector()
        
        # Process in batches to save progress
        batch_size = 20
        total = len(missing_symbols)
        # Limit to 100 per run to avoid hanging too long if many are missing
        limit = 100 
        total_processed = 0
        
        for i in range(0, min(total, limit), batch_size):
            batch = missing_symbols[i:i + batch_size]
            updates = []
            
            for symbol in batch:
                try:
                    # reusing collect_stock_details which fetches overview
                    details = await collector.collect_stock_details(symbol)
                    if details.get('sector'):
                        updates.append({
                            'symbol': symbol,
                            'sector': details['sector'],
                            'industry': details['industry']
                        })
                except Exception as e:
                    logger.debug(f"Failed to get sector for {symbol}: {e}")
            
            if updates:
                async with self.db.connection() as conn:
                    await conn.executemany(
                        "UPDATE stocks SET sector = ?, industry = ? WHERE symbol = ?",
                        [(u['sector'], u['industry'], u['symbol']) for u in updates]
                    )
                    await conn.commit()
                
                result.symbols_updated += len(updates)
                logger.info(f"   Updated sectors for {result.symbols_updated} stocks")
            
            total_processed += len(batch)
            await asyncio.sleep(1)
        
        if total > limit:
            logger.info("   ⚠️ Processed 100 stocks. More updates needed on next run.")
            
        result.duration_seconds = (datetime.now() - start).total_seconds()
        return result

    def print_analysis(self, gaps: Dict[DataType, UpdatePlan]):
        """Pretty print gap analysis."""
        print("\n" + "=" * 60)
        print("📊 DATA GAP ANALYSIS")
        print("=" * 60)
        
        if not gaps:
            print("\n✅ Database is fully up-to-date!")
            print("   No stale or missing data detected.")
        else:
            for dtype, plan in gaps.items():
                print(f"\n🔶 {dtype.value.upper()}")
                print(f"   Status: {plan.reason}")
                print(f"   Gap: {plan.gap_days:.1f} days")
                print(f"   Priority: {plan.priority}/5")
                if plan.symbols_to_update and plan.symbols_to_update != ["ALL"]:
                    print(f"   Symbols: {len(plan.symbols_to_update)}")
                    if len(plan.symbols_to_update) <= 10:
                        print(f"   List: {', '.join(plan.symbols_to_update)}")
        
        print("\n" + "=" * 60)


async def main_analyze():
    """Just analyze and print gaps."""
    updater = SmartUpdater()
    try:
        gaps = await updater.analyze_gaps()
        updater.print_analysis(gaps)
    finally:
        await updater.close()


async def main_update(force: bool = False):
    """Run the update."""
    updater = SmartUpdater()
    try:
        await updater.update_missing_only(force=force)
    finally:
        await updater.close()


def main():
    parser = argparse.ArgumentParser(description='Smart Data Updater')
    parser.add_argument('command', nargs='?', default='update', 
                        choices=['update', 'analyze'],
                        help='Command to run')
    parser.add_argument('--force', action='store_true', 
                        help='Force full refresh')
    args = parser.parse_args()
    
    if args.command == 'analyze':
        asyncio.run(main_analyze())
    else:
        asyncio.run(main_update(force=args.force))


if __name__ == "__main__":
    main()
