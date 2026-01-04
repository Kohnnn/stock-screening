
"""
Update stock prices using vnstock API (works anytime, not just market hours).
This fetches the latest day's data for all stocks and updates percent_change.
"""

import asyncio
from datetime import datetime, timedelta
from loguru import logger
from database import Database
from vnstock import Vnstock

# Top stocks to update (VN30 + key stocks)
PRIORITY_SYMBOLS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    "DPM", "DHG", "PVS", "PVI", "SBT", "VCG", "IDC", "LGC", "VGC", "REE"
]

async def update_prices_vnstock():
    """Update prices using vnstock for priority symbols."""
    logger.info("🚀 Starting price update using vnstock...")
    
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    vn = Vnstock()
    
    updated = 0
    failed = 0
    
    for symbol in PRIORITY_SYMBOLS:
        try:
            # Get last 2 days of data to calculate change
            stock = vn.stock(symbol=symbol, source='VCI')
            # Use sync call - vnstock 3.x doesn't have async quote.history()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(stock.quote.history, days=5)
                df = future.result(timeout=30)
            
            if df is not None and len(df) >= 2:
                latest = df.iloc[-1]
                previous = df.iloc[-2]
                
                current_price = float(latest.get('close', 0))
                prev_close = float(previous.get('close', 0))
                
                if prev_close > 0:
                    price_change = current_price - prev_close
                    percent_change = (price_change / prev_close) * 100
                else:
                    price_change = 0
                    percent_change = 0
                
                async with db.connection() as conn:
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
                        current_price,
                        price_change,
                        round(percent_change, 2),
                        int(latest.get('volume', 0)),
                        float(latest.get('open', 0)),
                        float(latest.get('high', 0)),
                        float(latest.get('low', 0)),
                        current_price,
                        datetime.now().isoformat(),
                        symbol
                    ))
                    await conn.commit()
                
                updated += 1
                logger.info(f"✅ {symbol}: {current_price} ({percent_change:+.2f}%)")
            else:
                failed += 1
                logger.warning(f"⚠️ {symbol}: No data")
                
        except Exception as e:
            failed += 1
            logger.error(f"❌ {symbol}: {e}")
        
        # Rate limit
        await asyncio.sleep(0.5)
    
    logger.info(f"\n🏁 Complete! Updated: {updated}, Failed: {failed}")
    
    # Check results
    async with db.connection() as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change > 0")
        positive = (await cursor.fetchone())[0]
        cursor = await conn.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change < 0")
        negative = (await cursor.fetchone())[0]
        logger.info(f"📈 Stocks with positive change: {positive}")
        logger.info(f"📉 Stocks with negative change: {negative}")

if __name__ == "__main__":
    asyncio.run(update_prices_vnstock())
