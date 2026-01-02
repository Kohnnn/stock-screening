"""
Intelligent Update Scheduler for VnStock data.

Market-aware scheduling with priority-based task execution.
Designed for 24/7 operation with minimal API usage.
"""

import asyncio
import schedule
import time
from datetime import datetime, timedelta, time as dt_time
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

from config import settings
from database import Database, get_database
from vnstock_collector import VnStockCollector, get_collector


class UpdateType(Enum):
    """Types of data updates."""
    SCREENER_DATA = "screener_data"      # Current prices & metrics
    STOCK_LISTINGS = "stock_listings"    # Stock list
    PRICE_HISTORY = "price_history"      # Historical prices
    FINANCIAL_DATA = "financial_data"    # Financial statements


class UpdateFrequency(Enum):
    """Update frequency options."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class UpdateTask:
    """Scheduled update task configuration."""
    name: str
    update_type: UpdateType
    frequency: UpdateFrequency
    schedule_time: str  # HH:MM format
    enabled: bool = True
    priority: int = 1   # Lower = higher priority
    max_runtime_minutes: int = 60
    retry_count: int = 3
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0


class UpdateScheduler:
    """
    Market-aware scheduler for data updates.
    
    Features:
    - Runs updates after market close
    - Prioritizes critical updates
    - Avoids updates during market hours
    - Persistent state for recovery
    - Health monitoring
    """
    
    def __init__(
        self,
        db: Optional[Database] = None,
        collector: Optional[VnStockCollector] = None,
    ):
        """Initialize scheduler."""
        self._db = db
        self._collector = collector
        self._running = False
        self._current_task: Optional[str] = None
        
        # Default tasks
        self.tasks: Dict[str, UpdateTask] = {}
        self._setup_default_tasks()
        
        logger.info("📅 UpdateScheduler initialized")
    
    async def _get_db(self) -> Database:
        """Get database instance."""
        if self._db is None:
            self._db = await get_database()
        return self._db
    
    async def _get_collector(self) -> VnStockCollector:
        """Get collector instance."""
        if self._collector is None:
            self._collector = await get_collector()
        return self._collector
    
    def _setup_default_tasks(self):
        """Set up default update tasks."""
        
        # Daily screener data (high priority - main data source)
        self.tasks["daily_screener"] = UpdateTask(
            name="Daily Screener Update",
            update_type=UpdateType.SCREENER_DATA,
            frequency=UpdateFrequency.DAILY,
            schedule_time=settings.DAILY_UPDATE_TIME,
            priority=1,
            max_runtime_minutes=30,
        )
        
        # Daily price history (high priority)
        self.tasks["daily_prices"] = UpdateTask(
            name="Daily Price History",
            update_type=UpdateType.PRICE_HISTORY,
            frequency=UpdateFrequency.DAILY,
            schedule_time="18:30",
            priority=2,
            max_runtime_minutes=120,
        )
        
        # Weekly stock listings (medium priority)
        self.tasks["weekly_listings"] = UpdateTask(
            name="Weekly Stock Listings",
            update_type=UpdateType.STOCK_LISTINGS,
            frequency=UpdateFrequency.WEEKLY,
            schedule_time="22:00",
            priority=3,
            max_runtime_minutes=30,
        )
        
        # Weekly financial data (lower priority, heavy API usage)
        self.tasks["weekly_financials"] = UpdateTask(
            name="Weekly Financial Data",
            update_type=UpdateType.FINANCIAL_DATA,
            frequency=UpdateFrequency.WEEKLY,
            schedule_time=settings.WEEKLY_UPDATE_TIME,
            priority=4,
            max_runtime_minutes=180,
        )
    
    def is_market_hours(self) -> bool:
        """Check if current time is within market hours."""
        now = datetime.now()
        current_hour = now.hour
        
        # Vietnam market: 9:00-11:30, 13:00-15:00
        is_morning = settings.MARKET_OPEN_HOUR <= current_hour < 12
        is_afternoon = 13 <= current_hour < settings.MARKET_CLOSE_HOUR
        
        return is_morning or is_afternoon
    
    def is_market_day(self) -> bool:
        """Check if today is a trading day (Mon-Fri)."""
        return datetime.now().weekday() < 5
    
    def can_run_update(self) -> bool:
        """Check if updates can run now."""
        # Always allow on weekends
        if not self.is_market_day():
            return True
        
        # Don't run during market hours
        if self.is_market_hours():
            return False
        
        return True
    
    async def execute_task(self, task: UpdateTask) -> bool:
        """
        Execute a single update task.
        
        Returns: True if successful
        """
        if not task.enabled:
            logger.info(f"⏸️ Task '{task.name}' is disabled")
            return False
        
        logger.info(f"🚀 Starting task: {task.name}")
        self._current_task = task.name
        task.run_count += 1
        task.last_run = datetime.now()
        
        db = await self._get_db()
        collector = await self._get_collector()
        
        log_id = await db.log_update_start(task.update_type.value)
        
        try:
            records_processed = 0
            
            if task.update_type == UpdateType.SCREENER_DATA:
                records_processed = await self._update_screener_data(db, collector)
                
            elif task.update_type == UpdateType.STOCK_LISTINGS:
                records_processed = await self._update_stock_listings(db, collector)
                
            elif task.update_type == UpdateType.PRICE_HISTORY:
                records_processed = await self._update_price_history(db, collector)
                
            elif task.update_type == UpdateType.FINANCIAL_DATA:
                records_processed = await self._update_financial_data(db, collector)
            
            # Success
            task.success_count += 1
            task.last_status = "completed"
            await db.log_update_complete(log_id, "completed", records_processed)
            
            logger.info(
                f"✅ Task '{task.name}' completed: "
                f"{records_processed} records"
            )
            return True
            
        except Exception as e:
            task.failure_count += 1
            task.last_status = f"failed: {str(e)}"
            await db.log_update_complete(log_id, "failed", error_message=str(e))
            
            logger.error(f"❌ Task '{task.name}' failed: {e}")
            return False
            
        finally:
            self._current_task = None
    
    async def _update_screener_data(
        self,
        db: Database,
        collector: VnStockCollector
    ) -> int:
        """Update screener data (current prices + full metrics)."""
        logger.info("📊 Updating screener data with FULL metrics...")
        
        # Use collect_screener_full for complete 84-metric data
        prices = await collector.collect_screener_full()
        
        if not prices:
            # Fallback to basic screener data
            logger.warning("⚠️ Full screener failed, falling back to basic")
            prices = await collector.collect_screener_data()
        
        if not prices:
            logger.warning("⚠️ No screener data collected")
            return 0
        
        # Upsert stock prices with all metrics
        count = await db.upsert_stock_prices(prices)
        
        # Also update stock listings from screener
        stocks = [
            {
                'symbol': p['symbol'],
                'company_name': p.get('company_name'),
                'exchange': p.get('exchange'),
                'industry': p.get('industry'),
            }
            for p in prices
        ]
        await db.upsert_stocks(stocks)
        
        return count
    
    async def _update_stock_listings(
        self,
        db: Database,
        collector: VnStockCollector
    ) -> int:
        """Update stock listings."""
        logger.info("📋 Updating stock listings...")
        
        stocks = await collector.collect_stock_listings()
        
        if not stocks:
            logger.warning("⚠️ No stock listings collected")
            return 0
        
        count = await db.upsert_stocks(stocks)
        return count
    
    async def _update_price_history(
        self,
        db: Database,
        collector: VnStockCollector
    ) -> int:
        """Update price history for all stocks."""
        logger.info("📈 Updating price history...")
        
        # Get all symbols
        symbols = await db.get_stock_symbols()
        
        if not symbols:
            logger.warning("⚠️ No symbols to update")
            return 0
        
        # Limit to top stocks by market cap to conserve API calls
        # Full history update would be too expensive
        max_symbols = min(len(symbols), 50)  # Top 50 stocks
        logger.info(f"📊 Updating history for {max_symbols} stocks")
        
        history_map = await collector.collect_batch_price_history(
            symbols[:max_symbols],
            batch_size=settings.BATCH_SIZE
        )
        
        total_records = 0
        for symbol, history in history_map.items():
            if history:
                count = await db.upsert_price_history(history)
                total_records += count
        
        return total_records
    
    async def _update_financial_data(
        self,
        db: Database,
        collector: VnStockCollector
    ) -> int:
        """Update financial data (weekly, expensive operation)."""
        logger.info("💰 Updating financial data...")
        
        # Get symbols - limit to conserve API
        symbols = await db.get_stock_symbols()
        max_symbols = min(len(symbols), 20)  # Top 20 only
        
        logger.info(f"💼 Updating financials for {max_symbols} stocks")
        
        count = 0
        for symbol in symbols[:max_symbols]:
            # Check circuit breaker
            if collector.circuit_breaker.is_open:
                logger.warning("⚠️ Circuit open, stopping financial update")
                break
            
            financial = await collector.collect_financial_data(symbol)
            if financial.get('ratios') or financial.get('balance_sheet'):
                count += 1
        
        return count
    
    async def run_task_by_name(self, task_name: str) -> bool:
        """Run a specific task by name."""
        if task_name not in self.tasks:
            logger.error(f"❌ Unknown task: {task_name}")
            return False
        
        return await self.execute_task(self.tasks[task_name])
    
    async def run_all_tasks(self) -> Dict[str, bool]:
        """Run all enabled tasks in priority order."""
        results = {}
        
        # Sort by priority
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.priority
        )
        
        for task in sorted_tasks:
            if task.enabled:
                results[task.name] = await self.execute_task(task)
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "running": self._running,
            "current_task": self._current_task,
            "is_market_hours": self.is_market_hours(),
            "is_market_day": self.is_market_day(),
            "can_run_update": self.can_run_update(),
            "tasks": {
                name: {
                    "enabled": task.enabled,
                    "priority": task.priority,
                    "schedule_time": task.schedule_time,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "last_status": task.last_status,
                    "run_count": task.run_count,
                    "success_count": task.success_count,
                    "failure_count": task.failure_count,
                }
                for name, task in self.tasks.items()
            }
        }


# Global scheduler instance
_scheduler: Optional[UpdateScheduler] = None


async def get_scheduler() -> UpdateScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        _scheduler = UpdateScheduler()
    
    return _scheduler
