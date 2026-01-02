"""
Data Update Registry for VnStock Screener.

Centralized tracking of what data has been updated and what needs updating.
Runs comprehensive checks on app startup to identify stale/missing data.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from config import settings


class DataType(Enum):
    """Types of data that can be tracked for updates."""
    PRICE = "price"              # Current stock prices
    HISTORY = "history"          # Price history (OHLCV)
    FINANCIALS = "financials"    # Financial statements
    DIVIDENDS = "dividends"      # Dividend history
    RATINGS = "ratings"          # Company ratings
    OVERVIEW = "overview"        # Company overview/profile


@dataclass
class UpdateConfig:
    """Configuration for each data type's update frequency."""
    data_type: DataType
    update_interval_hours: int      # How often to update
    priority: int                   # 1=highest, 5=lowest
    market_hours_only: bool = False # Only update during market hours
    
    
# Default update configurations
DEFAULT_UPDATE_CONFIGS = {
    DataType.PRICE: UpdateConfig(DataType.PRICE, 1, 1, True),           # Every hour during market
    DataType.HISTORY: UpdateConfig(DataType.HISTORY, 24, 2, False),     # Daily
    DataType.FINANCIALS: UpdateConfig(DataType.FINANCIALS, 168, 4, False),  # Weekly
    DataType.DIVIDENDS: UpdateConfig(DataType.DIVIDENDS, 168, 5, False),    # Weekly
    DataType.RATINGS: UpdateConfig(DataType.RATINGS, 168, 5, False),        # Weekly
    DataType.OVERVIEW: UpdateConfig(DataType.OVERVIEW, 168, 3, False),      # Weekly
}


