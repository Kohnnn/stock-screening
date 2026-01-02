"""
Comprehensive data collection script for VnStock Screener.

Collects all available data from vnstock library:
- Stock listings (1700+ symbols)
- Price history (last 30 days for top stocks)
- Company overview and sectors

Runs with rate limiting to avoid API blocks.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd

# Suppress vnstock upgrade messages
import warnings
warnings.filterwarnings('ignore')

# vnstock imports
from vnstock import Vnstock, Listing

# Local imports
from config import settings
from database import Database
from rate_limiter import get_rate_limiter
from circuit_breaker import get_circuit_breaker


class DataCollector:
    """Comprehensive data collector with rate limiting."""
    
    def __init__(self):
        self.vnstock = Vnstock()
        self.listing = Listing()
        self.rate_limiter = get_rate_limiter(requests_per_minute=settings.VNSTOCK_RATE_LIMIT)
        self.circuit_breaker = get_circuit_breaker()
        self.db = None
        
        # Statistics
        self.stats = {
            'listings_collected': 0,
            'prices_collected': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None,
        }
    
    async def initialize(self):
        """Initialize database connection."""
        self.db = Database()
        await self.db.initialize()
        print(f"[OK] Database initialized: {settings.DATABASE_PATH}")
    
    async def rate_limited_call(self, func, *args, **kwargs):
        """Execute API call with rate limiting."""
        await self.rate_limiter.acquire()
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: func(*args, **kwargs)
            )
            await self.rate_limiter.on_success()
            return result
        except Exception as e:
            await self.rate_limiter.on_failure()
            self.stats['errors'] += 1
            raise
    
    async def collect_all_listings(self) -> List[Dict]:
        """Collect all stock listings."""
        print("\n[1/3] Collecting stock listings...")
        
        try:
            df = await self.rate_limited_call(self.listing.all_symbols)
            
            if df is None or df.empty:
                print("[WARN] No listings returned")
                return []
            
            print(f"[OK] Found {len(df)} symbols")
            print(f"[INFO] Columns: {list(df.columns)}")
            
            # Convert to list of dicts
            stocks = []
            for _, row in df.iterrows():
                stock = {
                    'symbol': str(row.get('symbol', '')).upper(),
                    'company_name': row.get('organ_name', ''),
                    'exchange': None,
                    'sector': None,
                    'industry': None,
                }
                stocks.append(stock)
            
            # Save to database
            await self.db.upsert_stocks(stocks)
            self.stats['listings_collected'] = len(stocks)
            print(f"[OK] Saved {len(stocks)} stocks to database")
            
            return stocks
            
        except Exception as e:
            print(f"[ERROR] Listings collection failed: {e}")
            return []
    
    async def collect_stock_prices(self, symbols: List[str], days: int = 30) -> int:
        """Collect price history for given symbols."""
        print(f"\n[2/3] Collecting prices for {len(symbols)} stocks (last {days} days)...")
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        collected = 0
        failed = 0
        
        for i, symbol in enumerate(symbols):
            # Check circuit breaker
            if self.circuit_breaker.is_open:
                print(f"[WARN] Circuit breaker open, stopping at {i}/{len(symbols)}")
                break
            
            try:
                stock = self.vnstock.stock(symbol=symbol, source='VCI')
                df = await self.rate_limited_call(
                    stock.quote.history,
                    start=start_date,
                    end=end_date
                )
                
                if df is not None and not df.empty:
                    # Get latest price for stock_prices table
                    latest = df.iloc[-1]
                    price_data = {
                        'symbol': symbol,
                        'current_price': float(latest.get('close', 0)),
                        'open_price': float(latest.get('open', 0)),
                        'high_price': float(latest.get('high', 0)),
                        'low_price': float(latest.get('low', 0)),
                        'close_price': float(latest.get('close', 0)),
                        'volume': int(latest.get('volume', 0)),
                    }
                    await self.db.upsert_stock_prices([price_data])
                    
                    # Save full history
                    history = []
                    for _, row in df.iterrows():
                        history.append({
                            'symbol': symbol,
                            'date': str(row.get('time', '')),
                            'open_price': float(row.get('open', 0)),
                            'high_price': float(row.get('high', 0)),
                            'low_price': float(row.get('low', 0)),
                            'close_price': float(row.get('close', 0)),
                            'volume': int(row.get('volume', 0)),
                            'adjusted_close': float(row.get('close', 0)),
                        })
                    await self.db.upsert_price_history(history)
                    
                    collected += 1
                    print(f"  [{i+1}/{len(symbols)}] {symbol}: {len(history)} days, close={price_data['current_price']}")
                else:
                    failed += 1
                    print(f"  [{i+1}/{len(symbols)}] {symbol}: No data")
                    
            except Exception as e:
                failed += 1
                print(f"  [{i+1}/{len(symbols)}] {symbol}: ERROR - {str(e)[:50]}")
            
            # Progress every 10 stocks
            if (i + 1) % 10 == 0:
                progress = (i + 1) / len(symbols) * 100
                print(f"[INFO] Progress: {i+1}/{len(symbols)} ({progress:.1f}%)")
        
        self.stats['prices_collected'] = collected
        print(f"[OK] Collected prices for {collected}/{len(symbols)} stocks ({failed} failed)")
        return collected

    async def collect_company_details(self, symbols: List[str]) -> int:
        """Collect company overview for given symbols."""
        print(f"\n[3/3] Collecting company details for {len(symbols)} stocks...")
        
        collected = 0
        failed = 0
        
        for i, symbol in enumerate(symbols):
            if self.circuit_breaker.is_open:
                print(f"[WARN] Circuit breaker open, stopping")
                break
            
            try:
                stock = self.vnstock.stock(symbol=symbol, source='VCI')
                overview = await self.rate_limited_call(stock.company.overview)
                
                if overview is not None and not overview.empty:
                    row = overview.iloc[0]
                    update_data = {
                        'symbol': symbol,
                        'sector': row.get('icb_name2', ''),
                        'industry': row.get('icb_name3', ''),
                    }
                    
                    # Update stock with sector/industry
                    await self.db.upsert_stocks([update_data])
                    collected += 1
                    
                    if (i + 1) % 5 == 0:
                        print(f"  [{i+1}/{len(symbols)}] Collected {collected} company details")
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
        
        print(f"[OK] Collected details for {collected}/{len(symbols)} stocks")
        return collected

    async def run_full_collection(self, price_limit: int = 50, detail_limit: int = 30):
        """Run comprehensive data collection."""
        self.stats['start_time'] = datetime.now()
        
        print("=" * 60)
        print("VnStock Data Collection")
        print(f"Started: {self.stats['start_time']}")
        print(f"Rate limit: {settings.VNSTOCK_RATE_LIMIT} requests/minute")
        print("=" * 60)
        
        # Initialize
        await self.initialize()
        
        # Step 1: Collect all listings
        stocks = await self.collect_all_listings()
        
        if not stocks:
            print("[ERROR] No stocks to process")
            return
        
        # Get top symbols (use first N for testing)
        symbols = [s['symbol'] for s in stocks[:price_limit]]
        
        # Step 2: Collect prices for top stocks
        await self.collect_stock_prices(symbols, days=30)
        
        # Step 3: Collect company details for subset
        detail_symbols = symbols[:detail_limit]
        await self.collect_company_details(detail_symbols)
        
        # Final stats
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("Collection Complete!")
        print(f"Duration: {duration:.1f} seconds")
        print(f"Listings: {self.stats['listings_collected']}")
        print(f"Prices: {self.stats['prices_collected']}")
        print(f"Errors: {self.stats['errors']}")
        print("=" * 60)
        
        # Show database stats
        db_stats = await self.db.get_database_stats()
        print(f"\nDatabase Status:")
        print(f"  Stocks: {db_stats.get('stocks_count', 0)}")
        print(f"  Prices: {db_stats.get('stock_prices_count', 0)}")
        print(f"  History: {db_stats.get('price_history_count', 0)}")


async def main():
    """Main entry point."""
    collector = DataCollector()
    
    # Run collection with limits to avoid hitting API too hard
    # price_limit: how many stocks to get prices for
    # detail_limit: how many stocks to get company details for
    await collector.run_full_collection(
        price_limit=100,   # Top 100 stocks for prices
        detail_limit=50,   # Top 50 for company details
    )


if __name__ == "__main__":
    asyncio.run(main())
