import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import technical_indicators as ti

class MetricsCalculator:
    """
    Calculates derived financial metrics from raw data.
    """
    
    def __init__(self, db_path: str = "./data/vnstock_data.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def calculate_all_metrics(self) -> int:
        """
        Calculate all derived metrics (financial + technical) for stocks.
        Returns number of stocks updated.
        """
        financial_count = self.calculate_financial_metrics()
        technical_count = self.calculate_technicals()
        screener_count = self.calculate_screener_backfill()
        return financial_count + technical_count + screener_count

    def calculate_financial_metrics(self) -> int:
        """
        Calculate derived financial metrics (PE, PS, Debt/Equity, etc.)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updated = 0
        
        # Get stocks with raw data
        cursor.execute("""
            SELECT symbol, current_price, market_cap, total_debt, total_assets,
                   owner_equity, cash, revenue, profit, eps
            FROM stock_prices
            WHERE current_price IS NOT NULL AND current_price > 0
        """)
        
        stocks = cursor.fetchall()
        
        for stock in stocks:
            symbol = stock['symbol']
            updates = {}
            
            # Calculate debt_to_equity if not present
            if stock['total_debt'] and stock['owner_equity'] and stock['owner_equity'] > 0:
                debt_to_equity = stock['total_debt'] / stock['owner_equity']
                updates['debt_to_equity'] = round(debt_to_equity, 2)
            
            # Calculate equity_to_assets
            if stock['owner_equity'] and stock['total_assets'] and stock['total_assets'] > 0:
                equity_to_assets = stock['owner_equity'] / stock['total_assets']
                updates['equity_to_assets'] = round(equity_to_assets * 100, 2)  # As percentage
            
            # Calculate price_to_sales (PS ratio) if not present
            if stock['market_cap'] and stock['revenue'] and stock['revenue'] > 0:
                ps_ratio = stock['market_cap'] / stock['revenue']
                updates['ps_ratio'] = round(ps_ratio, 2)
            
            # Calculate PE ratio if not present but we have EPS
            current_price = stock['current_price']
            if current_price and stock['eps'] and stock['eps'] > 0:
                pe_ratio = current_price / stock['eps']
                updates['pe_ratio'] = round(pe_ratio, 2)
            
            if updates:
                set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
                values = list(updates.values()) + [symbol]
                
                cursor.execute(f"""
                    UPDATE stock_prices
                    SET {set_clause}
                    WHERE symbol = ?
                """, values)
                
                updated += 1
        
        conn.commit()
        conn.close()
        
        logger.info(f"📊 Updated financial metrics for {updated} stocks")
        return updated

    def calculate_technicals(self) -> int:
        """
        Calculate technical indicators (RSI, MACD, Trend) and save to stock_metrics.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Ensure stock_metrics table exists (handled by schema, but good to be safe)
        
        # Get all active stocks
        cursor.execute("SELECT symbol FROM stocks WHERE is_active = 1")
        symbols = [row['symbol'] for row in cursor.fetchall()]
        
        updated_count = 0
        
        for symbol in symbols:
            # Get price history
            cursor.execute("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM price_history
                WHERE symbol = ?
                ORDER BY date ASC
            """, (symbol,))
            
            history = [dict(row) for row in cursor.fetchall()]
            
            if not history or len(history) < 14:
                continue
                
            # Calculate indicators using technical_indicators module
            indicators = ti.calculate_all_indicators(history)
            
            if not indicators:
                continue
                
            # Prepare upsert into stock_metrics
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO stock_metrics (
                        symbol, 
                        rsi_14, macd, macd_signal, macd_histogram, adx,
                        ema_20, ema_50, ema_200,
                        price_vs_ema20, ema20_vs_ema50, ema50_vs_ema200,
                        price_return_1m, price_return_3m, price_fluctuation,
                        adtv_shares, adtv_value, volume_vs_adtv,
                        stock_trend, updated_at
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, CURRENT_TIMESTAMP
                    )
                """, (
                    symbol,
                    indicators.get('rsi_14'),
                    indicators.get('macd'),
                    indicators.get('macd_signal'),
                    indicators.get('macd_histogram'),
                    indicators.get('adx'),
                    indicators.get('ema_20'),
                    indicators.get('ema_50'),
                    indicators.get('ema_200'),
                    indicators.get('price_vs_ema20'),
                    indicators.get('ema20_vs_ema50'),
                    indicators.get('ema50_vs_ema200'),
                    indicators.get('price_return_1m'),
                    indicators.get('price_return_3m'),
                    indicators.get('price_fluctuation'),
                    indicators.get('adtv_shares'),
                    indicators.get('adtv_value'),
                    indicators.get('volume_vs_adtv'),
                    indicators.get('stock_trend')
                ))
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating technicals for {symbol}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"📈 Updated technical indicators for {updated_count} stocks")
        return updated_count
    
    def calculate_enterprise_value(self, symbol: str) -> Optional[float]:
        """
        Calculate Enterprise Value: Market Cap + Total Debt - Cash
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT market_cap, total_debt, cash
            FROM stock_prices
            WHERE symbol = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        market_cap = row['market_cap'] or 0
        total_debt = row['total_debt'] or 0
        cash = row['cash'] or 0
        
        ev = market_cap + total_debt - cash
        return ev if ev > 0 else None
    
    def get_sector_averages(self, sector: str) -> Dict[str, float]:
        """
        Get average metrics for a sector (for peer comparison).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                AVG(sp.pe_ratio) as avg_pe,
                AVG(sp.pb_ratio) as avg_pb,
                AVG(sp.roe) as avg_roe,
                AVG(sp.roa) as avg_roa,
                AVG(sp.market_cap) as avg_market_cap,
                COUNT(*) as stock_count
            FROM stock_prices sp
            JOIN stocks s ON sp.symbol = s.symbol
            WHERE s.sector = ? AND sp.pe_ratio > 0
        """, (sector,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {}
        
        return {
            'avg_pe': round(row['avg_pe'], 2) if row['avg_pe'] else None,
            'avg_pb': round(row['avg_pb'], 2) if row['avg_pb'] else None,
            'avg_roe': round(row['avg_roe'], 2) if row['avg_roe'] else None,
            'avg_roa': round(row['avg_roa'], 2) if row['avg_roa'] else None,
            'avg_market_cap': round(row['avg_market_cap'], 2) if row['avg_market_cap'] else None,
            'stock_count': row['stock_count']
        }
    
    def get_peer_comparison(self, symbol: str) -> Dict[str, Any]:
        """
        Compare a stock with its sector peers.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get stock info with sector
        cursor.execute("""
            SELECT s.symbol, s.company_name, s.sector, s.industry,
                   sp.pe_ratio, sp.pb_ratio, sp.roe, sp.roa, sp.market_cap,
                   sp.current_price, sp.eps
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE s.symbol = ?
        """, (symbol,))
        
        stock = cursor.fetchone()
        
        if not stock:
            conn.close()
            return {}
        
        # Get sector peers
        sector = stock['sector']
        if not sector:
            conn.close()
            return {'stock': dict(stock), 'peers': [], 'sector_avg': {}}
        
        # Get top 10 peers by market cap
        cursor.execute("""
            SELECT s.symbol, s.company_name,
                   sp.pe_ratio, sp.pb_ratio, sp.roe, sp.roa, sp.market_cap
            FROM stocks s
            LEFT JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE s.sector = ? AND s.symbol != ?
            ORDER BY sp.market_cap DESC
            LIMIT 10
        """, (sector, symbol))
        
        peers = [dict(row) for row in cursor.fetchall()]
        
        # Get sector averages
        sector_avg = self.get_sector_averages(sector)
        
        conn.close()
        
        return {
            'stock': dict(stock),
            'peers': peers,
            'sector_avg': sector_avg
        }
    
    def rank_in_sector(self, symbol: str, metric: str = 'roe') -> Dict[str, Any]:
        """
        Get a stock's rank within its sector for a given metric.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get stock's sector
        cursor.execute("""
            SELECT s.sector FROM stocks s WHERE s.symbol = ?
        """, (symbol,))
        
        row = cursor.fetchone()
        if not row or not row['sector']:
            conn.close()
            return {}
        
        sector = row['sector']
        
        # Get ranking
        cursor.execute(f"""
            SELECT s.symbol, sp.{metric}
            FROM stocks s
            JOIN stock_prices sp ON s.symbol = sp.symbol
            WHERE s.sector = ? AND sp.{metric} IS NOT NULL
            ORDER BY sp.{metric} DESC
        """, (sector,))
        
        stocks = cursor.fetchall()
        conn.close()
        
        total = len(stocks)
        rank = None
        value = None
        
        for i, s in enumerate(stocks, 1):
            if s['symbol'] == symbol:
                rank = i
                value = s[metric]
                break
        
        return {
            'symbol': symbol,
            'sector': sector,
            'metric': metric,
            'rank': rank,
            'total': total,
            'value': value,
            'percentile': round((total - rank + 1) / total * 100, 1) if rank else None
        }



    def calculate_screener_backfill(self) -> int:
        """
        Backfill missing screener metrics (RS Rating, Price vs SMA) manually.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get all symbols
        cursor.execute("SELECT symbol FROM stocks WHERE is_active = 1")
        symbols = [row['symbol'] for row in cursor.fetchall()]
        
        updates = []
        returns_1y = []
        
        for symbol in symbols:
            # Get price history (need 1 year + buffer)
            cursor.execute("""
                SELECT date, close_price
                FROM price_history
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 400
            """, (symbol,))
            
            history = cursor.fetchall()  # Newest first
            if not history:
                continue
                
            closes = [h['close_price'] for h in history][::-1] # Oldest to newest
            current_price = closes[-1]
            
            # Calculate SMAs
            smas = {}
            for period in [5, 10, 20, 50, 100]:
                sma = ti.calculate_sma(closes, period)
                if sma:
                    # Format: "Above" or "Below"
                    status = "Above" if current_price > sma else "Below"
                    smas[f'price_vs_sma{period}'] = status
            
            # Calculate 1y return for RS Rating
            # 1 year ~ 250 trading days
            ret_1y = ti.calculate_price_return(closes, 250)
            if ret_1y is not None:
                returns_1y.append({'symbol': symbol, 'ret': ret_1y})
                
            updates.append({
                'symbol': symbol,
                'smas': smas,
                'ret_1y': ret_1y
            })
            
        # Calculate RS Rating (Percentile of 1y return)
        returns_1y.sort(key=lambda x: x['ret'])
        count = len(returns_1y)
        rs_map = {}
        for i, item in enumerate(returns_1y):
            # 1 to 99
            rank = int(((i + 1) / count) * 99)
            if rank < 1: rank = 1
            rs_map[item['symbol']] = rank
            
        # Perform collected updates
        updated_count = 0
        for item in updates:
            symbol = item['symbol']
            smas = item['smas']
            rs = rs_map.get(symbol)
            
            # Update attributes
            fields = []
            values = []
            
            if rs:
                fields.append("tc_rs = ?")
                values.append(rs)
                if item['ret_1y'] is not None:
                    fields.append("rel_strength_1y = ?")
                    values.append(item['ret_1y'])
            
            for k, v in smas.items():
                fields.append(f"{k} = ?")
                values.append(v)
                
            if not fields:
                continue
                
            values.append(symbol)
            sql = f"UPDATE screener_metrics SET {', '.join(fields)} WHERE symbol = ?"
            
            # Ensure row exists
            cursor.execute("INSERT OR IGNORE INTO screener_metrics (symbol) VALUES (?)", (symbol,))
            cursor.execute(sql, values)
            updated_count += 1
            
        conn.commit()
        conn.close()
        logger.info(f"📊 Backfilled screener metrics for {updated_count} stocks")
        return updated_count


def run_metrics_calculation(db_path: str = "./data/vnstock_data.db"):
    """Utility function to run metrics calculation."""
    calculator = MetricsCalculator(db_path)
    return calculator.calculate_all_metrics()


if __name__ == "__main__":
    count = run_metrics_calculation()
    print(f"Updated metrics for {count} stocks/records")
