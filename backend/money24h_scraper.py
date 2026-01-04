"""
24HMoney.vn Scraper

Collects financial data, transaction flow, and sector analysis from 24hmoney.vn.
This site uses Nuxt.js with SSR, so we can extract data from the __NUXT__ state
or use their internal APIs.

Key data:
- Transaction flow (active buy/sell per stock)
- Sector money flow
- Financial reports
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from loguru import logger

from base_scraper import BaseScraper, RateLimiter


class Money24hScraper(BaseScraper):
    """
    Scraper for 24hmoney.vn financial data.
    
    Uses Nuxt.js state extraction and DOM parsing for:
    - Stock transaction flow (active buy/sell)
    - Sector money flow
    - Financial indicators
    """
    
    BASE_URL = "https://24hmoney.vn"
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        if rate_limiter is None:
            rate_limiter = RateLimiter(
                min_delay=2.0,
                max_jitter=1.0,
                max_per_minute=20
            )
        super().__init__(name="24HMoney", rate_limiter=rate_limiter)
    
    def _extract_nuxt_state(self, html: str) -> Optional[Dict]:
        """
        Extract __NUXT__ state from Nuxt.js page.
        
        The Nuxt state contains pre-fetched data for hydration.
        """
        try:
            # Look for window.__NUXT__ = {...}
            match = re.search(
                r'window\.__NUXT__\s*=\s*(\{.+?\})(?:\s*;?\s*</script>)',
                html,
                re.DOTALL
            )
            if match:
                # Parse JSON (may need cleaning)
                json_str = match.group(1)
                # Fix common issues
                json_str = re.sub(r'undefined', 'null', json_str)
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.debug(f"[{self.name}] Could not parse Nuxt state: {e}")
        except Exception as e:
            logger.debug(f"[{self.name}] Error extracting Nuxt state: {e}")
        return None
    
    async def collect_sector_flow(self) -> List[Dict[str, Any]]:
        """
        Collect sector-level money flow data.
        
        URL: /recommend/business
        Shows money flow distribution across industries.
        """
        url = f"{self.BASE_URL}/recommend/business"
        
        logger.info(f"[{self.name}] Fetching sector money flow...")
        
        html = await self.fetch(url)
        if not html:
            return []
        
        results = []
        
        # Try Nuxt state first
        nuxt_data = self._extract_nuxt_state(html)
        if nuxt_data and 'data' in nuxt_data:
            # Navigate Nuxt structure to find sector data
            for page_data in nuxt_data.get('data', []):
                if isinstance(page_data, dict):
                    # Look for business/sector data
                    for key, value in page_data.items():
                        if 'business' in key.lower() or 'sector' in key.lower():
                            if isinstance(value, list):
                                for item in value:
                                    if isinstance(item, dict):
                                        results.append(self._parse_sector_item(item))
        
        # Fallback to DOM parsing
        if not results:
            soup = BeautifulSoup(html, 'html.parser')
            # Look for sector tables or cards
            sector_items = soup.find_all(['tr', 'div'], class_=lambda x: x and ('sector' in x.lower() or 'business' in x.lower()))
            for item in sector_items:
                parsed = self._parse_sector_dom_item(item)
                if parsed:
                    results.append(parsed)
        
        logger.info(f"[{self.name}] Collected {len(results)} sector flow records")
        return results
    
    def _parse_sector_item(self, item: Dict) -> Dict[str, Any]:
        """Parse a sector item from Nuxt state."""
        return {
            'industry_name': item.get('name') or item.get('industry'),
            'net_buy_volume': item.get('netBuyVolume') or item.get('net_buy'),
            'net_buy_value': item.get('netBuyValue') or item.get('net_value'),
            'sector_performance': item.get('performance') or item.get('change'),
            'source': '24hmoney',
            'timestamp': datetime.now().isoformat()
        }
    
    def _parse_sector_dom_item(self, element) -> Optional[Dict[str, Any]]:
        """Parse a sector item from DOM element."""
        try:
            text = element.get_text(strip=True)
            if not text:
                return None
            
            # Basic extraction - will need refinement based on actual HTML
            return {
                'industry_name': text[:50],  # Truncate
                'source': '24hmoney',
                'timestamp': datetime.now().isoformat()
            }
        except Exception:
            return None
    
    async def collect_stock_transactions(self, symbol: str) -> Dict[str, Any]:
        """
        Collect transaction flow data for a specific stock.
        
        URL: /stock/{SYMBOL}/transactions
        Shows active buy/sell volumes.
        """
        url = f"{self.BASE_URL}/stock/{symbol.upper()}/transactions"
        
        logger.debug(f"[{self.name}] Fetching transactions for {symbol}...")
        
        html = await self.fetch(url)
        if not html:
            return {}
        
        result = {'symbol': symbol.upper()}
        
        # Try Nuxt state
        nuxt_data = self._extract_nuxt_state(html)
        if nuxt_data:
            for page_data in nuxt_data.get('data', []):
                if isinstance(page_data, dict):
                    transactions = page_data.get('transactions') or page_data.get('data')
                    if isinstance(transactions, list):
                        # Calculate totals from transaction list
                        buy_vol = 0
                        sell_vol = 0
                        for tx in transactions:
                            if isinstance(tx, dict):
                                vol = tx.get('volume', 0) or 0
                                if tx.get('side', '').lower() == 'buy' or tx.get('isBuy'):
                                    buy_vol += vol
                                else:
                                    sell_vol += vol
                        result['active_buy_volume'] = buy_vol
                        result['active_sell_volume'] = sell_vol
                        result['net_buy_volume'] = buy_vol - sell_vol
                        return result
        
        # DOM parsing fallback
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for buy/sell summary elements
        for element in soup.find_all(['div', 'span', 'td']):
            text = element.get_text(strip=True).lower()
            
            if 'mua' in text or 'buy' in text:
                # Try to find associated number
                num_match = re.search(r'[\d,]+(?:\.\d+)?', element.get_text())
                if num_match:
                    result['active_buy_volume'] = self.parse_number(num_match.group())
            
            elif 'bán' in text or 'sell' in text:
                num_match = re.search(r'[\d,]+(?:\.\d+)?', element.get_text())
                if num_match:
                    result['active_sell_volume'] = self.parse_number(num_match.group())
        
        if 'active_buy_volume' in result and 'active_sell_volume' in result:
            result['net_buy_volume'] = (result.get('active_buy_volume') or 0) - (result.get('active_sell_volume') or 0)
        
        return result
    
    async def collect_financial_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Collect financial indicators for a specific stock.
        
        URL: /stock/{SYMBOL}/financial-indicators
        """
        url = f"{self.BASE_URL}/stock/{symbol.upper()}/financial-indicators"
        
        logger.debug(f"[{self.name}] Fetching financial indicators for {symbol}...")
        
        html = await self.fetch(url)
        if not html:
            return {}
        
        result = {'symbol': symbol.upper()}
        
        # Try Nuxt state
        nuxt_data = self._extract_nuxt_state(html)
        if nuxt_data:
            for page_data in nuxt_data.get('data', []):
                if isinstance(page_data, dict):
                    # Look for financial indicator fields
                    for key in ['pe', 'pb', 'roe', 'roa', 'eps', 'marketCap']:
                        if key in page_data:
                            result[key.lower()] = page_data[key]
        
        # DOM parsing fallback
        soup = BeautifulSoup(html, 'html.parser')
        
        indicator_patterns = {
            'P/E': 'pe_ratio',
            'P/B': 'pb_ratio',
            'ROE': 'roe',
            'ROA': 'roa',
            'EPS': 'eps'
        }
        
        for pattern, field in indicator_patterns.items():
            for element in soup.find_all(['td', 'div', 'span']):
                if pattern in element.get_text():
                    # Find next sibling or parent for value
                    value_elem = element.find_next(['td', 'div', 'span'])
                    if value_elem:
                        num = self.parse_number(value_elem.get_text())
                        if num is not None:
                            result[field] = num
                            break
        
        return result
    
    async def collect_batch_transactions(self, symbols: List[str], batch_size: int = 5) -> List[Dict[str, Any]]:
        """
        Collect transaction data for multiple symbols.
        
        Uses small batch sizes to be polite to the server.
        """
        results = []
        
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            logger.info(f"[{self.name}] Processing batch {i//batch_size + 1}: {batch}")
            
            for symbol in batch:
                try:
                    data = await self.collect_stock_transactions(symbol)
                    if data:
                        results.append(data)
                except Exception as e:
                    logger.error(f"[{self.name}] Error collecting {symbol}: {e}")
            
            # Extra pause between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(2)
        
        return results
    
    async def collect(self) -> List[Dict[str, Any]]:
        """Main collection method - returns sector flow data."""
        return await self.collect_sector_flow()
    
    async def test(self) -> bool:
        """Test connectivity."""
        logger.info(f"[{self.name}] Testing connectivity...")
        
        try:
            # Test main page
            html = await self.fetch(f"{self.BASE_URL}/")
            if html:
                logger.info(f"[{self.name}] ✅ Main page accessible")
                
                # Test a stock transaction page
                tx_data = await self.collect_stock_transactions("VNM")
                logger.info(f"[{self.name}] VNM transaction test: {tx_data}")
                
                return True
            return False
        except Exception as e:
            logger.error(f"[{self.name}] ❌ Test failed: {e}")
            return False
        finally:
            await self.close()


# Standalone test
async def main():
    """Test the scraper."""
    async with Money24hScraper() as scraper:
        success = await scraper.test()
        
        if success:
            # Test sector flow
            sectors = await scraper.collect_sector_flow()
            print(f"\n📊 Sector Flow: {len(sectors)} sectors")
            
            # Test transaction for a single stock
            tx = await scraper.collect_stock_transactions("HPG")
            print(f"🔄 HPG Transactions: {tx}")


if __name__ == "__main__":
    asyncio.run(main())
