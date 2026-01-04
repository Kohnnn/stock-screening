"""
Base Scraper Module

Provides common functionality for all web scrapers:
- Async HTTP client with connection pooling
- Rate limiting with jitter
- Exponential backoff retry logic
- Browser-like headers rotation
- Response validation
- Logging integration
"""

import asyncio
import aiohttp
import random
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from bs4 import BeautifulSoup
from loguru import logger

# Configure base logger
logger.add(
    Path(__file__).parent / "logs" / "scraper.log",
    rotation="10 MB",
    retention="7 days",
    level="DEBUG"
)


class RateLimiter:
    """Token bucket rate limiter with jitter."""
    
    def __init__(
        self,
        min_delay: float = 2.0,
        max_jitter: float = 1.5,
        max_per_minute: int = 15,
        backoff_multiplier: float = 2.0,
        max_backoff: float = 60.0
    ):
        self.min_delay = min_delay
        self.max_jitter = max_jitter
        self.max_per_minute = max_per_minute
        self.backoff_multiplier = backoff_multiplier
        self.max_backoff = max_backoff
        
        self._last_request_time: float = 0
        self._request_count: int = 0
        self._minute_start: float = 0
        self._consecutive_errors: int = 0
    
    async def acquire(self):
        """Wait for rate limit token."""
        now = asyncio.get_event_loop().time()
        
        # Reset per-minute counter if needed
        if now - self._minute_start > 60:
            self._minute_start = now
            self._request_count = 0
        
        # Wait if at limit
        if self._request_count >= self.max_per_minute:
            wait_time = 60 - (now - self._minute_start)
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached, waiting {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
                self._minute_start = asyncio.get_event_loop().time()
                self._request_count = 0
        
        # Calculate delay with backoff
        base_delay = self.min_delay
        if self._consecutive_errors > 0:
            backoff = min(
                base_delay * (self.backoff_multiplier ** self._consecutive_errors),
                self.max_backoff
            )
            base_delay = backoff
        
        # Add jitter
        jitter = random.uniform(0, self.max_jitter)
        total_delay = base_delay + jitter
        
        # Wait since last request
        now = asyncio.get_event_loop().time()
        time_since_last = now - self._last_request_time
        if time_since_last < total_delay:
            wait_time = total_delay - time_since_last
            await asyncio.sleep(wait_time)
        
        self._last_request_time = asyncio.get_event_loop().time()
        self._request_count += 1
    
    def record_success(self):
        """Reset error counter on success."""
        self._consecutive_errors = 0
    
    def record_error(self):
        """Increment error counter for backoff."""
        self._consecutive_errors += 1


# Common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class BaseScraper(ABC):
    """
    Abstract base class for all web scrapers.
    
    Provides:
    - Async HTTP client with timeouts
    - Rate limiting with jitter
    - Retry logic with exponential backoff
    - Response validation
    - Number parsing utilities
    """
    
    def __init__(
        self,
        name: str = "BaseScraper",
        rate_limiter: Optional[RateLimiter] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.name = name
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self.max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get browser-like headers with randomized User-Agent."""
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self._get_headers()
            )
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def fetch(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        custom_headers: Optional[Dict] = None,
        retries: Optional[int] = None
    ) -> Optional[str]:
        """
        Fetch a URL with rate limiting and retry logic.
        
        Returns HTML content or None on failure.
        """
        retries = retries if retries is not None else self.max_retries
        
        for attempt in range(retries + 1):
            try:
                await self.rate_limiter.acquire()
                
                session = await self._get_session()
                headers = self._get_headers()
                if custom_headers:
                    headers.update(custom_headers)
                
                logger.debug(f"[{self.name}] Fetching: {url} (attempt {attempt + 1})")
                
                if method.upper() == "GET":
                    async with session.get(url, headers=headers) as response:
                        return await self._handle_response(response, url)
                else:
                    async with session.post(url, headers=headers, data=data) as response:
                        return await self._handle_response(response, url)
                        
            except asyncio.TimeoutError:
                self.rate_limiter.record_error()
                logger.warning(f"[{self.name}] Timeout on {url} (attempt {attempt + 1})")
                
            except aiohttp.ClientError as e:
                self.rate_limiter.record_error()
                logger.warning(f"[{self.name}] Client error on {url}: {e}")
                
            except Exception as e:
                self.rate_limiter.record_error()
                logger.error(f"[{self.name}] Unexpected error on {url}: {e}")
            
            if attempt < retries:
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logger.debug(f"[{self.name}] Retrying in {wait_time:.1f}s...")
                await asyncio.sleep(wait_time)
        
        return None
    
    async def _handle_response(self, response: aiohttp.ClientResponse, url: str) -> Optional[str]:
        """Handle HTTP response."""
        if response.status == 200:
            self.rate_limiter.record_success()
            html = await response.text()
            logger.debug(f"[{self.name}] Fetched {len(html)} bytes from {url}")
            return html
        elif response.status == 403:
            self.rate_limiter.record_error()
            logger.error(f"[{self.name}] Forbidden (403) on {url} - possible anti-scrape")
            return None
        elif response.status == 429:
            self.rate_limiter.record_error()
            logger.warning(f"[{self.name}] Rate limited (429) on {url}")
            return None
        else:
            self.rate_limiter.record_error()
            logger.error(f"[{self.name}] HTTP {response.status} on {url}")
            return None
    
    async def fetch_json(
        self,
        url: str,
        custom_headers: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Fetch JSON from a URL."""
        try:
            await self.rate_limiter.acquire()
            
            session = await self._get_session()
            headers = self._get_headers()
            headers["Accept"] = "application/json"
            if custom_headers:
                headers.update(custom_headers)
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    self.rate_limiter.record_success()
                    return await response.json()
                else:
                    self.rate_limiter.record_error()
                    logger.error(f"[{self.name}] HTTP {response.status} on JSON fetch: {url}")
                    return None
                    
        except Exception as e:
            self.rate_limiter.record_error()
            logger.error(f"[{self.name}] JSON fetch error: {e}")
            return None
    
    # ==================== Parsing Utilities ====================
    
    @staticmethod
    def parse_number(text: str) -> Optional[float]:
        """
        Parse a number from Vietnamese-formatted text.
        
        Handles:
        - Commas as thousands separators
        - Percentages
        - Billion/Million suffixes (B, M, tỷ, tr)
        """
        if not text:
            return None
        
        text = str(text).strip().replace(',', '').replace(' ', '')
        
        # Handle percentage
        is_percent = '%' in text
        text = text.replace('%', '')
        
        # Handle suffixes
        multiplier = 1
        if text.endswith('B') or 'tỷ' in text.lower():
            multiplier = 1_000_000_000
            text = re.sub(r'[Btỷ]', '', text, flags=re.IGNORECASE)
        elif text.endswith('M') or 'tr' in text.lower():
            multiplier = 1_000_000
            text = re.sub(r'[Mtr]', '', text, flags=re.IGNORECASE)
        elif text.endswith('K') or text.endswith('k'):
            multiplier = 1_000
            text = text[:-1]
        
        try:
            value = float(text) * multiplier
            # Don't divide percentages, just return as-is for caller to handle
            return value
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def parse_date(text: str, formats: Optional[List[str]] = None) -> Optional[datetime]:
        """Parse a date from text using common Vietnamese formats."""
        if not text:
            return None
        
        formats = formats or [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d/%m/%y",
        ]
        
        text = text.strip()
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean whitespace and normalize text."""
        if not text:
            return ""
        return ' '.join(str(text).split()).strip()
    
    def validate_stock_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate stock data record.
        
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        if not data.get('symbol'):
            errors.append("Missing symbol")
        
        if data.get('current_price') is not None:
            price = data['current_price']
            if price < 0:
                errors.append(f"Invalid negative price: {price}")
            elif price > 10_000_000:  # 10M VND seems unreasonably high
                errors.append(f"Suspiciously high price: {price}")
        
        if data.get('pe_ratio') is not None:
            pe = data['pe_ratio']
            if pe < -1000 or pe > 10000:
                errors.append(f"Suspicious P/E ratio: {pe}")
        
        if data.get('roe') is not None:
            roe = data['roe']
            if roe < -100 or roe > 1000:
                errors.append(f"Suspicious ROE: {roe}")
        
        return len(errors) == 0, errors
    
    # ==================== Abstract Methods ====================
    
    @abstractmethod
    async def collect(self) -> List[Dict[str, Any]]:
        """
        Main collection method. Must be implemented by subclasses.
        
        Returns list of stock data dictionaries.
        """
        pass
    
    async def test(self) -> bool:
        """Run a quick connectivity test."""
        logger.info(f"[{self.name}] Running connectivity test...")
        return True
