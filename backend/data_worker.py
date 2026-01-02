"""
Real-time Data Worker for VnStock Screener.

Provides continuous background data updates with:
- Priority queue for VN30 stocks
- Configurable update intervals
- Market hours awareness
- Live progress tracking
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Set, Optional
from loguru import logger
from enum import Enum
from technical_indicators import calculate_all_indicators

class DataWorker:
    # ... (existing init methods)

    async def _calculate_and_save_metrics(self, symbols: List[str]):
        """Calculate and save technical metrics for updated stocks."""
        if not symbols:
            return
            
        metrics_batch = []
        for symbol in symbols:
            try:
                # Get history for calculation (need enough data for EMA200)
                history = await self.db.get_price_history(symbol, days=250)
                if not history or len(history) < 14:
                    continue
                    
                # Reverse to get oldest first for calculation
                history = list(reversed(history))
                
                metrics = calculate_all_indicators(history)
                if metrics:
                    metrics['symbol'] = symbol
                    metrics_batch.append(metrics)
            except Exception as e:
                logger.debug(f"Failed to calculate metrics for {symbol}: {e}")
        
        if metrics_batch:
            await self.db.upsert_stock_metrics(metrics_batch)
            logger.info(f"✨ Calculated metrics for {len(metrics_batch)} stocks")

    async def update_vn30(self) -> int:
        """Update VN30 stocks (highest priority)."""
        logger.info("📊 Updating VN30 stocks...")
        self.current_task = "VN30 Update"
        
        updated = 0
        updated_symbols = []
        for symbol in VN30_SYMBOLS:
            try:
                # Get latest price
                history = await self.collector.collect_price_history(
                    symbol, 
                    start_date=(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                )
                
                if history:
                    latest = history[-1]
                    price_data = {
                        'symbol': symbol,
                        'current_price': latest['close_price'],
                        'open_price': latest['open_price'],
                        'high_price': latest['high_price'],
                        'low_price': latest['low_price'],
                        'close_price': latest['close_price'],
                        'volume': latest['volume'],
                    }
                    await self.db.upsert_stock_prices([price_data])
                    updated += 1
                    updated_symbols.append(symbol)
                    self.successful_updates += 1
                    
            except Exception as e:
                logger.debug(f"Failed to update {symbol}: {e}")
                self.failed_updates += 1
        
        # Calculate metrics for updated stocks
        if updated_symbols:
            await self._calculate_and_save_metrics(updated_symbols)
        
        self.total_updates += len(VN30_SYMBOLS)
        self.last_vn30_update = datetime.now()
        logger.info(f"✅ VN30 update complete: {updated}/{len(VN30_SYMBOLS)}")
        return updated
    
    async def update_top_stocks(self, limit: int = 100) -> int:
        """Update top stocks by most recent activity."""
        logger.info(f"📊 Updating top {limit} stocks...")
        self.current_task = f"Top {limit} Update"
        
        # Get symbols with most data
        stocks_with_prices = await self.db.get_stocks_with_prices(limit=limit)
        symbols = [s['symbol'] for s in stocks_with_prices]
        
        updated = 0
        updated_symbols = []
        for symbol in symbols:
            if symbol in VN30_SYMBOLS:
                continue  # Already updated
            
            try:
                history = await self.collector.collect_price_history(
                    symbol,
                    start_date=(datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
                )
                
                if history:
                    latest = history[-1]
                    price_data = {
                        'symbol': symbol,
                        'current_price': latest['close_price'],
                        'open_price': latest['open_price'],
                        'high_price': latest['high_price'],
                        'low_price': latest['low_price'],
                        'close_price': latest['close_price'],
                        'volume': latest['volume'],
                    }
                    await self.db.upsert_stock_prices([price_data])
                    updated += 1
                    updated_symbols.append(symbol)
                    self.successful_updates += 1
                    
            except Exception as e:
                logger.debug(f"Failed to update {symbol}: {e}")
                self.failed_updates += 1
        
        # Calculate metrics for updated stocks
        if updated_symbols:
            await self._calculate_and_save_metrics(updated_symbols)
        
        self.total_updates += len(symbols)
        self.last_top100_update = datetime.now()
        logger.info(f"✅ Top stocks update complete: {updated}/{len(symbols)}")
        return updated
    
    async def update_all_listings(self) -> int:
        """Update all stock listings."""
        logger.info("📋 Updating all listings...")
        self.current_task = "Listings Update"
        
        listings = await self.collector.collect_stock_listings()
        if listings:
            await self.db.upsert_stocks(listings)
        
        self.last_all_update = datetime.now()
        logger.info(f"✅ Listings update complete: {len(listings)} stocks")
        return len(listings)
    
    async def run_update_cycle(self):
        """Run a single update cycle based on priorities and timing."""
        now = datetime.now()
        
        # Check if VN30 needs update
        if (
            self.last_vn30_update is None or 
            (now - self.last_vn30_update).total_seconds() >= self.vn30_interval
        ):
            await self.update_vn30()
            return
        
        # Check if top 100 needs update
        if (
            self.last_top100_update is None or
            (now - self.last_top100_update).total_seconds() >= self.top100_interval
        ):
            await self.update_top_stocks(100)
            return
        
        # Check if listings need update
        if (
            self.last_all_update is None or
            (now - self.last_all_update).total_seconds() >= self.all_stocks_interval
        ):
            await self.update_all_listings()
            return
        
        # Check if screener needs update (MOST EFFICIENT - 84 metrics in 1 call)
        if (
            self.last_screener_update is None or
            (now - self.last_screener_update).total_seconds() >= self.screener_interval
        ):
            await self.update_screener()
            return
        
        # Nothing to do
        self.current_task = None
    
    async def update_screener(self) -> int:
        """
        Update all stocks via TCBS Screener API.
        
        This is the MOST EFFICIENT method:
        - ONE API call returns 84 metrics for ALL ~1,600 stocks
        - Includes fundamentals, technicals, ratings, and signals
        """
        logger.info("📊 Updating via Screener (84 metrics)...")
        self.current_task = "Screener Update"
        
        try:
            screener_data = await self.collector.collect_screener_full()
            
            if screener_data:
                await self.db.upsert_screener_metrics(screener_data)
                self.successful_updates += 1
                logger.info(f"✅ Screener update complete: {len(screener_data)} stocks")
            else:
                logger.warning("⚠️ No screener data returned")
            
            self.last_screener_update = datetime.now()
            self.total_updates += 1
            return len(screener_data) if screener_data else 0
            
        except Exception as e:
            logger.error(f"❌ Screener update failed: {e}")
            self.failed_updates += 1
            self.last_screener_update = datetime.now()  # Still update to avoid retry flood
            return 0
    
    async def start(self):
        """Start the background worker."""
        self.running = True
        await self.initialize()
        
        logger.info("🚀 DataWorker started")
        
        while self.running:
            try:
                # Run update cycle
                await self.run_update_cycle()
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                logger.info("🛑 DataWorker cancelled")
                break
            except Exception as e:
                logger.error(f"❌ DataWorker error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
        
        logger.info("👋 DataWorker stopped")
    
    async def stop(self):
        """Stop the background worker."""
        self.running = False
        self.current_task = None
    
    def get_status(self) -> Dict:
        """Get worker status."""
        return {
            'running': self.running,
            'current_task': self.current_task,
            'is_market_hours': self.is_market_hours(),
            'total_updates': self.total_updates,
            'successful_updates': self.successful_updates,
            'failed_updates': self.failed_updates,
            'success_rate': round(
                self.successful_updates / max(self.total_updates, 1) * 100, 2
            ),
            'last_vn30_update': self.last_vn30_update.isoformat() if self.last_vn30_update else None,
            'last_top100_update': self.last_top100_update.isoformat() if self.last_top100_update else None,
            'last_all_update': self.last_all_update.isoformat() if self.last_all_update else None,
        }


# Global worker instance
_worker: Optional[DataWorker] = None
_worker_task: Optional[asyncio.Task] = None


async def get_worker(db: Database) -> DataWorker:
    """Get or create the global worker instance."""
    global _worker
    
    if _worker is None:
        _worker = DataWorker(db)
    
    return _worker


async def start_worker(db: Database):
    """Start the global worker in background."""
    global _worker, _worker_task
    
    if _worker_task is not None and not _worker_task.done():
        logger.info("Worker already running")
        return
    
    _worker = await get_worker(db)
    _worker_task = asyncio.create_task(_worker.start())
    logger.info("🚀 Background worker started")


async def stop_worker():
    """Stop the global worker."""
    global _worker, _worker_task
    
    if _worker:
        await _worker.stop()
    
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    
    logger.info("🛑 Background worker stopped")
