
"""
Simple synchronous price updater using vnstock.
Updates percent_change for priority stocks to enable "Tăng giá mạnh" highlights.
"""

import sqlite3
from datetime import datetime
from loguru import logger
from vnstock import Vnstock

# Top stocks
PRIORITY_SYMBOLS = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]

def update_prices():
    """Update prices using vnstock synchronously."""
    logger.info("🚀 Starting synchronous price update...")
    
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    
    vn = Vnstock()
    updated = 0
    failed = 0
    
    for symbol in PRIORITY_SYMBOLS:
        try:
            stock = vn.stock(symbol=symbol, source='VCI')
            df = stock.quote.history(days=5)
            
            if df is not None and len(df) >= 2:
                latest = df.iloc[-1]
                previous = df.iloc[-2]
                
                current_price = float(latest.get('close', 0))
                prev_close = float(previous.get('close', 0))
                
                if prev_close > 0:
                    price_change = current_price - prev_close
                    percent_change = round((price_change / prev_close) * 100, 2)
                else:
                    price_change = 0
                    percent_change = 0
                
                cursor.execute("""
                    UPDATE stock_prices SET 
                        current_price = ?,
                        price_change = ?,
                        percent_change = ?,
                        volume = ?,
                        updated_at = ?
                    WHERE symbol = ?
                """, (
                    current_price,
                    price_change,
                    percent_change,
                    int(latest.get('volume', 0)),
                    datetime.now().isoformat(),
                    symbol
                ))
                conn.commit()
                
                updated += 1
                logger.info(f"✅ {symbol}: {current_price} ({percent_change:+.2f}%)")
            else:
                failed += 1
                logger.warning(f"⚠️ {symbol}: No data")
                
        except Exception as e:
            failed += 1
            logger.error(f"❌ {symbol}: {str(e)[:50]}")
        
        # Rate limit
        import time
        time.sleep(0.5)
    
    conn.close()
    logger.info(f"\n🏁 Complete! Updated: {updated}, Failed: {failed}")
    
    # Check results
    conn = sqlite3.connect("./data/vnstock_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change > 0")
    positive = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM stock_prices WHERE percent_change < 0")
    negative = cursor.fetchone()[0]
    conn.close()
    
    logger.info(f"📈 Stocks with positive change: {positive}")
    logger.info(f"📉 Stocks with negative change: {negative}")

if __name__ == "__main__":
    update_prices()
