"""
Quick script to collect VN30 stock data (highest priority).
Run this to populate price history for the major stocks.
"""

import asyncio
from datetime import datetime, timedelta

# Suppress vnstock upgrade messages
import warnings
warnings.filterwarnings('ignore')

from vnstock import Vnstock
from config import settings
from database import Database
from rate_limiter import get_rate_limiter

# VN30 symbols
VN30_SYMBOLS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]


async def collect_vn30():
    """Collect price data for VN30 stocks."""
    print("=" * 60)
    print("VN30 Data Collection")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    # Initialize
    db = Database()
    await db.initialize()
    
    vnstock = Vnstock()
    rate_limiter = get_rate_limiter(requests_per_minute=settings.VNSTOCK_RATE_LIMIT)
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
    
    collected = 0
    failed = 0
    
    print(f"\nCollecting {len(VN30_SYMBOLS)} VN30 stocks...")
    print(f"Date range: {start_date} to {end_date}\n")
    
    for i, symbol in enumerate(VN30_SYMBOLS):
        try:
            # Rate limit
            await rate_limiter.acquire()
            
            # Get price history
            stock = vnstock.stock(symbol=symbol, source='VCI')
            df = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: stock.quote.history(start=start_date, end=end_date)
            )
            
            if df is not None and not df.empty:
                # Save current price
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
                await db.upsert_stock_prices([price_data])
                
                # Save price history
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
                await db.upsert_price_history(history)
                
                collected += 1
                print(f"  [{i+1}/{len(VN30_SYMBOLS)}] {symbol}: {len(history)} days, close={price_data['current_price']}")
            else:
                failed += 1
                print(f"  [{i+1}/{len(VN30_SYMBOLS)}] {symbol}: No data")
                
        except Exception as e:
            failed += 1
            print(f"  [{i+1}/{len(VN30_SYMBOLS)}] {symbol}: ERROR - {str(e)[:50]}")
    
    print("\n" + "=" * 60)
    print("VN30 Collection Complete!")
    print(f"Collected: {collected}/{len(VN30_SYMBOLS)}")
    print(f"Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(collect_vn30())
