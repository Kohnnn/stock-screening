"""
Backfill missing data for VnStock Screener.

Calculates and populates:
- percent_change from price_history
- RS Rating from 1yr price return
- Runs batch price history collection
"""

import sqlite3
from datetime import datetime, timedelta
from loguru import logger
import sys

# Add backend path
sys.path.insert(0, '/app')
import technical_indicators as ti


DB_PATH = "./data/vnstock_data.db"


def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def backfill_percent_change():
    """
    Calculate percent_change from price_history for stocks missing this value.
    Uses the last 2 trading days to compute change.
    """
    logger.info("📊 Backfilling percent_change from price_history...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all active stocks
    cursor.execute("SELECT symbol FROM stocks WHERE is_active = 1")
    symbols = [row['symbol'] for row in cursor.fetchall()]
    
    updated = 0
    
    for symbol in symbols:
        # Get last 2 price history records
        cursor.execute("""
            SELECT close_price 
            FROM price_history 
            WHERE symbol = ? 
            ORDER BY date DESC 
            LIMIT 2
        """, (symbol,))
        
        rows = cursor.fetchall()
        
        if len(rows) >= 2:
            current_price = rows[0]['close_price']
            prev_price = rows[1]['close_price']
            
            if prev_price and prev_price > 0:
                pct_change = ((current_price - prev_price) / prev_price) * 100
                price_change = current_price - prev_price
                
                # Update stock_prices table
                cursor.execute("""
                    UPDATE stock_prices 
                    SET percent_change = ?, price_change = ?
                    WHERE symbol = ?
                """, (round(pct_change, 2), round(price_change, 2), symbol))
                
                updated += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated percent_change for {updated} stocks")
    return updated


def backfill_rs_rating():
    """
    Calculate RS Rating (Relative Strength) from 1-year price return.
    RS Rating is a percentile ranking of price performance.
    """
    logger.info("📊 Backfilling RS Rating...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all active stocks
    cursor.execute("SELECT symbol FROM stocks WHERE is_active = 1")
    symbols = [row['symbol'] for row in cursor.fetchall()]
    
    returns_1y = []
    
    for symbol in symbols:
        # Get price history (need ~250 trading days for 1 year)
        cursor.execute("""
            SELECT close_price 
            FROM price_history 
            WHERE symbol = ? 
            ORDER BY date ASC
        """, (symbol,))
        
        rows = cursor.fetchall()
        closes = [row['close_price'] for row in rows]
        
        if len(closes) >= 50:  # At least 50 days for meaningful calculation
            # Calculate return over available period
            days = min(len(closes) - 1, 250)  # Up to 1 year
            ret = ti.calculate_price_return(closes, days)
            
            if ret is not None:
                returns_1y.append({'symbol': symbol, 'ret': ret})
    
    # Calculate RS Rating (percentile ranking)
    if not returns_1y:
        logger.warning("⚠️ No stocks with sufficient price history for RS Rating")
        conn.close()
        return 0
    
    returns_1y.sort(key=lambda x: x['ret'])
    count = len(returns_1y)
    
    updated = 0
    for i, item in enumerate(returns_1y):
        # RS Rating 1-99
        rs_rating = int(((i + 1) / count) * 99)
        if rs_rating < 1:
            rs_rating = 1
        
        # Update screener_metrics
        cursor.execute("""
            INSERT OR REPLACE INTO screener_metrics (symbol, tc_rs, rel_strength_1y)
            VALUES (?, ?, ?)
        """, (item['symbol'], rs_rating, round(item['ret'], 2)))
        
        updated += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated RS Rating for {updated} stocks")
    return updated


def update_trend_classification():
    """
    Update stock_trend based on EMAs and RSI.
    """
    logger.info("📊 Updating trend classifications...")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get stocks with technical indicators
    cursor.execute("""
        SELECT symbol, ema_20, ema_50, ema_200, rsi_14
        FROM stock_metrics
        WHERE ema_20 IS NOT NULL
    """)
    
    rows = cursor.fetchall()
    updated = 0
    
    for row in rows:
        # Get current price
        cursor.execute("""
            SELECT current_price FROM stock_prices WHERE symbol = ?
        """, (row['symbol'],))
        
        price_row = cursor.fetchone()
        if not price_row:
            continue
        
        current_price = price_row['current_price']
        
        # Classify trend
        trend = ti.classify_trend(
            ema_20=row['ema_20'],
            ema_50=row['ema_50'],
            ema_200=row['ema_200'],
            rsi=row['rsi_14'],
            current_price=current_price
        )
        
        if trend and trend != 'unknown':
            cursor.execute("""
                UPDATE stock_metrics SET stock_trend = ? WHERE symbol = ?
            """, (trend, row['symbol']))
            updated += 1
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated trend for {updated} stocks")
    return updated


def get_stats():
    """Get current data coverage stats."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total stocks
    cursor.execute("SELECT COUNT(*) as cnt FROM stocks WHERE is_active = 1")
    total = cursor.fetchone()['cnt']
    
    # With percent_change
    cursor.execute("SELECT COUNT(*) as cnt FROM stock_prices WHERE percent_change IS NOT NULL")
    with_pct = cursor.fetchone()['cnt']
    
    # With RS Rating
    cursor.execute("SELECT COUNT(*) as cnt FROM screener_metrics WHERE tc_rs IS NOT NULL")
    with_rs = cursor.fetchone()['cnt']
    
    # With RSI
    cursor.execute("SELECT COUNT(*) as cnt FROM stock_metrics WHERE rsi_14 IS NOT NULL")
    with_rsi = cursor.fetchone()['cnt']
    
    # With price history
    cursor.execute("SELECT COUNT(DISTINCT symbol) as cnt FROM price_history")
    with_history = cursor.fetchone()['cnt']
    
    conn.close()
    
    return {
        'total_stocks': total,
        'with_percent_change': with_pct,
        'with_rs_rating': with_rs,
        'with_rsi': with_rsi,
        'with_price_history': with_history
    }


def run_all_backfills():
    """Run all backfill operations."""
    logger.info("=" * 60)
    logger.info("VnStock Data Backfill")
    logger.info("=" * 60)
    
    # Show before stats
    stats_before = get_stats()
    logger.info(f"Before: {stats_before}")
    
    # Run backfills
    backfill_percent_change()
    backfill_rs_rating()
    update_trend_classification()
    
    # Show after stats
    stats_after = get_stats()
    logger.info(f"After: {stats_after}")
    
    logger.info("=" * 60)
    logger.info("Backfill Complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_all_backfills()
