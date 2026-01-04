
import asyncio
from database import Database
from vnstock import Vnstock
from loguru import logger
import time

async def backfill_sectors_full():
    """
    Robust full backfill for sectors using VCI source.
    """
    logger.add("sector_backfill_full.log")
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    # Get all stocks
    async with db.connection() as conn:
        async with conn.execute("SELECT symbol FROM stocks ORDER BY symbol") as cursor:
            rows = await cursor.fetchall()
            symbols = [row[0] for row in rows]
    
    logger.info(f"Starting full sector backfill for {len(symbols)} stocks...")
    
    vn = Vnstock()
    updates = []
    
    for i, symbol in enumerate(symbols):
        try:
            # Fetch company overview
            # Use sync call in async loop (blocking but fine for script)
            stock = vn.stock(symbol=symbol, source='VCI')
            overview = stock.company.overview()
            
            if overview is not None and not overview.empty:
                row = overview.iloc[0]
                sector = row.get('icb_name2') or row.get('industry') or row.get('sector')
                
                if sector:
                    updates.append((sector, symbol))
                    logger.info(f"[{i+1}/{len(symbols)}] {symbol}: {sector}")
                else:
                    logger.warning(f"[{i+1}/{len(symbols)}] {symbol}: No sector found")
            else:
                 logger.warning(f"[{i+1}/{len(symbols)}] {symbol}: No overview data")
                 
        except Exception as e:
            logger.error(f"[{i+1}/{len(symbols)}] {symbol} Error: {e}")
            
        # Batch update every 20
        if len(updates) >= 20:
            async with db.connection() as conn:
                await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
                await conn.commit()
            logger.info(f"🔄 Flushed {len(updates)} sector updates")
            updates = []
            await asyncio.sleep(0.5) # Slight pause to be nice to API
            
        # Rate limit
        time.sleep(0.1) 

    # Final flush
    if updates:
        async with db.connection() as conn:
            await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
            await conn.commit()
        logger.info(f"🔄 Final flush of {len(updates)} updates")

if __name__ == "__main__":
    asyncio.run(backfill_sectors_full())
