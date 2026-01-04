
import asyncio
from database import Database
from vnstock import Vnstock
from loguru import logger

async def backfill_sectors_deep():
    """
    Backfill sectors by fetching company overview for each stock individually.
    This is slow but reliable if listing() doesn't return sector info.
    """
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    # Get all stocks that have missing sector
    async with db.connection() as conn:
        async with conn.execute("SELECT symbol FROM stocks") as cursor:
            rows = await cursor.fetchall()
            symbols = [row[0] for row in rows]
    
    logger.info(f"Found {len(symbols)} stocks with missing sector.")
    
    vn = Vnstock()
    
    chunk_size = 10
    updates = []
    
    for i, symbol in enumerate(symbols):
        try:
            # Fetch company overview
            stock = vn.stock(symbol=symbol, source='VCI')
            overview_df = stock.company.overview()
            
            if overview_df is not None and not overview_df.empty:
                row = overview_df.iloc[0]
                sector = row.get('icb_name2') or row.get('industry') or row.get('sector')
                
                if sector:
                    updates.append((sector, symbol))
                    logger.info(f"[{i+1}/{len(symbols)}] Found sector for {symbol}: {sector}")
                else:
                    logger.warning(f"[{i+1}/{len(symbols)}] No sector in overview for {symbol}")
            else:
                 logger.warning(f"[{i+1}/{len(symbols)}] No overview data for {symbol}")
                 
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {e}")
            
        # Batch update every 20 or at end
        if len(updates) >= 20:
            async with db.connection() as conn:
                await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
                await conn.commit()
            logger.info(f"🔄 Flushed {len(updates)} sector updates")
            updates = []
            
        # Rate limit friendly sleep
        await asyncio.sleep(0.2)

    # Final flush
    if updates:
        async with db.connection() as conn:
            await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
            await conn.commit()
        logger.info(f"🔄 Final flush of {len(updates)} updates")

if __name__ == "__main__":
    asyncio.run(backfill_sectors_deep())
