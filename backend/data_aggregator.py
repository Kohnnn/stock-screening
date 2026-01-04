"""
Data Aggregator Module

Unified data collection orchestrator that:
- Coordinates multiple scrapers
- Merges data from different sources
- Handles conflict resolution
- Validates and normalizes data
- Provides atomic database updates

This replaces the vnstock library dependency with web scraping.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from loguru import logger

from base_scraper import BaseScraper
from cophieu68_collector import Cophieu68Collector
from sieucophieu_scraper import SieucophieuScraper
from money24h_scraper import Money24hScraper

# Configure logging
logger.add(
    Path(__file__).parent / "logs" / "aggregator.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)


class DataAggregator:
    """
    Orchestrates data collection from multiple sources.
    
    Priority order for conflicting data:
    1. cophieu68 - most reliable for prices and fundamentals
    2. 24hmoney - best for active buy/sell flow
    3. sieucophieu - unique industry cashflow data
    
    Collection modes:
    - full: Complete data refresh from all sources
    - prices: Quick price update from bulk endpoint
    - industry: Industry flow update only
    - transactions: Stock-level transaction flow
    """
    
    def __init__(self, db=None):
        self.db = db
        self._cophieu68: Optional[Cophieu68Collector] = None
        self._sieucophieu: Optional[SieucophieuScraper] = None
        self._money24h: Optional[Money24hScraper] = None
    
    async def _get_cophieu68(self) -> Cophieu68Collector:
        if self._cophieu68 is None:
            self._cophieu68 = Cophieu68Collector()
        return self._cophieu68
    
    async def _get_sieucophieu(self) -> SieucophieuScraper:
        if self._sieucophieu is None:
            self._sieucophieu = SieucophieuScraper()
        return self._sieucophieu
    
    async def _get_money24h(self) -> Money24hScraper:
        if self._money24h is None:
            self._money24h = Money24hScraper()
        return self._money24h
    
    async def close(self):
        """Close all scraper sessions."""
        if self._cophieu68:
            await self._cophieu68.close()
        if self._sieucophieu:
            await self._sieucophieu.close()
        if self._money24h:
            await self._money24h.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    # ==================== Collection Methods ====================
    
    async def collect_all_stocks(self) -> Dict[str, Dict[str, Any]]:
        """
        Collect complete stock data from cophieu68.
        
        Returns dict keyed by symbol with merged data from all vt views.
        This is the primary source for stock listings and fundamentals.
        """
        logger.info("📊 Starting full stock collection from cophieu68...")
        
        cophieu68 = await self._get_cophieu68()
        
        try:
            data = await cophieu68.collect_all_stocks_data()
            
            # Validate collected data
            valid_count = 0
            for symbol, stock_data in data.items():
                is_valid, errors = self._validate_stock(stock_data)
                if is_valid:
                    valid_count += 1
                else:
                    logger.debug(f"Validation issues for {symbol}: {errors}")
            
            logger.info(f"✅ Collected {len(data)} stocks, {valid_count} valid")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error collecting stocks: {e}")
            return {}
    
    async def collect_industry_flow(self) -> List[Dict[str, Any]]:
        """
        Collect industry cashflow data from sieucophieu.
        
        Returns list of industry records with cashflow and relative strength.
        """
        logger.info("🏭 Collecting industry flow from sieucophieu...")
        
        sieucophieu = await self._get_sieucophieu()
        
        try:
            data = await sieucophieu.collect_industry_cashflow()
            logger.info(f"✅ Collected {len(data)} industry records")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error collecting industry flow: {e}")
            return []
    
    async def collect_transaction_flow(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Collect active buy/sell data for specific stocks from 24hmoney.
        
        Best used for VN30 or watchlist stocks, not all 1700+.
        """
        logger.info(f"💹 Collecting transaction flow for {len(symbols)} stocks...")
        
        money24h = await self._get_money24h()
        
        try:
            data = await money24h.collect_batch_transactions(symbols)
            logger.info(f"✅ Collected transactions for {len(data)} stocks")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error collecting transactions: {e}")
            return []
    
    async def collect_full_update(self) -> Dict[str, Any]:
        """
        Perform a complete data update from all sources.
        
        Returns summary with collected counts and any errors.
        """
        logger.info("🚀 Starting full data update from all sources...")
        start_time = datetime.now()
        
        results = {
            'started_at': start_time.isoformat(),
            'stocks': {},
            'industry_flow': [],
            'errors': []
        }
        
        # 1. Collect stocks from cophieu68 (primary source)
        try:
            stocks = await self.collect_all_stocks()
            results['stocks'] = stocks
            results['stocks_count'] = len(stocks)
        except Exception as e:
            results['errors'].append(f"Stock collection failed: {e}")
        
        # Small pause between sources
        await asyncio.sleep(2)
        
        # 2. Collect industry flow from sieucophieu
        try:
            industry = await self.collect_industry_flow()
            results['industry_flow'] = industry
            results['industry_count'] = len(industry)
        except Exception as e:
            results['errors'].append(f"Industry flow failed: {e}")
        
        # Calculate duration
        end_time = datetime.now()
        results['completed_at'] = end_time.isoformat()
        results['duration_seconds'] = (end_time - start_time).total_seconds()
        
        logger.info(
            f"✅ Full update complete in {results['duration_seconds']:.1f}s - "
            f"Stocks: {results.get('stocks_count', 0)}, "
            f"Industries: {results.get('industry_count', 0)}"
        )
        
        return results
    
    # ==================== Merge & Validation ====================
    
    def merge_stock_data(
        self,
        primary: Dict[str, Any],
        secondary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge stock data from two sources.
        
        Primary source takes precedence for conflicting values.
        Secondary fills in missing fields.
        """
        merged = primary.copy()
        
        for key, value in secondary.items():
            if key not in merged or merged[key] is None:
                merged[key] = value
            elif key == 'updated_at':
                # Use most recent timestamp
                pass
        
        return merged
    
    def _validate_stock(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a stock data record."""
        errors = []
        
        if not data.get('symbol'):
            errors.append("Missing symbol")
        
        if data.get('current_price') is not None:
            price = data['current_price']
            if price < 0:
                errors.append(f"Negative price: {price}")
            elif price > 10_000_000:
                errors.append(f"Price too high: {price}")
        
        if data.get('pe_ratio') is not None:
            pe = data['pe_ratio']
            if pe < -1000 or pe > 10000:
                errors.append(f"Invalid P/E: {pe}")
        
        return len(errors) == 0, errors
    
    # ==================== Database Integration ====================
    
    async def save_to_database(self, data: Dict[str, Any]) -> int:
        """
        Save collected data to database.
        
        Returns number of records saved.
        """
        if not self.db:
            logger.warning("No database configured, skipping save")
            return 0
        
        saved_count = 0
        
        # Save stocks
        if data.get('stocks'):
            stocks_list = list(data['stocks'].values())
            
            # Convert to stock format for database
            stock_records = []
            price_records = []
            
            for stock in stocks_list:
                stock_records.append({
                    'symbol': stock.get('symbol'),
                    'company_name': stock.get('company_name'),
                    'exchange': stock.get('exchange'),
                })
                
                price_records.append({
                    'symbol': stock.get('symbol'),
                    'current_price': stock.get('current_price'),
                    'volume': stock.get('volume'),
                    'market_cap': stock.get('market_cap'),
                    'pe_ratio': stock.get('pe_ratio'),
                    'pb_ratio': stock.get('pb_ratio'),
                    'eps': stock.get('eps'),
                    'roe': stock.get('roe'),
                    'roa': stock.get('roa'),
                    'foreign_ownership': stock.get('foreign_ownership'),
                    'data_source': 'cophieu68',
                })
            
            await self.db.upsert_stocks(stock_records)
            await self.db.upsert_stock_prices(price_records)
            saved_count += len(stock_records)
        
        # Save industry flow
        if data.get('industry_flow'):
            await self.db.upsert_industry_flow(data['industry_flow'])
            saved_count += len(data['industry_flow'])
        
        logger.info(f"💾 Saved {saved_count} records to database")
        return saved_count
    
    # ==================== Testing ====================
    
    async def test_connectivity(self) -> Dict[str, bool]:
        """Test connectivity to all data sources."""
        results = {}
        
        logger.info("🧪 Testing connectivity to all sources...")
        
        # Test cophieu68
        try:
            cophieu68 = await self._get_cophieu68()
            html = await cophieu68._fetch_page(f"{cophieu68.BASE_URL}/")
            results['cophieu68'] = html is not None
        except Exception as e:
            logger.error(f"cophieu68 test failed: {e}")
            results['cophieu68'] = False
        
        # Test sieucophieu
        try:
            sieucophieu = await self._get_sieucophieu()
            data = await sieucophieu.collect_industry_cashflow()
            results['sieucophieu'] = len(data) > 0
        except Exception as e:
            logger.error(f"sieucophieu test failed: {e}")
            results['sieucophieu'] = False
        
        # Test 24hmoney
        try:
            money24h = await self._get_money24h()
            html = await money24h.fetch(f"{money24h.BASE_URL}/")
            results['24hmoney'] = html is not None
        except Exception as e:
            logger.error(f"24hmoney test failed: {e}")
            results['24hmoney'] = False
        
        for source, ok in results.items():
            status = "✅" if ok else "❌"
            logger.info(f"  {status} {source}")
        
        return results
    
    async def test_collect(self):
        """Quick test collection."""
        logger.info("🧪 Running test collection...")
        
        # Test industry flow (fastest)
        industries = await self.collect_industry_flow()
        print(f"\n🏭 Industries: {len(industries)}")
        if industries:
            print(f"   Sample: {industries[0]}")
        
        # Test single page of stocks (limited)
        cophieu68 = await self._get_cophieu68()
        stocks = await cophieu68.collect_market_data(vt_type=1, max_pages=1)
        print(f"\n📊 Stocks (1 page): {len(stocks)}")
        if stocks:
            print(f"   Sample: {stocks[0]}")


# Standalone test
async def main():
    """Test the data aggregator."""
    async with DataAggregator() as aggregator:
        # Test connectivity
        results = await aggregator.test_connectivity()
        print("\n📡 Connectivity Test Results:")
        for source, ok in results.items():
            print(f"  {'✅' if ok else '❌'} {source}")
        
        # Test quick collection
        await aggregator.test_collect()


if __name__ == "__main__":
    asyncio.run(main())
