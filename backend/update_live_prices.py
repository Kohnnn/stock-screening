
"""
Live Price Updater using SSI iBoard API.
Updates current_price and percent_change for all stocks.
Run this during/after market hours to get fresh data for highlights.
"""

import asyncio
from datetime import datetime
from loguru import logger
from database import Database
from ssi_iboard_collector import SSIiBoardCollector

async def update_live_prices():
    """Fetch live prices from SSI iBoard and update stock_prices table."""
    logger.info("🚀 Starting live price update from SSI iBoard...")
    
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    collector = SSIiBoardCollector()
    
    try:
        # Get all markets
        all_markets = await collector.get_all_markets()
        
        updates = []
        for group, stocks in all_markets.items():
            logger.info(f"📊 Processing {group}: {len(stocks)} stocks")
            
            for stock_data in stocks:
                if stock_data.get('symbol'):
                    updates.append({
                        'symbol': stock_data['symbol'],
                        'current_price': stock_data.get('current_price') or 0,
                        'price_change': stock_data.get('price_change') or 0,
                        'percent_change': stock_data.get('percent_change') or 0,
                        'volume': stock_data.get('volume') or 0,
                        'open_price': stock_data.get('open_price') or 0,
                        'high_price': stock_data.get('high_price') or 0,
                        'low_price': stock_data.get('low_price') or 0,
                        'close_price': stock_data.get('close_price') or 0,
                    })
        
        # Bulk update
        if updates:
            async with db.connection() as conn:
                for batch_start in range(0, len(updates), 100):
                    batch = updates[batch_start:batch_start+100]
                    for data in batch:
                        await conn.execute("""
                            UPDATE stock_prices SET
                                current_price = ?,
                                price_change = ?,
                                percent_change = ?,
                                volume = ?,
                                open_price = ?,
                                high_price = ?,
                                low_price = ?,
                                close_price = ?,
                                updated_at = ?
                            WHERE symbol = ?
                        """, (
                            data['current_price'],
                            data['price_change'],
                            data['percent_change'],
                            data['volume'],
                            data['open_price'],
                            data['high_price'],
                            data['low_price'],
                            data['close_price'],
                            datetime.now().isoformat(),
                            data['symbol']
                        ))
                    await conn.commit()
                    logger.info(f"📥 Updated batch: {batch_start} to {min(batch_start+100, len(updates))}")
            
            logger.info(f"✅ Updated {len(updates)} stock prices with live data!")
        else:
            logger.warning("⚠️ No price data received from SSI")
            
    except Exception as e:
        logger.error(f"❌ Error updating prices: {e}")
    finally:
        await collector.close()

    # Check results
    async with db.connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change > 0")
        positive = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change < 0")
        negative = (await cursor.fetchone())[0]
        logger.info(f"📈 Stocks with positive change: {positive}")
        logger.info(f"📉 Stocks with negative change: {negative}")

if __name__ == "__main__":
    asyncio.run(update_live_prices())
