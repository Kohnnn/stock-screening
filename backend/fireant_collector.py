
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from database import Database
from vnstock_collector import VnStockCollector

class FireAntCollector:
    """
    Collector for financial metrics (Margin, Growth) to fill Screener.
    
    NOTE: Direct scraping of dautu.fireant.vn requires Authentication (stateless 401).
    This collector currently leverages the enabled DNSE source in VnStock to 
    fetch equivalent financial ratio data and backfill the screener_metrics table.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.collector = VnStockCollector()
        # Force VCI source for reliable financial statements
        self.collector.default_source = 'VCI'
        
    async def update_margins_and_growth(self, concurrency: int = 5) -> int:
        """
        Update missing Margin and Growth metrics in screener_metrics.
        Calculates metrics manually from Income Statement (VCI source).
        """
        logger.info("🔥 FireAntCollector: Starting margin/growth calculation (Local)...")
        
        # Get all active symbols
        try:
            stocks = await self.db.get_stock_symbols()
        except AttributeError:
             stocks = []
             async with self.db.connection() as conn:
                 cursor = await conn.execute("SELECT symbol FROM stocks WHERE is_active=1")
                 stocks = [row['symbol'] for row in await cursor.fetchall()]

        if not stocks:
            return 0
            
        updated_count = 0
        semaphore = asyncio.Semaphore(concurrency)
        
        async def process_stock(symbol: str):
            nonlocal updated_count
            async with semaphore:
                try:
                    # 1. Collect Income Statement (Annual) - VCI source
                    # We access vnstock directly to handle Vietnamese keys
                    try:
                        stock = self.collector.vnstock.stock(symbol=symbol, source='VCI')
                        df = await self.collector._protected_api_call(
                            stock.finance.income_statement,
                            period='year', 
                            lang='vi'
                        )
                    except Exception as e:
                        logger.debug(f"Error fetching income stmt for {symbol}: {e}")
                        df = None

                    if df is None or df.empty:
                        return

                    # Parse records manually
                    records = df.to_dict('records')
                    # Sort desc by year (usually needed as API order varies)
                    # VCI usually has 'Năm' or 'yearReport'
                    records.sort(key=lambda x: x.get('Năm', x.get('yearReport', 0)), reverse=True)

                    latest = records[0] if len(records) > 0 else None
                    prev = records[1] if len(records) > 1 else None
                    
                    if not latest:
                        return
                        
                    # 2. Extract Values using Vietnamese keys (VCI specific)
                    # Keys based on inspection:
                    # 'Doanh thu thuần', 'Lãi gộp', 'Cổ đông của Công ty mẹ'
                    
                    def get_val(row, keys):
                         for k in keys:
                             if k in row and row[k] is not None:
                                 return self.collector._safe_float(row[k])
                         return 0.0

                    revenue = get_val(latest, ['Doanh thu thuần', 'Doanh thu (đồng)', 'Doanh thu'])
                    gross_profit = get_val(latest, ['Lãi gộp', 'Lợi nhuận gộp'])
                    net_profit = get_val(latest, ['Cổ đông của Công ty mẹ', 'Lợi nhuận sau thuế của Cổ đông của Công ty mẹ', 'Lợi nhuận sau thuế'])
                    
                    year = latest.get('Năm', latest.get('yearReport'))
                    # logger.info(f"{symbol} {year}: R={revenue} GP={gross_profit} NP={net_profit}") # Debug log
                    
                    # 3. Calculate Metrics
                    updates = {}
                    
                    # Gross Profit (Ty) / Revenue (Ty)
                    # Note: VCI values are absolute (Dong).
                    
                    if revenue and revenue != 0:
                        updates['gross_margin'] = (gross_profit / revenue) * 100
                        updates['net_margin'] = (net_profit / revenue) * 100
                    
                    # 4. Calculate Growth (YoY)
                    if prev:
                        prev_revenue = get_val(prev, ['Doanh thu thuần', 'Doanh thu (đồng)', 'Doanh thu'])
                        if prev_revenue and prev_revenue != 0:
                            updates['revenue_growth_1y'] = ((revenue - prev_revenue) / prev_revenue) * 100
                    
                    # 5. Store updates
                    if updates:
                        async with self.db.connection() as conn:
                            fields = [f"{k} = ?" for k in updates.keys()]
                            # Ensure record exists before update, or use upsert. 
                            # Since we only have partial data here, and other columns might be NULL if we just insert,
                            # best is to try UPDATE first, if 0 rows modified, then INSERT (with only these fields) 
                            # But wait, screener_metrics has many columns. Initializing a row with just these 3 might be fine.
                            
                            current_time = datetime.now().isoformat()
                            
                            # UPSERT logic for SQLite:
                            # INSERT INTO table (col1, col2, symbol) VALUES (?, ?, ?) 
                            # ON CONFLICT(symbol) DO UPDATE SET col1=excluded.col1, col2=excluded.col2;
                            
                            # Prepare keys and placeholders
                            keys = list(updates.keys())
                            placeholders = ["?"] * len(keys)
                            
                            # Construct query
                            query = f"""
                                INSERT INTO screener_metrics (symbol, updated_at, {', '.join(keys)})
                                VALUES (?, ?, {', '.join(placeholders)})
                                ON CONFLICT(symbol) DO UPDATE SET
                                    updated_at = excluded.updated_at,
                                    {', '.join([f"{k} = excluded.{k}" for k in keys])}
                            """
                            
                            # Prepare values: symbol, time, ...metrics
                            query_values = [symbol, current_time] + list(updates.values())
                            
                            await conn.execute(query, query_values)
                            await conn.commit()
                            
                        updated_count += 1
                        
                except Exception as e:
                    logger.debug(f"Failed to update {symbol}: {e}")

        # Run in batches
        tasks = [process_stock(s) for s in stocks]
        
        batch_size = 50
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i+batch_size]
            await asyncio.gather(*batch)
            logger.info(f"🔥 Progress: {min(i+batch_size, len(tasks))}/{len(tasks)}")
            
        logger.info(f"✅ FireAntCollector: Calculated & updated metrics for {updated_count} stocks")
        return updated_count

# Helper to run standalone
async def run_fireant_backfill(db_path: str = "backend/data/vnstock_data.db"):
    import os
    if not os.path.exists(db_path):
        # Try relative to backend dir if running from there
        if os.path.exists("data/vnstock_data.db"):
            db_path = "data/vnstock_data.db"
    
    logger.info(f"Using database: {db_path}")
    db = Database(db_path)
    await db.initialize() # Ensure schema is loaded
    collector = FireAntCollector(db)
    await collector.update_margins_and_growth()

if __name__ == "__main__":
    asyncio.run(run_fireant_backfill())
