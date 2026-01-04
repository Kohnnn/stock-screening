
import asyncio
from database import Database
from vnstock import Listing
from loguru import logger
import pandas as pd

async def backfill_sectors():
    db = Database("./data/vnstock_data.db")
    await db.initialize()
    
    try:
        # Using Listing class from vnstock 3.x
        logger.info("Fetching listing from TCBS via Listing class...")
        listing_tcbs = Listing(source='VCI')
        df = listing_tcbs.all_symbols()
        
        sector_col = None
        symbol_col = 'ticker'
        
        if df is not None and not df.empty:
            logger.info(f"TCBS Columns: {df.columns.tolist()}")
            # Columns usually: ticker, organName, organShortName, comGroupCode, icbCode, icbName, sector...
            for col in ['industry', 'sector', 'icbName', 'icb_name', 'nganh_nghe', 'organName']:
                if col in df.columns:
                    sector_col = col
                    break
        
        # Fallback to SSI if needed
        if (not sector_col) or (df is None) or df.empty:
            logger.info("Fetching listing from SSI...")
            listing_ssi = Listing(source='SSI')
            df_ssi = listing_ssi.all_symbols()
            
            if df_ssi is not None and not df_ssi.empty:
                df = df_ssi
                logger.info(f"SSI Columns: {df.columns.tolist()}")
                for col in ['icbName', 'sectorName', 'industry']:
                    if col in df.columns:
                        sector_col = col
                        symbol_col = 'ticker'
                        break

        if df is not None and not df.empty and sector_col:
            logger.info(f"Found sector column: {sector_col}")
            updates = []
            for _, row in df.iterrows():
                symbol = row.get(symbol_col)
                sector = row.get(sector_col)
                
                if symbol and sector and isinstance(sector, str):
                    updates.append((sector, symbol))
            
            if updates:
                logger.info(f"Updating sectors for {len(updates)} stocks...")
                async with db.connection() as conn:
                    await conn.executemany("UPDATE stocks SET sector = ? WHERE symbol = ?", updates)
                    await conn.commit()
                logger.info("✅ Sectors updated")
            else:
                logger.warning("No updates prepared (maybe empty sectors?)")
        else:
            logger.error("Could not find sector column in any source")

    except Exception as e:
        logger.error(f"Error backfilling sectors: {e}")

if __name__ == "__main__":
    asyncio.run(backfill_sectors())
