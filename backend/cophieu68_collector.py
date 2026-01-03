"""
Cophieu68.vn Data Collector

Super polite web scraper for Vietnamese stock data from cophieu68.vn
with robust rate limiting to avoid stressing the server.

Data sources:
- vt=1: Listings, market cap, volume, foreign ownership
- vt=2: Financial ratios (PE, EPS, ROE, ROA, P/B, PS)
- vt=3: Balance sheet (Debt, Equity, Assets, Cash)
- historydaily.php: Daily OHLCV price data
"""

import asyncio
import aiohttp
import re
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from loguru import logger

# Configure logging
logger.add(
    Path(__file__).parent / "logs" / "cophieu68_collector.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)


class Cophieu68Collector:
    """
    Super polite web scraper for cophieu68.vn data.
    
    Rate limiting:
    - Minimum 3 seconds between requests
    - Random jitter of 0-2 seconds added
    - Exponential backoff on errors
    - Maximum 10 requests per minute
    
    This ensures we don't stress the cophieu68 server.
    """
    
    BASE_URL = "https://www.cophieu68.vn"
    
    # Super polite rate limiting settings
    MIN_REQUEST_DELAY = 3.0  # Minimum 3 seconds between requests
    MAX_JITTER = 2.0         # Random jitter up to 2 seconds
    MAX_REQUESTS_PER_MINUTE = 10
    BACKOFF_MULTIPLIER = 2.0
    MAX_BACKOFF = 60.0       # Maximum backoff of 60 seconds
    
    # Request timeout
    REQUEST_TIMEOUT = 30
    
    # User agent to identify ourselves politely
    USER_AGENT = "VnStockScreener/1.0 (Educational Purpose; Polite Scraper)"
    
    def __init__(self):
        self._last_request_time: float = 0
        self._request_count: int = 0
        self._minute_start: float = 0
        self._consecutive_errors: int = 0
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
            }
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
        return self._session
    
    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _wait_politely(self):
        """
        Wait politely before making a request.
        Implements rate limiting with jitter.
        """
        import random
        
        now = asyncio.get_event_loop().time()
        
        # Check requests per minute limit
        if now - self._minute_start > 60:
            self._minute_start = now
            self._request_count = 0
        
        if self._request_count >= self.MAX_REQUESTS_PER_MINUTE:
            wait_time = 60 - (now - self._minute_start)
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                self._minute_start = asyncio.get_event_loop().time()
                self._request_count = 0
        
        # Calculate delay with exponential backoff on errors
        base_delay = self.MIN_REQUEST_DELAY
        if self._consecutive_errors > 0:
            backoff = min(
                base_delay * (self.BACKOFF_MULTIPLIER ** self._consecutive_errors),
                self.MAX_BACKOFF
            )
            base_delay = backoff
            logger.warning(f"⚠️ Backoff active: {base_delay:.1f}s delay (errors: {self._consecutive_errors})")
        
        # Add random jitter
        jitter = random.uniform(0, self.MAX_JITTER)
        total_delay = base_delay + jitter
        
        # Wait for minimum time since last request
        time_since_last = now - self._last_request_time
        if time_since_last < total_delay:
            wait_time = total_delay - time_since_last
            logger.debug(f"🐢 Waiting politely for {wait_time:.1f}s...")
            await asyncio.sleep(wait_time)
        
        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1
    
    async def _fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch a page with polite rate limiting.
        Returns HTML content or None on error.
        """
        await self._wait_politely()
        
        session = await self._get_session()
        
        try:
            logger.info(f"📥 Fetching: {url}")
            async with session.get(url) as response:
                if response.status == 200:
                    self._consecutive_errors = 0  # Reset on success
                    html = await response.text()
                    logger.debug(f"✅ Fetched {len(html)} bytes")
                    return html
                else:
                    self._consecutive_errors += 1
                    logger.error(f"❌ HTTP {response.status} for {url}")
                    return None
                    
        except asyncio.TimeoutError:
            self._consecutive_errors += 1
            logger.error(f"⏰ Timeout fetching {url}")
            return None
        except Exception as e:
            self._consecutive_errors += 1
            logger.error(f"❌ Error fetching {url}: {e}")
            return None
    
    def _parse_number(self, text: str) -> Optional[float]:
        """Parse a number from text, handling Vietnamese formatting."""
        if not text:
            return None
        
        # Remove non-numeric characters except . and -
        text = text.strip().replace(',', '').replace(' ', '')
        
        # Handle percentage
        if '%' in text:
            text = text.replace('%', '')
            
        # Handle billion/million suffixes
        multiplier = 1
        if text.endswith('B') or text.endswith('tỷ'):
            multiplier = 1_000_000_000
            text = text[:-1] if text[-1] == 'B' else text.replace('tỷ', '')
        elif text.endswith('M') or text.endswith('tr'):
            multiplier = 1_000_000
            text = text[:-1] if text[-1] == 'M' else text.replace('tr', '')
            
        try:
            return float(text) * multiplier
        except (ValueError, TypeError):
            return None
    
    def _parse_market_table(self, html: str, vt_type: int) -> List[Dict[str, Any]]:
        """
        Parse the market table from HTML.
        
        vt=1: Giá, KLGD, Vốn Thị Trường, NN sở hữu
        vt=2: P/B, EPS, PE, PS, ROA, ROE
        vt=3: Nợ, Vốn CSH, Tổng TS, Tiền mặt
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find the main data table
        table = soup.find('table', {'id': 'dataTable'}) or soup.find('table', class_='dataTable')
        
        if not table:
            # Try to find any table with stock data
            tables = soup.find_all('table')
            for t in tables:
                if t.find('a', href=lambda x: x and 'quote/summary.php' in x):
                    table = t
                    break
        
        if not table:
            logger.warning(f"⚠️ Could not find data table for vt={vt_type}")
            return results
        
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 2:
                continue
            
            # Find the stock symbol link
            symbol_link = row.find('a', href=lambda x: x and 'quote/summary.php' in x)
            if not symbol_link:
                continue
            
            # Extract symbol from link
            href = symbol_link.get('href', '')
            symbol_match = re.search(r'id=([A-Za-z0-9]+)', href)
            if not symbol_match:
                continue
            
            symbol = symbol_match.group(1).upper()
            company_name = symbol_link.get_text(strip=True)
            
            # Parse based on vt type
            stock_data = {
                'symbol': symbol,
                'company_name': company_name.split('\n')[0].strip() if company_name else None,
            }
            
            # Get all cell values
            cell_values = [c.get_text(strip=True) for c in cells]
            
            try:
                if vt_type == 1:
                    # vt=1: Mã, Tên, Giá, KLGD, KL52w, KLNiêmYết, VốnTT, NN%
                    if len(cell_values) >= 7:
                        stock_data['current_price'] = self._parse_number(cell_values[2]) if len(cell_values) > 2 else None
                        stock_data['volume'] = self._parse_number(cell_values[3]) if len(cell_values) > 3 else None
                        stock_data['avg_volume_52w'] = self._parse_number(cell_values[4]) if len(cell_values) > 4 else None
                        stock_data['listed_shares'] = self._parse_number(cell_values[5]) if len(cell_values) > 5 else None
                        stock_data['market_cap'] = self._parse_number(cell_values[6]) if len(cell_values) > 6 else None
                        stock_data['foreign_ownership'] = self._parse_number(cell_values[7]) if len(cell_values) > 7 else None
                        
                elif vt_type == 2:
                    # vt=2: Mã, Tên, Giá, GiáSổSách, P/B, EPS, PE, PS, ROA, ROE
                    if len(cell_values) >= 8:
                        stock_data['current_price'] = self._parse_number(cell_values[2]) if len(cell_values) > 2 else None
                        stock_data['book_value'] = self._parse_number(cell_values[3]) if len(cell_values) > 3 else None
                        stock_data['pb_ratio'] = self._parse_number(cell_values[4]) if len(cell_values) > 4 else None
                        stock_data['eps'] = self._parse_number(cell_values[5]) if len(cell_values) > 5 else None
                        stock_data['pe_ratio'] = self._parse_number(cell_values[6]) if len(cell_values) > 6 else None
                        stock_data['ps_ratio'] = self._parse_number(cell_values[7]) if len(cell_values) > 7 else None
                        stock_data['roa'] = self._parse_number(cell_values[8]) if len(cell_values) > 8 else None
                        stock_data['roe'] = self._parse_number(cell_values[9]) if len(cell_values) > 9 else None
                        
                elif vt_type == 3:
                    # vt=3: Mã, Tên, Giá, Nợ, VốnCSH, TổngTS, %Nợ/CSH, %CSH/TS, TiềnMặt
                    if len(cell_values) >= 7:
                        stock_data['current_price'] = self._parse_number(cell_values[2]) if len(cell_values) > 2 else None
                        stock_data['total_debt'] = self._parse_number(cell_values[3]) if len(cell_values) > 3 else None
                        stock_data['owner_equity'] = self._parse_number(cell_values[4]) if len(cell_values) > 4 else None
                        stock_data['total_assets'] = self._parse_number(cell_values[5]) if len(cell_values) > 5 else None
                        stock_data['debt_to_equity'] = self._parse_number(cell_values[6]) if len(cell_values) > 6 else None
                        stock_data['equity_to_assets'] = self._parse_number(cell_values[7]) if len(cell_values) > 7 else None
                        stock_data['cash'] = self._parse_number(cell_values[8]) if len(cell_values) > 8 else None
                        
            except Exception as e:
                logger.debug(f"Error parsing row for {symbol}: {e}")
            
            if stock_data.get('symbol'):
                results.append(stock_data)
        
        logger.info(f"📊 Parsed {len(results)} stocks from vt={vt_type}")
        return results
    
    async def collect_market_data(self, vt_type: int = 1, max_pages: int = 20) -> List[Dict[str, Any]]:
        """
        Collect all stocks from a specific market view with pagination.
        
        Args:
            vt_type: 1=listings, 2=financials, 3=balance sheet
            max_pages: Maximum pages to scrape (safety limit)
        """
        all_stocks = []
        page = 1
        
        while page <= max_pages:
            url = f"{self.BASE_URL}/market/markets.php?vt={vt_type}&cP={page}"
            
            html = await self._fetch_page(url)
            if not html:
                break
            
            stocks = self._parse_market_table(html, vt_type)
            
            if not stocks:
                logger.info(f"📄 No more data on page {page}")
                break
            
            all_stocks.extend(stocks)
            logger.info(f"📄 Page {page}: {len(stocks)} stocks (total: {len(all_stocks)})")
            
            # Check for next page link
            soup = BeautifulSoup(html, 'html.parser')
            next_link = soup.find('a', text=re.compile(r'>>|Next|Tiếp'))
            if not next_link:
                break
            
            page += 1
        
        return all_stocks
    
    async def collect_all_stocks_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Collect and merge data from all vt views into a single dict by symbol.
        This is the main method to get complete stock data.
        """
        logger.info("🚀 Starting full data collection (this will take several minutes)...")
        
        merged_data: Dict[str, Dict[str, Any]] = {}
        
        # Collect vt=1 (listings, market cap)
        logger.info("📊 Collecting vt=1 (listings, market cap)...")
        vt1_data = await self.collect_market_data(vt_type=1)
        for stock in vt1_data:
            symbol = stock.get('symbol')
            if symbol:
                merged_data[symbol] = stock
        
        # Collect vt=2 (financial ratios) - very politely
        logger.info("📊 Collecting vt=2 (financial ratios)...")
        await asyncio.sleep(5)  # Extra pause between different data types
        vt2_data = await self.collect_market_data(vt_type=2)
        for stock in vt2_data:
            symbol = stock.get('symbol')
            if symbol:
                if symbol in merged_data:
                    merged_data[symbol].update(stock)
                else:
                    merged_data[symbol] = stock
        
        # Collect vt=3 (balance sheet) - very politely
        logger.info("📊 Collecting vt=3 (balance sheet)...")
        await asyncio.sleep(5)  # Extra pause
        vt3_data = await self.collect_market_data(vt_type=3)
        for stock in vt3_data:
            symbol = stock.get('symbol')
            if symbol:
                if symbol in merged_data:
                    merged_data[symbol].update(stock)
                else:
                    merged_data[symbol] = stock
        
        # Add timestamp
        for symbol in merged_data:
            merged_data[symbol]['updated_at'] = datetime.now().isoformat()
        
        logger.info(f"🎉 Collection complete: {len(merged_data)} stocks with merged data")
        return merged_data
    
    async def collect_daily_prices(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect daily OHLCV data from historydaily.php.
        
        Args:
            date: Date in YYYY-MM-DD format. Defaults to today.
        """
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/download/historydaily.php?d={date}"
        
        html = await self._fetch_page(url)
        if not html:
            return []
        
        # Parse the page for download link or data
        # Note: This page may require different parsing based on actual format
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for download link or data table
        # TODO: Implement based on actual page structure
        
        logger.info(f"📅 Parsed daily prices for {date}")
        return []
    
    async def test(self):
        """Test the collector with a small sample."""
        logger.info("🧪 Running collector test...")
        
        try:
            # Test single page fetch
            html = await self._fetch_page(f"{self.BASE_URL}/market/markets.php?vt=1")
            if html:
                stocks = self._parse_market_table(html, 1)
                logger.info(f"✅ Test successful: parsed {len(stocks)} stocks")
                if stocks:
                    logger.info(f"Sample: {stocks[0]}")
            else:
                logger.error("❌ Test failed: could not fetch page")
        finally:
            await self.close()


# Utility function to run the collector
async def run_collection():
    """Run a full data collection."""
    collector = Cophieu68Collector()
    try:
        data = await collector.collect_all_stocks_data()
        
        # Save to JSON for inspection
        output_path = Path(__file__).parent / "data" / "cophieu68_data.json"
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Saved data to {output_path}")
        return data
        
    finally:
        await collector.close()


if __name__ == "__main__":
    # Run test when executed directly
    asyncio.run(Cophieu68Collector().test())
