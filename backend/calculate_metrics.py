"""
Calculate Technical Metrics for All Stocks.

Runs through stocks with price history and calculates all technical indicators.
"""

import asyncio
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

from loguru import logger
from database import Database
from technical_indicators import calculate_all_indicators


async def calculate_metrics():
    """Calculate technical metrics for all stocks with price history."""
    print("=" * 60)
    print("Technical Metrics Calculation")
    print(f"Started: {datetime.now()}")
    print("=" * 60)
    
    db = Database()
    await db.initialize()
    
    # Get stocks with price history
    async with db.connection() as conn:
        cursor = await conn.execute("""
            SELECT DISTINCT symbol 
            FROM price_history 
            GROUP BY symbol 
            HAVING COUNT(*) >= 20
        """)
        symbols = [row['symbol'] for row in await cursor.fetchall()]
    
    print(f"\nCalculating metrics for {len(symbols)} stocks...\n")
    
    calculated = 0
    failed = 0
    batch = []
    batch_size = 50
    
    for i, symbol in enumerate(symbols):
        try:
            # Get price history (oldest first for proper calculation)
            history = await db.get_price_history(symbol, days=250)
            
            if not history or len(history) < 14:
                continue
            
            # Reverse to get oldest first
            history = list(reversed(history))
            
            # Calculate all indicators
            metrics = calculate_all_indicators(history)
            
            if metrics:
                metrics['symbol'] = symbol
                batch.append(metrics)
                calculated += 1
            
            # Save in batches
            if len(batch) >= batch_size:
                await db.upsert_stock_metrics(batch)
                print(f"  [{i+1}/{len(symbols)}] Saved {len(batch)} metrics")
                batch = []
            
        except Exception as e:
            failed += 1
            logger.debug(f"Error calculating metrics for {symbol}: {e}")
        
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i + 1}/{len(symbols)}")
    
    # Save remaining batch
    if batch:
        await db.upsert_stock_metrics(batch)
        print(f"  Saved final {len(batch)} metrics")
    
    print("\n" + "=" * 60)
    print("Metrics Calculation Complete!")
    print(f"Calculated: {calculated}")
    print(f"Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(calculate_metrics())
