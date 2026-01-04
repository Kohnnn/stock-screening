
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger
from database import Database
from vnstock_collector import VnStockCollector

class MarketIndicesCollector:
    """
    Collector for market indices (VNINDEX, VN30, HNX, UPCOM).
    Uses vnstock's price_board for real-time data or historical methods.
    """
    
    def __init__(self, db: Database):
        self.db = db
        self.collector = VnStockCollector()
        
    async def update_indices(self) -> int:
        """Fetch and update market indices."""
        logger.info("📊 Updating market indices...")
        
        # Standard indices list
        indices = [
            'VNINDEX', 'VN30', 
            'HNX', 'HNX30', 'HNXINDEX',
            'UPCOM', 'UPCOMINDEX'
        ]
        
        updated_count = 0
        
        # Use vnstock price_board for these if possible, 
        # but price_board usually takes stock symbols.
        # Indices in vnstock might come from a different API specifically for indices
        # or we treat them as symbols on specific exchanges.
        
        # Method 1: Use stock_board for indices if supported
        # Some sources map indices to tickers like 'VNINDEX', etc.
        
        # Valid symbols for price board?
        # VNINDEX is usually not in price_board directly as a tradeable stock.
        # We might need `stock_historical_data` or a specific index endpoint.
        
        # Let's try direct index history for today to get "current" value
        today = datetime.now().strftime('%Y-%m-%d')
        
        for index_code in indices:
            try:
                # Get latest data using quote/history which works for indices too usually
                df = await self.collector._protected_api_call(
                    self.collector.vnstock.stock(symbol=index_code, source='VCI').quote.history,
                    start=today, 
                    end=today
                )
                
                # If no data for today (e.g. weekend), try last 3 days
                if df is None or df.empty:
                    df = await self.collector._protected_api_call(
                        self.collector.vnstock.stock(symbol=index_code, source='VCI').quote.history,
                        days=3
                    )

                if df is not None and not df.empty:
                    latest = df.iloc[-1]
                    
                    # Map fields
                    # Time, Open, High, Low, Close, Volume
                    
                    data = {
                        'index_code': index_code,
                        'timestamp': str(latest.get('time', datetime.now().isoformat())),
                        'value': float(latest.get('close', 0)),
                        'change_value': float(latest.get('close', 0)) - float(latest.get('open', 0)), # Approx if no explicit change
                        'change_percent': 0.0, # Calculate below
                        'volume': int(latest.get('volume', 0)),
                        # Detailed advances/declines not available in simple history
                        'advances': 0,
                        'declines': 0,
                        'unchanged': 0,
                        'total_value': 0.0 
                    }
                    
                    # Calculate change from previous if possible
                    if len(df) > 1:
                        prev = df.iloc[-2]
                        prev_close = float(prev.get('close', 0))
                        if prev_close > 0:
                            data['change_value'] = data['value'] - prev_close
                            data['change_percent'] = (data['change_value'] / prev_close) * 100
                            
                    # Upsert to DB
                    await self.db.upsert_market_indices([data])
                    updated_count += 1
                    logger.info(f"✅ Updated index: {index_code} = {data['value']}")
                    
            except Exception as e:
                logger.error(f"❌ Failed to update index {index_code}: {e}")
                
        return updated_count

# Standalone run
async def run_indices_update(db_path: str = "./data/vnstock_data.db"):
    db = Database(db_path)
    await db.initialize()
    collector = MarketIndicesCollector(db)
    await collector.update_indices()

if __name__ == "__main__":
    asyncio.run(run_indices_update())
