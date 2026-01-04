"""
24hMoney Orderflow Scraper

Scrapes transaction/orderflow data and technical screening metrics from 24hMoney.
Provides Relative Strength (RS) ratings and EV/EBITDA metrics.

Endpoints:
- /stock/{SYMBOL}/transactions - Order matching history
- /api-finance-t19.24hmoney.vn/v1/ios/company/technical-filter - Screener API
"""

import asyncio
import aiohttp
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger


class Money24hScraper:
    """
    Scraper for 24hMoney orderflow and screening data.
    
    Provides:
    - Relative Strength (rs1m, rs3m, rs52w)
    - EV/EBIT, EV/EBITDA ratios
    - Beta values
    - Transaction/orderflow data
    """
    
    # Screener API (most valuable)
    SCREENER_URL = "https://api-finance-t19.24hmoney.vn/v1/ios/company/technical-filter"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._device_id = str(uuid.uuid4())
        self._browser_id = str(uuid.uuid4())
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.HEADERS
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get_screener_data(
        self,
        floor: str = 'all',
        page: int = 1,
        per_page: int = 100,
        sort_by: str = 'market_cap',
        sort_order: str = 'desc'
    ) -> List[Dict[str, Any]]:
        """
        Fetch screener data with RS ratings and valuation metrics.
        
        Args:
            floor: 'all', 'HOSE', 'HNX', 'UPCOM'
            page: Page number (1-indexed)
            per_page: Results per page
            sort_by: Sort field
            sort_order: 'asc' or 'desc'
        
        Returns: List of stock records with RS and valuation data
        """
        params = {
            'device_id': self._device_id,
            'browser_id': self._browser_id,
            'os': 'Chrome',
            'floor': floor,
            'group_id': 'all',
            'key': sort_by,
            'sort': sort_order,
            'page': page,
            'per_page': per_page,
            'param': '',  # Filter string (e.g., "pe4Q:0:50|pb4Q:0:10")
        }
        
        try:
            session = await self._get_session()
            async with session.get(self.SCREENER_URL, params=params) as resp:
                if resp.status != 200:
                    logger.warning(f"24hMoney screener failed: {resp.status}")
                    return []
                
                data = await resp.json()
                
                # Handle different response formats
                stocks = []
                if isinstance(data, dict):
                    stocks = data.get('data', {})
                    if isinstance(stocks, dict):
                        stocks = stocks.get('list', [])
                    elif isinstance(stocks, list):
                        pass  # Already a list
                elif isinstance(data, list):
                    stocks = data
                
                logger.info(f"✅ 24hMoney screener: {len(stocks)} stocks")
                
                # Normalize the data
                return [self._normalize_stock(s) for s in stocks]
                
        except Exception as e:
            logger.error(f"❌ 24hMoney screener error: {e}")
            return []
    
    def _normalize_stock(self, raw: Dict) -> Dict[str, Any]:
        """Normalize 24hMoney stock data to our schema."""
        return {
            'symbol': raw.get('symbol', ''),
            'company_name': raw.get('company_name', ''),
            'current_price': raw.get('match_price'),
            'market_cap': raw.get('market_cap'),
            
            # Financial ratios
            'pe_ratio': raw.get('pe4Q'),
            'pb_ratio': raw.get('pb4Q'),
            'eps': raw.get('eps4Q'),
            'roe': raw.get('roe'),
            'roa': raw.get('roa'),
            
            # Relative Strength (highly valuable!)
            'rs_1m': raw.get('rs1m'),
            'rs_3m': raw.get('rs3m'),
            'rs_52w': raw.get('rs52w'),
            
            # Valuation metrics
            'ev_ebit': raw.get('ev_per_ebit'),
            'ev_ebitda': raw.get('ev_per_ebitda'),
            'beta': raw.get('the_beta4Q'),
            
            # Metadata
            'exchange': raw.get('floor', ''),
            'data_source': '24hmoney',
            'updated_at': datetime.now().isoformat(),
        }
    
    async def get_all_screener_data(self, floor: str = 'all') -> List[Dict[str, Any]]:
        """
        Fetch all stocks from screener (paginated).
        
        Returns: Complete list of stocks with RS ratings
        """
        all_stocks = []
        page = 1
        per_page = 100
        
        while True:
            stocks = await self.get_screener_data(
                floor=floor,
                page=page,
                per_page=per_page
            )
            
            if not stocks:
                break
            
            all_stocks.extend(stocks)
            
            if len(stocks) < per_page:
                break
            
            page += 1
            await asyncio.sleep(0.5)  # Polite delay
        
        logger.info(f"🎉 24hMoney total: {len(all_stocks)} stocks")
        return all_stocks


# Singleton instance
_scraper: Optional[Money24hScraper] = None


async def get_24hmoney_scraper() -> Money24hScraper:
    """Get or create 24hMoney scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = Money24hScraper()
    return _scraper


# Test script
async def main():
    """Test the 24hMoney scraper."""
    scraper = Money24hScraper()
    
    try:
        print("\n📊 Testing 24hMoney screener API...")
        stocks = await scraper.get_screener_data(per_page=10)
        
        print(f"   Found {len(stocks)} stocks")
        
        if stocks:
            sample = stocks[0]
            print(f"\n   Sample: {sample['symbol']}")
            print(f"   Price: {sample['current_price']}")
            print(f"   RS 1M: {sample['rs_1m']}")
            print(f"   RS 3M: {sample['rs_3m']}")
            print(f"   RS 52W: {sample['rs_52w']}")
            print(f"   EV/EBITDA: {sample['ev_ebitda']}")
            print(f"   Beta: {sample['beta']}")
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
