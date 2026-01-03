"""
Database manager for VnStock Screener.

Provides async SQLite operations with connection pooling and error handling.
"""

import sqlite3
import aiosqlite
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from loguru import logger

from config import settings


class Database:
    """
    Async database manager for VnStock data.
    
    Uses aiosqlite for non-blocking operations.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager."""
        self.db_path = db_path or settings.DATABASE_PATH
        self._initialized = False
        
        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize database with schema."""
        if self._initialized:
            return
        
        schema_path = Path(__file__).parent / "database_schema.sql"
        
        if schema_path.exists():
            async with aiosqlite.connect(self.db_path) as db:
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = f.read()
                await db.executescript(schema)
                await db.commit()
            
            logger.info(f"✅ Database initialized: {self.db_path}")
        else:
            logger.warning(f"⚠️ Schema file not found: {schema_path}")
        
        self._initialized = True
    
    @asynccontextmanager
    async def connection(self):
        """Get async database connection."""
        if not self._initialized:
            await self.initialize()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db
    
    # =========================================
    # Stock Operations
    # =========================================
    
    async def upsert_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """Insert or update stock listings."""
        if not stocks:
            return 0
        
        query = """
            INSERT OR REPLACE INTO stocks 
            (symbol, company_name, exchange, sector, industry, 
             listing_date, shares_outstanding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    s.get('symbol'),
                    s.get('company_name'),
                    s.get('exchange'),
                    s.get('sector'),
                    s.get('industry'),
                    s.get('listing_date'),
                    s.get('shares_outstanding'),
                    datetime.now().isoformat()
                )
                for s in stocks
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(stocks)} stocks")
            return len(stocks)
    
    async def upsert_stock_prices(self, prices: List[Dict[str, Any]]) -> int:
        """Insert or update current stock prices."""
        if not prices:
            return 0
        
        query = """
            INSERT OR REPLACE INTO stock_prices 
            (symbol, current_price, price_change, percent_change,
             open_price, high_price, low_price, close_price,
             volume, market_cap, pe_ratio, pb_ratio,
             eps, bvps, roe, roa, revenue, profit,
             book_value, ps_ratio, total_debt, owner_equity,
             total_assets, debt_to_equity, equity_to_assets,
             cash, foreign_ownership, avg_volume_52w, listed_shares,
             data_source, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    p.get('symbol'),
                    p.get('current_price'),
                    p.get('price_change'),
                    p.get('percent_change'),
                    p.get('open_price'),
                    p.get('high_price'),
                    p.get('low_price'),
                    p.get('close_price'),
                    p.get('volume'),
                    p.get('market_cap'),
                    p.get('pe_ratio'),
                    p.get('pb_ratio'),
                    p.get('eps'),
                    p.get('bvps') or p.get('book_value'),  # Alias for compatibility
                    p.get('roe'),
                    p.get('roa'),
                    p.get('revenue'),
                    p.get('profit'),
                    # Cophieu68 specific fields
                    p.get('book_value'),
                    p.get('ps_ratio'),
                    p.get('total_debt'),
                    p.get('owner_equity'),
                    p.get('total_assets'),
                    p.get('debt_to_equity'),
                    p.get('equity_to_assets'),
                    p.get('cash'),
                    p.get('foreign_ownership'),
                    p.get('avg_volume_52w'),
                    p.get('listed_shares'),
                    p.get('data_source', 'vnstock'),
                    datetime.now().isoformat()
                )
                for p in prices
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(prices)} stock prices")
            return len(prices)
    
    async def upsert_price_history(self, history: List[Dict[str, Any]]) -> int:
        """Insert or update price history."""
        if not history:
            return 0
        
        query = """
            INSERT OR REPLACE INTO price_history 
            (symbol, date, open_price, high_price, low_price, 
             close_price, volume, adjusted_close)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    h.get('symbol'),
                    h.get('date'),
                    h.get('open_price'),
                    h.get('high_price'),
                    h.get('low_price'),
                    h.get('close_price'),
                    h.get('volume'),
                    h.get('adjusted_close')
                )
                for h in history
            ]
            await db.executemany(query, params)
            await db.commit()
            
            return len(history)
    
    # =========================================
    # Query Operations
    # =========================================
    
    async def get_stocks(
        self,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        pe_min: Optional[float] = None,
        pe_max: Optional[float] = None,
        pb_min: Optional[float] = None,
        pb_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        market_cap_min: Optional[float] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get stocks with optional filters."""
        
        query = """
            SELECT 
                s.symbol,
                s.company_name,
                s.exchange,
                s.sector,
                s.industry,
                sp.current_price,
                sp.price_change,
                sp.percent_change,
                sp.volume,
                sp.market_cap,
                sp.pe_ratio,
                sp.pb_ratio,
                sp.roe,
                sp.roa,
                sp.eps,
                sp.updated_at
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE s.is_active = 1
        """
        
        params = []
        
        if exchange:
            query += " AND s.exchange = ?"
            params.append(exchange)
        
        if sector:
            query += " AND s.sector = ?"
            params.append(sector)
        
        if pe_min is not None:
            query += " AND sp.pe_ratio >= ?"
            params.append(pe_min)
        
        if pe_max is not None:
            query += " AND sp.pe_ratio <= ?"
            params.append(pe_max)
        
        if pb_min is not None:
            query += " AND sp.pb_ratio >= ?"
            params.append(pb_min)
        
        if pb_max is not None:
            query += " AND sp.pb_ratio <= ?"
            params.append(pb_max)
        
        if roe_min is not None:
            query += " AND sp.roe >= ?"
            params.append(roe_min)
        
        if market_cap_min is not None:
            query += " AND sp.market_cap >= ?"
            params.append(market_cap_min)
        
        if search:
            query += " AND (s.symbol LIKE ? OR s.company_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        query += " ORDER BY sp.market_cap DESC NULLS LAST"
        query += f" LIMIT {limit} OFFSET {offset}"
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    async def get_stock_count(self, exchange: Optional[str] = None) -> int:
        """Get total stock count."""
        query = "SELECT COUNT(*) as count FROM stocks WHERE is_active = 1"
        params = []
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    async def get_stock_symbols(self, exchange: Optional[str] = None) -> List[str]:
        """Get list of stock symbols."""
        query = "SELECT symbol FROM stocks WHERE is_active = 1"
        params = []
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [row['symbol'] for row in rows]
    
    async def get_sectors(self) -> List[str]:
        """Get list of unique sectors."""
        query = """
            SELECT DISTINCT sector FROM stocks 
            WHERE sector IS NOT NULL AND sector != ''
            ORDER BY sector
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query)
            rows = await cursor.fetchall()
            return [row['sector'] for row in rows]
    
    async def get_stocks_with_prices(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get stocks that have price data (for priority updates)."""
        query = """
            SELECT 
                s.symbol,
                s.company_name,
                sp.current_price,
                sp.updated_at
            FROM stocks s
            INNER JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE s.is_active = 1 AND sp.current_price IS NOT NULL
            ORDER BY sp.updated_at DESC
            LIMIT ?
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_price_history(
        self,
        symbol: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get price history for a specific stock."""
        query = """
            SELECT date, open_price, high_price, low_price, close_price, volume
            FROM price_history
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol, days))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Stock Metrics Operations
    # =========================================
    
    async def upsert_stock_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """Insert or update calculated stock metrics."""
        if not metrics:
            return 0
        
        query = """
            INSERT OR REPLACE INTO stock_metrics 
            (symbol, adtv_shares, adtv_value, volume_vs_adtv,
             rsi_14, macd, macd_signal, macd_histogram, adx,
             ema_20, ema_50, ema_200,
             price_vs_ema20, ema20_vs_ema50, ema50_vs_ema200,
             price_return_1m, price_return_3m, price_fluctuation,
             stock_trend, net_margin, gross_margin, 
             npat_growth_yoy, revenue_growth_yoy, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    m.get('symbol'),
                    m.get('adtv_shares'),
                    m.get('adtv_value'),
                    m.get('volume_vs_adtv'),
                    m.get('rsi_14'),
                    m.get('macd'),
                    m.get('macd_signal'),
                    m.get('macd_histogram'),
                    m.get('adx'),
                    m.get('ema_20'),
                    m.get('ema_50'),
                    m.get('ema_200'),
                    m.get('price_vs_ema20'),
                    m.get('ema20_vs_ema50'),
                    m.get('ema50_vs_ema200'),
                    m.get('price_return_1m'),
                    m.get('price_return_3m'),
                    m.get('price_fluctuation'),
                    m.get('stock_trend'),
                    m.get('net_margin'),
                    m.get('gross_margin'),
                    m.get('npat_growth_yoy'),
                    m.get('revenue_growth_yoy'),
                    datetime.now().isoformat(),
                )
                for m in metrics
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(metrics)} stock metrics")
            return len(metrics)
    
    async def get_stock_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get calculated metrics for a specific stock."""
        query = "SELECT * FROM stock_metrics WHERE symbol = ?"
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol,))
            row = await cursor.fetchone()
            return dict(row) if row else None
    
    async def get_stocks_with_metrics(
        self,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        trend: Optional[str] = None,
        adx_min: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get stocks filtered by technical metrics."""
        query = """
            SELECT 
                s.symbol, s.company_name, s.exchange, s.sector,
                sp.current_price, sp.percent_change, sp.volume, sp.market_cap,
                sp.pe_ratio, sp.pb_ratio, sp.roe,
                sm.*
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            LEFT JOIN stock_metrics sm ON s.symbol = sm.symbol
            WHERE s.is_active = 1
        """
        params = []
        
        if rsi_min is not None:
            query += " AND sm.rsi_14 >= ?"
            params.append(rsi_min)
        if rsi_max is not None:
            query += " AND sm.rsi_14 <= ?"
            params.append(rsi_max)
        if trend:
            query += " AND sm.stock_trend = ?"
            params.append(trend)
        if adx_min is not None:
            query += " AND sm.adx >= ?"
            params.append(adx_min)
        
        query += " ORDER BY sp.market_cap DESC NULLS LAST LIMIT ?"
        params.append(limit)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Statistics & Health
    # =========================================
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        async with self.connection() as db:
            stats = {}
            
            # Count tables
            tables = ['stocks', 'stock_prices', 'price_history', 'financial_metrics']
            for table in tables:
                cursor = await db.execute(f"SELECT COUNT(*) as count FROM {table}")
                row = await cursor.fetchone()
                stats[f"{table}_count"] = row['count'] if row else 0
            
            # Last update time
            cursor = await db.execute(
                "SELECT MAX(updated_at) as last_update FROM stock_prices"
            )
            row = await cursor.fetchone()
            stats['last_price_update'] = row['last_update'] if row else None
            
            # Database file size
            db_path = Path(self.db_path)
            if db_path.exists():
                stats['database_size_mb'] = round(
                    db_path.stat().st_size / (1024 * 1024), 2
                )
            
            return stats
    
    async def get_data_freshness(self) -> str:
        """Check data freshness status."""
        async with self.connection() as db:
            cursor = await db.execute(
                "SELECT MAX(updated_at) as last_update FROM stock_prices"
            )
            row = await cursor.fetchone()
            
            if not row or not row['last_update']:
                return 'no_data'
            
            last_update = datetime.fromisoformat(row['last_update'])
            hours_old = (datetime.now() - last_update).total_seconds() / 3600
            
            if hours_old < settings.STALE_DATA_THRESHOLD_HOURS:
                return 'fresh'
            elif hours_old < settings.STALE_DATA_THRESHOLD_HOURS * 2:
                return 'stale'
            else:
                return 'outdated'
    
    # =========================================
    # Update Logging
    # =========================================
    
    async def log_update_start(self, update_type: str) -> int:
        """Log the start of an update operation."""
        query = """
            INSERT INTO update_logs (update_type, status, started_at)
            VALUES (?, 'started', ?)
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (update_type, datetime.now().isoformat()))
            await db.commit()
            return cursor.lastrowid
    
    async def log_update_complete(
        self,
        log_id: int,
        status: str,
        records_processed: int = 0,
        records_failed: int = 0,
        error_message: Optional[str] = None
    ):
        """Log the completion of an update operation."""
        started_at_query = "SELECT started_at FROM update_logs WHERE id = ?"
        
        async with self.connection() as db:
            cursor = await db.execute(started_at_query, (log_id,))
            row = await cursor.fetchone()
            
            duration = None
            if row and row['started_at']:
                started = datetime.fromisoformat(row['started_at'])
                duration = (datetime.now() - started).total_seconds()
            
            update_query = """
                UPDATE update_logs 
                SET status = ?, records_processed = ?, records_failed = ?,
                    error_message = ?, completed_at = ?, duration_seconds = ?
                WHERE id = ?
            """
            
            await db.execute(update_query, (
                status,
                records_processed,
                records_failed,
                error_message,
                datetime.now().isoformat(),
                duration,
                log_id
            ))
            await db.commit()
    
    # =========================================
    # Dividend History Operations
    # =========================================
    
    async def upsert_dividend_history(self, dividends: List[Dict[str, Any]]) -> int:
        """Insert or update dividend history records."""
        if not dividends:
            return 0
        
        query = """
            INSERT OR REPLACE INTO dividend_history 
            (symbol, ex_date, record_date, payment_date, 
             cash_dividend, stock_dividend, dividend_yield, fiscal_year)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    d.get('symbol'),
                    d.get('ex_date'),
                    d.get('record_date'),
                    d.get('payment_date'),
                    d.get('cash_dividend'),
                    d.get('stock_dividend'),
                    d.get('dividend_yield'),
                    d.get('fiscal_year'),
                )
                for d in dividends
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(dividends)} dividend records")
            return len(dividends)
    
    async def get_dividend_history(
        self, 
        symbol: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get dividend history for a symbol."""
        query = """
            SELECT * FROM dividend_history
            WHERE symbol = ?
            ORDER BY ex_date DESC
            LIMIT ?
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Company Ratings Operations
    # =========================================
    
    async def upsert_company_ratings(self, ratings: List[Dict[str, Any]]) -> int:
        """Insert or update company ratings."""
        if not ratings:
            return 0
        
        query = """
            INSERT OR REPLACE INTO company_ratings 
            (symbol, rating_type, rating_value, rating_grade, 
             criteria_scores, rating_date, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            import json
            params = [
                (
                    r.get('symbol'),
                    r.get('rating_type'),
                    r.get('rating_value'),
                    r.get('rating_grade'),
                    json.dumps(r.get('criteria_scores')) if r.get('criteria_scores') else None,
                    r.get('rating_date'),
                    datetime.now().isoformat(),
                )
                for r in ratings
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(ratings)} rating records")
            return len(ratings)
    
    async def get_company_ratings(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all ratings for a company."""
        query = """
            SELECT * FROM company_ratings
            WHERE symbol = ?
            ORDER BY rating_type
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Intraday Prices Operations  
    # =========================================
    
    async def upsert_intraday_prices(self, prices: List[Dict[str, Any]]) -> int:
        """Insert or update intraday price data."""
        if not prices:
            return 0
        
        query = """
            INSERT OR REPLACE INTO intraday_prices 
            (symbol, timestamp, price, volume, bid_price, ask_price, total_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    p.get('symbol'),
                    p.get('timestamp'),
                    p.get('price'),
                    p.get('volume'),
                    p.get('bid_price'),
                    p.get('ask_price'),
                    p.get('total_volume'),
                )
                for p in prices
            ]
            await db.executemany(query, params)
            await db.commit()
            
            return len(prices)
    
    async def get_intraday_prices(
        self, 
        symbol: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent intraday prices for a symbol."""
        query = """
            SELECT * FROM intraday_prices
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Market Indices Operations
    # =========================================
    
    async def upsert_market_indices(self, indices: List[Dict[str, Any]]) -> int:
        """Insert or update market index data."""
        if not indices:
            return 0
        
        query = """
            INSERT OR REPLACE INTO market_indices 
            (index_code, timestamp, value, change_value, change_percent,
             volume, total_value, advances, declines, unchanged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    idx.get('index_code'),
                    idx.get('timestamp'),
                    idx.get('value'),
                    idx.get('change_value'),
                    idx.get('change_percent'),
                    idx.get('volume'),
                    idx.get('total_value'),
                    idx.get('advances'),
                    idx.get('declines'),
                    idx.get('unchanged'),
                )
                for idx in indices
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(indices)} market index records")
            return len(indices)
    
    async def get_market_indices(self, index_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get latest market index values."""
        if index_code:
            query = """
                SELECT * FROM market_indices
                WHERE index_code = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """
            params = (index_code,)
        else:
            query = """
                SELECT m1.* FROM market_indices m1
                INNER JOIN (
                    SELECT index_code, MAX(timestamp) as max_ts
                    FROM market_indices
                    GROUP BY index_code
                ) m2 ON m1.index_code = m2.index_code AND m1.timestamp = m2.max_ts
            """
            params = ()
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Screener Metrics Operations (84 columns)
    # =========================================
    
    async def upsert_screener_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """Insert or update screener metrics (84 columns from TCBS Screener)."""
        if not metrics:
            return 0
        
        query = """
            INSERT OR REPLACE INTO screener_metrics 
            (symbol, exchange, industry, market_cap, pe_ratio, pb_ratio, ev_ebitda,
             eps, roe, dividend_yield, gross_margin, net_margin, doe,
             revenue_growth_1y, revenue_growth_5y, eps_growth_1y, eps_growth_5y,
             last_quarter_revenue_growth, last_quarter_profit_growth,
             rsi14, macd_histogram, price_vs_sma5, price_vs_sma10, price_vs_sma20,
             price_vs_sma50, price_vs_sma100, bolling_band_signal, dmi_signal, rsi14_status,
             vol_vs_sma5, vol_vs_sma10, vol_vs_sma20, vol_vs_sma50,
             avg_trading_value_5d, avg_trading_value_10d, avg_trading_value_20d,
             price_near_realtime, price_growth_1w, price_growth_1m,
             prev_1d_growth_pct, prev_1m_growth_pct, prev_1y_growth_pct, prev_5y_growth_pct,
             pct_away_from_hist_peak, pct_off_hist_bottom, pct_1y_from_peak, pct_1y_from_bottom,
             relative_strength_3d, rel_strength_1m, rel_strength_3m, rel_strength_1y,
             tc_rs, alpha, beta,
             stock_rating, business_operation, business_model, financial_health,
             tcbs_recommend, tcbs_buy_sell_signal,
             foreign_vol_pct, foreign_transaction, foreign_buysell_20s,
             uptrend, breakout, price_break_out52_week, heating_up,
             num_increase_continuous_day, num_decrease_continuous_day,
             profit_last_4q, free_transfer_rate, net_cash_per_market_cap,
             net_cash_per_total_assets, has_financial_report, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    m.get('symbol'),
                    m.get('exchange'),
                    m.get('industry'),
                    m.get('market_cap'),
                    m.get('pe_ratio'),
                    m.get('pb_ratio'),
                    m.get('ev_ebitda'),
                    m.get('eps'),
                    m.get('roe'),
                    m.get('dividend_yield'),
                    m.get('gross_margin'),
                    m.get('net_margin'),
                    m.get('doe'),
                    m.get('revenue_growth_1y'),
                    m.get('revenue_growth_5y'),
                    m.get('eps_growth_1y'),
                    m.get('eps_growth_5y'),
                    m.get('last_quarter_revenue_growth'),
                    m.get('last_quarter_profit_growth'),
                    m.get('rsi14'),
                    m.get('macd_histogram'),
                    m.get('price_vs_sma5'),
                    m.get('price_vs_sma10'),
                    m.get('price_vs_sma20'),
                    m.get('price_vs_sma50'),
                    m.get('price_vs_sma100'),
                    m.get('bolling_band_signal'),
                    m.get('dmi_signal'),
                    m.get('rsi14_status'),
                    m.get('vol_vs_sma5'),
                    m.get('vol_vs_sma10'),
                    m.get('vol_vs_sma20'),
                    m.get('vol_vs_sma50'),
                    m.get('avg_trading_value_5d'),
                    m.get('avg_trading_value_10d'),
                    m.get('avg_trading_value_20d'),
                    m.get('price_near_realtime'),
                    m.get('price_growth_1w'),
                    m.get('price_growth_1m'),
                    m.get('prev_1d_growth_pct'),
                    m.get('prev_1m_growth_pct'),
                    m.get('prev_1y_growth_pct'),
                    m.get('prev_5y_growth_pct'),
                    m.get('pct_away_from_hist_peak'),
                    m.get('pct_off_hist_bottom'),
                    m.get('pct_1y_from_peak'),
                    m.get('pct_1y_from_bottom'),
                    m.get('relative_strength_3d'),
                    m.get('rel_strength_1m'),
                    m.get('rel_strength_3m'),
                    m.get('rel_strength_1y'),
                    m.get('tc_rs'),
                    m.get('alpha'),
                    m.get('beta'),
                    m.get('stock_rating'),
                    m.get('business_operation'),
                    m.get('business_model'),
                    m.get('financial_health'),
                    m.get('tcbs_recommend'),
                    m.get('tcbs_buy_sell_signal'),
                    m.get('foreign_vol_pct'),
                    m.get('foreign_transaction'),
                    m.get('foreign_buysell_20s'),
                    m.get('uptrend'),
                    m.get('breakout'),
                    m.get('price_break_out52_week'),
                    m.get('heating_up'),
                    m.get('num_increase_continuous_day'),
                    m.get('num_decrease_continuous_day'),
                    m.get('profit_last_4q'),
                    m.get('free_transfer_rate'),
                    m.get('net_cash_per_market_cap'),
                    m.get('net_cash_per_total_assets'),
                    m.get('has_financial_report'),
                    datetime.now().isoformat(),
                )
                for m in metrics
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(metrics)} screener metric records")
            return len(metrics)
    
    async def get_screener_metrics(
        self,
        exchange: Optional[str] = None,
        industry: Optional[str] = None,
        pe_min: Optional[float] = None,
        pe_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get screener metrics with optional filters."""
        query = "SELECT * FROM screener_metrics WHERE 1=1"
        params = []
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        if industry:
            query += " AND industry LIKE ?"
            params.append(f"%{industry}%")
        if pe_min is not None:
            query += " AND pe_ratio >= ?"
            params.append(pe_min)
        if pe_max is not None:
            query += " AND pe_ratio <= ?"
            params.append(pe_max)
        if roe_min is not None:
            query += " AND roe >= ?"
            params.append(roe_min)
        if rsi_min is not None:
            query += " AND rsi14 >= ?"
            params.append(rsi_min)
        if rsi_max is not None:
            query += " AND rsi14 <= ?"
            params.append(rsi_max)
        
        query += " ORDER BY market_cap DESC NULLS LAST LIMIT ?"
        params.append(limit)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def get_stocks_with_screener_data(
        self,
        # Basic filters
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        search: Optional[str] = None,
        # General metrics
        market_cap_min: Optional[float] = None,
        market_cap_max: Optional[float] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        price_change_min: Optional[float] = None,
        price_change_max: Optional[float] = None,
        adtv_value_min: Optional[float] = None,
        volume_vs_adtv_min: Optional[float] = None,
        # Technical signals
        stock_rating_min: Optional[float] = None,  # Stock Strength
        rs_min: Optional[float] = None,  # Relative Strength
        rs_max: Optional[float] = None,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        price_vs_sma20_min: Optional[float] = None,
        price_vs_sma20_max: Optional[float] = None,
        macd_histogram_min: Optional[float] = None,
        adx_min: Optional[float] = None,
        stock_trend: Optional[str] = None,  # 'uptrend', 'breakout', etc.
        price_return_1m_min: Optional[float] = None,
        price_return_1m_max: Optional[float] = None,
        price_return_3m_min: Optional[float] = None,
        # Financial indicators
        pe_min: Optional[float] = None,
        pe_max: Optional[float] = None,
        pb_min: Optional[float] = None,
        pb_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        roe_max: Optional[float] = None,
        revenue_growth_min: Optional[float] = None,
        npat_growth_min: Optional[float] = None,
        net_margin_min: Optional[float] = None,
        gross_margin_min: Optional[float] = None,
        dividend_yield_min: Optional[float] = None,
        # Pagination
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get comprehensive stock data by joining stocks, stock_prices, and screener_metrics.
        
        Returns all metrics needed for advanced screening:
        - General: market_cap, price, price_change, adtv
        - Technical: rsi, macd, stock_rating, relative_strength, trends
        - Financial: pe, pb, roe, margins, growth rates
        """
        query = """
            SELECT 
                s.symbol,
                s.company_name,
                s.exchange,
                s.sector,
                s.industry,
                -- Price data (prefer screener_metrics for fresh data)
                COALESCE(sm.price_near_realtime, sp.current_price) as current_price,
                sp.price_change,
                COALESCE(sm.prev_1d_growth_pct, sp.percent_change) as percent_change,
                sp.volume,
                -- General metrics
                COALESCE(sm.market_cap, sp.market_cap) as market_cap,
                sm.avg_trading_value_20d as adtv_value,
                sm.vol_vs_sma20 as volume_vs_adtv,
                -- Technical signals
                sm.stock_rating,
                sm.rel_strength_3m as relative_strength,
                sm.tc_rs,
                sm.rsi14 as rsi,
                sm.rsi14_status,
                sm.price_vs_sma5,
                sm.price_vs_sma10,
                sm.price_vs_sma20,
                sm.price_vs_sma50,
                sm.price_vs_sma100,
                sm.macd_histogram,
                sm.bolling_band_signal,
                sm.dmi_signal,
                sm.uptrend,
                sm.breakout,
                sm.price_break_out52_week,
                sm.heating_up,
                -- Price performance
                sm.price_growth_1w,
                sm.price_growth_1m,
                sm.prev_1m_growth_pct as price_return_1m,
                sm.rel_strength_1m as price_return_outperform_1m,
                sm.prev_1y_growth_pct as price_return_1y,
                sm.pct_away_from_hist_peak,
                sm.pct_off_hist_bottom,
                -- Financial indicators
                COALESCE(sm.pe_ratio, sp.pe_ratio) as pe_ratio,
                COALESCE(sm.pb_ratio, sp.pb_ratio) as pb_ratio,
                COALESCE(sm.roe, sp.roe) as roe,
                sm.eps,
                sm.dividend_yield,
                sm.gross_margin,
                sm.net_margin,
                sm.doe as debt_equity,
                -- Growth metrics
                sm.revenue_growth_1y,
                sm.eps_growth_1y,
                sm.last_quarter_revenue_growth,
                sm.last_quarter_profit_growth as npat_growth,
                -- TCBS ratings
                sm.financial_health,
                sm.business_model,
                sm.business_operation,
                sm.tcbs_recommend,
                -- Foreign activity
                sm.foreign_vol_pct,
                sm.foreign_buysell_20s,
                -- Metadata
                sm.updated_at as screener_updated_at
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            LEFT JOIN screener_metrics sm ON s.symbol = sm.symbol
            WHERE s.is_active = 1
        """
        params = []
        
        # Basic filters
        if exchange:
            query += " AND s.exchange = ?"
            params.append(exchange)
        if sector:
            query += " AND s.sector = ?"
            params.append(sector)
        if industry:
            query += " AND sm.industry LIKE ?"
            params.append(f"%{industry}%")
        if search:
            query += " AND (s.symbol LIKE ? OR s.company_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        # General metrics
        if market_cap_min is not None:
            query += " AND COALESCE(sm.market_cap, sp.market_cap) >= ?"
            params.append(market_cap_min)
        if market_cap_max is not None:
            query += " AND COALESCE(sm.market_cap, sp.market_cap) <= ?"
            params.append(market_cap_max)
        if price_min is not None:
            query += " AND COALESCE(sm.price_near_realtime, sp.current_price) >= ?"
            params.append(price_min)
        if price_max is not None:
            query += " AND COALESCE(sm.price_near_realtime, sp.current_price) <= ?"
            params.append(price_max)
        if price_change_min is not None:
            query += " AND sm.prev_1d_growth_pct >= ?"
            params.append(price_change_min)
        if price_change_max is not None:
            query += " AND sm.prev_1d_growth_pct <= ?"
            params.append(price_change_max)
        if adtv_value_min is not None:
            query += " AND sm.avg_trading_value_20d >= ?"
            params.append(adtv_value_min)
        if volume_vs_adtv_min is not None:
            query += " AND sm.vol_vs_sma20 >= ?"
            params.append(volume_vs_adtv_min)
        
        # Technical signals
        if stock_rating_min is not None:
            query += " AND sm.stock_rating >= ?"
            params.append(stock_rating_min)
        if rs_min is not None:
            query += " AND sm.rel_strength_3m >= ?"
            params.append(rs_min)
        if rs_max is not None:
            query += " AND sm.rel_strength_3m <= ?"
            params.append(rs_max)
        if rsi_min is not None:
            query += " AND sm.rsi14 >= ?"
            params.append(rsi_min)
        if rsi_max is not None:
            query += " AND sm.rsi14 <= ?"
            params.append(rsi_max)
        if price_vs_sma20_min is not None:
            query += " AND sm.price_vs_sma20 >= ?"
            params.append(price_vs_sma20_min)
        if price_vs_sma20_max is not None:
            query += " AND sm.price_vs_sma20 <= ?"
            params.append(price_vs_sma20_max)
        if macd_histogram_min is not None:
            query += " AND sm.macd_histogram >= ?"
            params.append(macd_histogram_min)
        if adx_min is not None:
            # Note: ADX not in screener_metrics, would need stock_metrics table
            pass
        if stock_trend == 'uptrend':
            query += " AND sm.uptrend = 1"
        elif stock_trend == 'breakout':
            query += " AND sm.breakout = 1"
        elif stock_trend == 'heating_up':
            query += " AND sm.heating_up = 1"
        if price_return_1m_min is not None:
            query += " AND sm.prev_1m_growth_pct >= ?"
            params.append(price_return_1m_min)
        if price_return_1m_max is not None:
            query += " AND sm.prev_1m_growth_pct <= ?"
            params.append(price_return_1m_max)
        if price_return_3m_min is not None:
            query += " AND sm.rel_strength_3m >= ?"
            params.append(price_return_3m_min)
        
        # Financial indicators
        if pe_min is not None:
            query += " AND COALESCE(sm.pe_ratio, sp.pe_ratio) >= ?"
            params.append(pe_min)
        if pe_max is not None:
            query += " AND COALESCE(sm.pe_ratio, sp.pe_ratio) <= ?"
            params.append(pe_max)
        if pb_min is not None:
            query += " AND COALESCE(sm.pb_ratio, sp.pb_ratio) >= ?"
            params.append(pb_min)
        if pb_max is not None:
            query += " AND COALESCE(sm.pb_ratio, sp.pb_ratio) <= ?"
            params.append(pb_max)
        if roe_min is not None:
            query += " AND COALESCE(sm.roe, sp.roe) >= ?"
            params.append(roe_min)
        if roe_max is not None:
            query += " AND COALESCE(sm.roe, sp.roe) <= ?"
            params.append(roe_max)
        if revenue_growth_min is not None:
            query += " AND sm.revenue_growth_1y >= ?"
            params.append(revenue_growth_min)
        if npat_growth_min is not None:
            query += " AND sm.last_quarter_profit_growth >= ?"
            params.append(npat_growth_min)
        if net_margin_min is not None:
            query += " AND sm.net_margin >= ?"
            params.append(net_margin_min)
        if gross_margin_min is not None:
            query += " AND sm.gross_margin >= ?"
            params.append(gross_margin_min)
        if dividend_yield_min is not None:
            query += " AND sm.dividend_yield >= ?"
            params.append(dividend_yield_min)
        
        query += " ORDER BY COALESCE(sm.market_cap, sp.market_cap) DESC NULLS LAST"
        query += f" LIMIT {limit} OFFSET {offset}"
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    async def count_stocks_with_screener_data(
        self,
        exchange: Optional[str] = None,
        sector: Optional[str] = None,
        search: Optional[str] = None,
        # Add same filters as above for accurate count
        pe_min: Optional[float] = None,
        pe_max: Optional[float] = None,
        pb_min: Optional[float] = None,
        pb_max: Optional[float] = None,
        roe_min: Optional[float] = None,
        rsi_min: Optional[float] = None,
        rsi_max: Optional[float] = None,
        market_cap_min: Optional[float] = None,
    ) -> int:
        """Count stocks matching screener filters."""
        query = """
            SELECT COUNT(*) as count
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            LEFT JOIN screener_metrics sm ON s.symbol = sm.symbol
            WHERE s.is_active = 1
        """
        params = []
        
        if exchange:
            query += " AND s.exchange = ?"
            params.append(exchange)
        if sector:
            query += " AND s.sector = ?"
            params.append(sector)
        if search:
            query += " AND (s.symbol LIKE ? OR s.company_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        if pe_min is not None:
            query += " AND COALESCE(sm.pe_ratio, sp.pe_ratio) >= ?"
            params.append(pe_min)
        if pe_max is not None:
            query += " AND COALESCE(sm.pe_ratio, sp.pe_ratio) <= ?"
            params.append(pe_max)
        if pb_min is not None:
            query += " AND COALESCE(sm.pb_ratio, sp.pb_ratio) >= ?"
            params.append(pb_min)
        if pb_max is not None:
            query += " AND COALESCE(sm.pb_ratio, sp.pb_ratio) <= ?"
            params.append(pb_max)
        if roe_min is not None:
            query += " AND COALESCE(sm.roe, sp.roe) >= ?"
            params.append(roe_min)
        if rsi_min is not None:
            query += " AND sm.rsi14 >= ?"
            params.append(rsi_min)
        if rsi_max is not None:
            query += " AND sm.rsi14 <= ?"
            params.append(rsi_max)
        if market_cap_min is not None:
            query += " AND COALESCE(sm.market_cap, sp.market_cap) >= ?"
            params.append(market_cap_min)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            return row['count'] if row else 0
    
    # =========================================
    # Shareholders Operations
    # =========================================
    
    async def upsert_shareholders(self, shareholders: List[Dict[str, Any]]) -> int:
        """Insert or update shareholder records."""
        if not shareholders:
            return 0
        
        query = """
            INSERT OR REPLACE INTO shareholders 
            (symbol, shareholder_id, shareholder_name, quantity, 
             ownership_percent, update_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    s.get('symbol'),
                    s.get('shareholder_id'),
                    s.get('shareholder_name'),
                    s.get('quantity'),
                    s.get('ownership_percent'),
                    s.get('update_date'),
                )
                for s in shareholders
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.debug(f"📥 Upserted {len(shareholders)} shareholder records")
            return len(shareholders)
    
    async def get_shareholders(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all shareholders for a symbol."""
        query = """
            SELECT * FROM shareholders
            WHERE symbol = ?
            ORDER BY ownership_percent DESC
        """
        
        async with self.connection() as db:
            cursor = await db.execute(query, (symbol,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Officers Operations
    # =========================================
    
    async def upsert_officers(self, officers: List[Dict[str, Any]]) -> int:
        """Insert or update officer records."""
        if not officers:
            return 0
        
        query = """
            INSERT OR REPLACE INTO officers 
            (symbol, officer_id, officer_name, position, position_short,
             ownership_percent, quantity, status, update_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    o.get('symbol'),
                    o.get('officer_id'),
                    o.get('officer_name'),
                    o.get('position'),
                    o.get('position_short'),
                    o.get('ownership_percent'),
                    o.get('quantity'),
                    o.get('status'),
                    o.get('update_date'),
                )
                for o in officers
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.debug(f"📥 Upserted {len(officers)} officer records")
            return len(officers)
    
    async def get_officers(self, symbol: str, status: str = 'working') -> List[Dict[str, Any]]:
        """Get officers for a symbol by status."""
        query = """
            SELECT * FROM officers
            WHERE symbol = ?
        """
        params = [symbol]
        
        if status != 'all':
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY ownership_percent DESC"
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
    
    # =========================================
    # Price Board Operations (Real-time Bid/Ask)
    # =========================================
    
    async def upsert_price_board(self, data: List[Dict[str, Any]]) -> int:
        """Insert or update real-time price board data."""
        if not data:
            return 0
        
        query = """
            INSERT OR REPLACE INTO price_board 
            (symbol, exchange, ceiling, floor, ref_price, prior_close,
             match_price, match_volume, accumulated_volume, accumulated_value,
             avg_match_price, highest, lowest,
             foreign_buy_volume, foreign_sell_volume, current_room, total_room,
             bid_1_price, bid_1_volume, bid_2_price, bid_2_volume, bid_3_price, bid_3_volume,
             ask_1_price, ask_1_volume, ask_2_price, ask_2_volume, ask_3_price, ask_3_volume,
             updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        async with self.connection() as db:
            params = [
                (
                    d.get('symbol'),
                    d.get('exchange'),
                    d.get('ceiling'),
                    d.get('floor'),
                    d.get('ref_price'),
                    d.get('prior_close'),
                    d.get('match_price'),
                    d.get('match_volume'),
                    d.get('accumulated_volume'),
                    d.get('accumulated_value'),
                    d.get('avg_match_price'),
                    d.get('highest'),
                    d.get('lowest'),
                    d.get('foreign_buy_volume'),
                    d.get('foreign_sell_volume'),
                    d.get('current_room'),
                    d.get('total_room'),
                    d.get('bid_1_price'),
                    d.get('bid_1_volume'),
                    d.get('bid_2_price'),
                    d.get('bid_2_volume'),
                    d.get('bid_3_price'),
                    d.get('bid_3_volume'),
                    d.get('ask_1_price'),
                    d.get('ask_1_volume'),
                    d.get('ask_2_price'),
                    d.get('ask_2_volume'),
                    d.get('ask_3_price'),
                    d.get('ask_3_volume'),
                    d.get('updated_at', datetime.now().isoformat()),
                )
                for d in data
            ]
            await db.executemany(query, params)
            await db.commit()
            
            logger.info(f"📥 Upserted {len(data)} price board records")
            return len(data)
    
    async def get_price_board(
        self,
        symbols: Optional[List[str]] = None,
        exchange: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get price board data."""
        query = "SELECT * FROM price_board WHERE 1=1"
        params = []
        
        if symbols:
            placeholders = ','.join(['?' for _ in symbols])
            query += f" AND symbol IN ({placeholders})"
            params.extend(symbols)
        
        if exchange:
            query += " AND exchange = ?"
            params.append(exchange)
        
        query += " ORDER BY accumulated_value DESC NULLS LAST LIMIT ?"
        params.append(limit)
        
        async with self.connection() as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# Global database instance
_db: Optional[Database] = None


async def get_database(db_path: Optional[str] = None) -> Database:
    """Get or create the global database instance."""
    global _db
    
    if _db is None:
        _db = Database(db_path)
        await _db.initialize()
    
    return _db
