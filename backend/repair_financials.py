import asyncio
import logging
from vnstock_collector import get_collector
from database import get_database
from calculate_metrics import run_metrics_calculation

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

async def repair_financials():
    """
    Repair financial data for all stocks using CafeF.
    """
    logger.info("🔧 Starting Financial Data Repair using CafeF...")
    
    db = await get_database()
    collector = await get_collector()
    
    # Get all active stocks
    stocks = await db.get_stocks(limit=5000)
    logger.info(f"📋 Found {len(stocks)} stocks to check")
    
    success_count = 0
    fail_count = 0
    
    # Process in chunks to avoid overwhelming everything
    chunk_size = 10
    
    for i in range(0, len(stocks), chunk_size):
        chunk = stocks[i:i+chunk_size]
        tasks = []
        
        for stock in chunk:
            symbol = stock['symbol']
            
            # Skip if we already have good data (e.g. recent revenue/profit)
            # But here we assume we need to fill gaps, so we check if key fields are missing
            if stock.get('revenue') and stock.get('profit') and stock.get('total_assets'):
                continue
                
            tasks.append(process_stock(db, collector, symbol))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            for res in results:
                if res:
                    success_count += 1
                else:
                    fail_count += 1
                    
        logger.info(f"📊 Progress: {min(i+chunk_size, len(stocks))}/{len(stocks)} - Success: {success_count}, Fail: {fail_count}")
        
        # Small pause between chunks
        await asyncio.sleep(2)

    logger.info("✅ Repair complete!")
    logger.info(f"🎉 Updated {success_count} stocks. Failed: {fail_count}")
    
    # Trigger metrics calculation
    logger.info("🧮 Recalculating metrics...")
    updated = run_metrics_calculation()
    logger.info(f"✅ Recalculated metrics for {updated} stocks")

async def process_stock(db, collector, symbol):
    try:
        data = await collector.collect_financials_from_cafef(symbol)
        if data:
            # We need to map this to db schema inside upsert_stock_prices or similar
            # stock_prices table has columns: revenue, profit, total_assets, total_debt, owner_equity, cash
            # data has these keys ready.
            
            # Create a minimal list of 1 dict for upsert
            stock_data = {
                'symbol': symbol,
                'revenue': data.get('revenue'),
                'profit': data.get('profit'),
                'total_assets': data.get('total_assets'),
                'total_debt': data.get('total_debt'),
                'owner_equity': data.get('owner_equity'),
                'cash': data.get('cash'),
                # We also need current price/volume ideally, but let's assume they might exist or we just update partials
                # upsert_stock_prices might require other fields or overwrite them with None if not cautious
                # Let's check upsert_stock_prices implementation first if we can partial update.
                # Actually, standard SQL upsert replaces. We should fetch existing first or use specific update query.
                # For safety, let's use a specific UPDATE query here directly.
            }
            
            async with db.connection() as conn:
                await conn.execute("""
                    UPDATE stock_prices 
                    SET revenue = COALESCE(?, revenue),
                        profit = COALESCE(?, profit),
                        total_assets = COALESCE(?, total_assets),
                        total_debt = COALESCE(?, total_debt),
                        owner_equity = COALESCE(?, owner_equity),
                        cash = COALESCE(?, cash)
                    WHERE symbol = ?
                """, (
                    stock_data['revenue'],
                    stock_data['profit'],
                    stock_data['total_assets'],
                    stock_data['total_debt'],
                    stock_data['owner_equity'],
                    stock_data['cash'],
                    symbol
                ))
                await conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
    return False

if __name__ == "__main__":
    asyncio.run(repair_financials())