class DataUpdateRegistry:
    """
    Centralized registry for tracking data updates.
    
    Features:
    - Per-symbol, per-data-type tracking
    - Priority-based update scheduling
    - Delta-based updates (only update what's needed)
    - Startup data health check
    """
    
    def __init__(self, db):
        """Initialize the registry with database connection."""
        self.db = db
        self.configs = DEFAULT_UPDATE_CONFIGS.copy()
        self._initialized = False
        
        logger.info("📊 DataUpdateRegistry initialized")
    
    async def initialize(self):
        """Initialize the registry, loading existing state from DB."""
        if self._initialized:
            return
        
        # Ensure database is initialized (schema created)
        await self.db.initialize()
        self._initialized = True
        logger.info("✅ DataUpdateRegistry ready")
    
    async def get_symbols_needing_update(
        self,
        data_type: DataType,
        limit: int = 100
    ) -> List[str]:
        """
        Get list of symbols that need updating for a specific data type.
        
        Considers:
        - Time since last update vs configured interval
        - Priority ordering
        - Failure retry logic
        """
        config = self.configs.get(data_type)
        if not config:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=config.update_interval_hours)
        
        query = """
            SELECT DISTINCT s.symbol
            FROM stocks s
            LEFT JOIN data_update_tracker t 
                ON s.symbol = t.symbol AND t.data_type = ?
            WHERE s.is_active = 1
              AND (
                  t.last_update IS NULL 
                  OR t.last_update < ?
                  OR t.last_status = 'failed'
              )
            ORDER BY 
                CASE WHEN t.last_update IS NULL THEN 0 ELSE 1 END,
                t.priority ASC,
                t.last_update ASC
            LIMIT ?
        """
        
        async with self.db.connection() as conn:
            cursor = await conn.execute(
                query, 
                (data_type.value, cutoff_time.isoformat(), limit)
            )
            rows = await cursor.fetchall()
            return [row['symbol'] for row in rows]
    
    async def mark_symbol_updated(
        self,
        symbol: str,
        data_type: DataType,
        status: str = "success",
        error_message: Optional[str] = None,
        data_hash: Optional[str] = None
    ):
        """Mark a symbol's data as updated."""
        now = datetime.now()
        config = self.configs.get(data_type)
        next_update = now + timedelta(hours=config.update_interval_hours if config else 24)
        
        query = """
            INSERT INTO data_update_tracker 
                (symbol, data_type, last_update, next_update_due, update_count, 
                 last_status, error_message, priority, data_hash)
            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
            ON CONFLICT(symbol, data_type) DO UPDATE SET
                last_update = excluded.last_update,
                next_update_due = excluded.next_update_due,
                update_count = update_count + 1,
                last_status = excluded.last_status,
                error_message = excluded.error_message,
                data_hash = excluded.data_hash
        """
        
        async with self.db.connection() as conn:
            await conn.execute(query, (
                symbol,
                data_type.value,
                now.isoformat(),
                next_update.isoformat(),
                status,
                error_message,
                config.priority if config else 3,
                data_hash
            ))
            await conn.commit()
    
    async def mark_batch_updated(
        self,
        symbols: List[str],
        data_type: DataType,
        status: str = "success"
    ):
        """Mark multiple symbols as updated (batch operation)."""
        for symbol in symbols:
            await self.mark_symbol_updated(symbol, data_type, status)
    
    async def get_update_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of update status across all data types.
        
        Returns dashboard-ready statistics.
        """
        summary = {
            "timestamp": datetime.now().isoformat(),
            "by_data_type": {},
            "totals": {
                "symbols_tracked": 0,
                "up_to_date": 0,
                "needing_update": 0,
                "failed": 0
            }
        }
        
        async with self.db.connection() as conn:
            # Get total active symbols
            cursor = await conn.execute(
                "SELECT COUNT(*) as count FROM stocks WHERE is_active = 1"
            )
            row = await cursor.fetchone()
            total_symbols = row['count'] if row else 0
            summary["totals"]["symbols_tracked"] = total_symbols
            
            # Stats per data type
            for data_type in DataType:
                config = self.configs.get(data_type)
                cutoff = datetime.now() - timedelta(
                    hours=config.update_interval_hours if config else 24
                )
                
                # Count up-to-date
                cursor = await conn.execute("""
                    SELECT COUNT(*) as count FROM data_update_tracker
                    WHERE data_type = ? AND last_status = 'success' 
                      AND last_update >= ?
                """, (data_type.value, cutoff.isoformat()))
                row = await cursor.fetchone()
                up_to_date = row['count'] if row else 0
                
                # Count failed
                cursor = await conn.execute("""
                    SELECT COUNT(*) as count FROM data_update_tracker
                    WHERE data_type = ? AND last_status = 'failed'
                """, (data_type.value,))
                row = await cursor.fetchone()
                failed = row['count'] if row else 0
                
                # Count never updated (need initial data)
                cursor = await conn.execute("""
                    SELECT COUNT(*) as count FROM stocks s
                    LEFT JOIN data_update_tracker t 
                        ON s.symbol = t.symbol AND t.data_type = ?
                    WHERE s.is_active = 1 AND t.symbol IS NULL
                """, (data_type.value,))
                row = await cursor.fetchone()
                never_updated = row['count'] if row else 0
                
                needing_update = total_symbols - up_to_date
                
                summary["by_data_type"][data_type.value] = {
                    "up_to_date": up_to_date,
                    "needing_update": needing_update,
                    "never_updated": never_updated,
                    "failed": failed,
                    "update_interval_hours": config.update_interval_hours if config else 24
                }
                
                summary["totals"]["up_to_date"] += up_to_date
                summary["totals"]["failed"] += failed
            
            summary["totals"]["needing_update"] = (
                total_symbols * len(DataType) - summary["totals"]["up_to_date"]
            )
        
        return summary
    
    async def startup_data_check(self) -> Dict[str, Any]:
        """
        Run comprehensive data health check on app startup.
        
        Returns summary of data status and recommendations.
        """
        logger.info("🔍 Running startup data health check...")
        
        await self.initialize()
        
        summary = await self.get_update_summary()
        
        # Add recommendations
        recommendations = []
        
        # Check for critical missing data
        price_stats = summary["by_data_type"].get("price", {})
        if price_stats.get("never_updated", 0) > 0:
            recommendations.append({
                "priority": "high",
                "type": "missing_price_data",
                "message": f"{price_stats['never_updated']} stocks have never had price data collected",
                "action": "Run initial price collection"
            })
        
        if price_stats.get("needing_update", 0) > price_stats.get("up_to_date", 0):
            recommendations.append({
                "priority": "medium", 
                "type": "stale_price_data",
                "message": "Most price data is outdated",
                "action": "Trigger price update cycle"
            })
        
        # Check for failed updates that need retry
        if summary["totals"]["failed"] > 0:
            recommendations.append({
                "priority": "medium",
                "type": "failed_updates",
                "message": f"{summary['totals']['failed']} updates have failed and need retry",
                "action": "Review error logs and retry failed updates"
            })
        
        summary["recommendations"] = recommendations
        summary["health_status"] = self._calculate_health_status(summary)
        
        logger.info(
            f"📊 Data check complete: "
            f"{summary['totals']['symbols_tracked']} symbols, "
            f"{summary['totals']['up_to_date']} up-to-date, "
            f"{summary['totals']['needing_update']} need updates, "
            f"Health: {summary['health_status']}"
        )
        
        return summary
    
    def _calculate_health_status(self, summary: Dict) -> str:
        """Calculate overall data health status."""
        totals = summary["totals"]
        
        if totals["symbols_tracked"] == 0:
            return "no_data"
        
        # Calculate percentage of up-to-date data
        total_data_points = totals["symbols_tracked"] * len(DataType)
        if total_data_points == 0:
            return "unknown"
        
        up_to_date_pct = (totals["up_to_date"] / total_data_points) * 100
        
        if up_to_date_pct >= 80:
            return "healthy"
        elif up_to_date_pct >= 50:
            return "degraded"
        elif up_to_date_pct >= 20:
            return "stale"
        else:
            return "critical"
    
    async def get_priority_update_queue(
        self,
        max_symbols: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get prioritized queue of symbols needing updates.
        
        Combines all data types, prioritized by:
        1. Never updated symbols (highest priority)
        2. Failed updates (need retry)
        3. Most overdue updates
        4. Priority setting
        """
        queue = []
        
        for data_type in DataType:
            config = self.configs.get(data_type)
            symbols = await self.get_symbols_needing_update(
                data_type, 
                limit=max_symbols // len(DataType)
            )
            
            for symbol in symbols:
                queue.append({
                    "symbol": symbol,
                    "data_type": data_type.value,
                    "priority": config.priority if config else 3
                })
        
        # Sort by priority
        queue.sort(key=lambda x: x["priority"])
        
        return queue[:max_symbols]
    
    async def clear_failed_status(self, symbol: Optional[str] = None):
        """Clear failed status to allow retry."""
        if symbol:
            query = """
                UPDATE data_update_tracker 
                SET last_status = 'pending', error_message = NULL
                WHERE symbol = ? AND last_status = 'failed'
            """
            params = (symbol,)
        else:
            query = """
                UPDATE data_update_tracker 
                SET last_status = 'pending', error_message = NULL
                WHERE last_status = 'failed'
            """
            params = ()
        
        async with self.db.connection() as conn:
            await conn.execute(query, params)
            await conn.commit()


# Global registry instance
_registry: Optional[DataUpdateRegistry] = None


async def get_update_registry(db=None) -> DataUpdateRegistry:
    """Get or create the global registry instance."""
    global _registry
    
    if _registry is None:
        if db is None:
            from database import get_database
            db = await get_database()
        _registry = DataUpdateRegistry(db)
        await _registry.initialize()
    
    return _registry
