
"""
Calculate percent_change from price history for all stocks.
This uses existing price_history data to compute real percent changes.
"""

import asyncio
import sqlite3
from datetime import datetime
from loguru import logger

def calculate_percent_changes():
    """Calculate percent_change from price_history for all stocks."""
    logger.info("🧮 Calculating percent_change from price history...")
    
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    
    # Get stocks with price history
    cursor.execute("""
        SELECT DISTINCT symbol FROM price_history
    """)
    symbols = [row[0] for row in cursor.fetchall()]
    
    logger.info(f"📊 Found {len(symbols)} stocks with price history")
    
    updated = 0
    for symbol in symbols:
        try:
            # Get last 2 days of price history
            cursor.execute("""
                SELECT date, close_price FROM price_history
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 2
            """, (symbol,))
            rows = cursor.fetchall()
            
            if len(rows) >= 2:
                today_close = rows[0][1]
                yesterday_close = rows[1][1]
                
                if yesterday_close and yesterday_close > 0:
                    percent_change = ((today_close - yesterday_close) / yesterday_close) * 100
                    price_change = today_close - yesterday_close
                    
                    cursor.execute("""
                        UPDATE stock_prices SET
                            current_price = ?,
                            price_change = ?,
                            percent_change = ?,
                            updated_at = ?
                        WHERE symbol = ?
                    """, (
                        today_close,
                        round(price_change, 2),
                        round(percent_change, 2),
                        datetime.now().isoformat(),
                        symbol
                    ))
                    updated += 1
                    
        except Exception as e:
            logger.error(f"❌ {symbol}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"✅ Updated percent_change for {updated} stocks")
    
    # Verify
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change > 0")
    positive = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change < 0")
    negative = cursor.fetchone()[0]
    conn.close()
    
    logger.info(f"📈 Positive: {positive}, 📉 Negative: {negative}")

if __name__ == "__main__":
    calculate_percent_changes()
