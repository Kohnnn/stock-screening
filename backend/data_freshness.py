"""
Data Freshness Checker

Intelligent gap detection system for stock data updates.
Tracks when data was last updated and identifies what needs refreshing.

Data Types and Update Frequencies:
- price: Daily (after market close)
- financials: Weekly (PE, PB, ROE, EPS)
- balance_sheet: Quarterly (Debt, Equity, Assets)
- profile: Monthly (Company info, sector)
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from loguru import logger


@dataclass
class DataGap:
    """Represents a gap in data that needs to be filled."""
    symbol: str
    data_type: str
    last_updated: Optional[datetime]
    days_stale: int
    priority: int  # 1=highest, 5=lowest


class DataFreshnessChecker:
    """
    Checks data freshness and identifies gaps that need updates.
    
    Freshness Thresholds:
    - price: 24 hours
    - financials: 7 days
    - balance_sheet: 90 days
    - profile: 30 days
    """
    
    THRESHOLDS = {
        'price': timedelta(hours=24),
        'financials': timedelta(days=7),
        'balance_sheet': timedelta(days=90),
        'profile': timedelta(days=30),
    }
    
    PRIORITIES = {
        'price': 1,
        'financials': 2,
        'balance_sheet': 3,
        'profile': 4,
    }
    
    def __init__(self, db_path: str = "./data/vnstock_data.db"):
        self.db_path = db_path
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_current_quarter(self) -> str:
        """Get current quarter string like '2024Q1'."""
        now = datetime.now()
        quarter = (now.month - 1) // 3 + 1
        return f"{now.year}Q{quarter}"
    
    def record_update(
        self,
        symbol: str,
        data_type: str,
        source: str = 'cophieu68',
        quarter: Optional[str] = None,
        record_count: int = 1
    ):
        """Record that data was updated for a symbol."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # For daily data, use NULL quarter
        quarter_val = quarter if data_type != 'price' else None
        
        cursor.execute("""
            INSERT INTO data_versions (symbol, data_type, last_updated, quarter, source, record_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, data_type, quarter) DO UPDATE SET
                last_updated = excluded.last_updated,
                source = excluded.source,
                record_count = excluded.record_count
        """, (symbol, data_type, datetime.now().isoformat(), quarter_val, source, record_count))
        
        conn.commit()
        conn.close()
    
    def record_bulk_update(
        self,
        symbols: List[str],
        data_type: str,
        source: str = 'cophieu68'
    ):
        """Record update for multiple symbols at once."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        quarter = self.get_current_quarter() if data_type != 'price' else None
        
        data = [(s, data_type, now, quarter, source, 1) for s in symbols]
        
        cursor.executemany("""
            INSERT INTO data_versions (symbol, data_type, last_updated, quarter, source, record_count)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (symbol, data_type, quarter) DO UPDATE SET
                last_updated = excluded.last_updated,
                source = excluded.source
        """, data)
        
        conn.commit()
        conn.close()
        logger.info(f"📝 Recorded {data_type} update for {len(symbols)} symbols")
    
    def get_stale_symbols(self, data_type: str) -> List[str]:
        """Get list of symbols with stale data for a given type."""
        threshold = self.THRESHOLDS.get(data_type, timedelta(days=1))
        cutoff = datetime.now() - threshold
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get symbols that are stale or never updated
        cursor.execute("""
            SELECT s.symbol
            FROM stocks s
            LEFT JOIN data_versions dv ON s.symbol = dv.symbol AND dv.data_type = ?
            WHERE s.is_active = 1
            AND (dv.last_updated IS NULL OR dv.last_updated < ?)
        """, (data_type, cutoff.isoformat()))
        
        symbols = [row['symbol'] for row in cursor.fetchall()]
        conn.close()
        
        return symbols
    
    def get_never_updated(self, data_type: str) -> List[str]:
        """Get symbols that have never been updated for a data type."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.symbol
            FROM stocks s
            LEFT JOIN data_versions dv ON s.symbol = dv.symbol AND dv.data_type = ?
            WHERE s.is_active = 1 AND dv.symbol IS NULL
        """, (data_type,))
        
        symbols = [row['symbol'] for row in cursor.fetchall()]
        conn.close()
        
        return symbols
    
    def get_data_gaps(self) -> List[DataGap]:
        """
        Get all data gaps across all data types, sorted by priority.
        Returns gaps that need to be filled.
        """
        gaps = []
        now = datetime.now()
        
        for data_type, threshold in self.THRESHOLDS.items():
            stale_symbols = self.get_stale_symbols(data_type)
            
            for symbol in stale_symbols:
                # Get last update time if available
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT last_updated FROM data_versions
                    WHERE symbol = ? AND data_type = ?
                    ORDER BY last_updated DESC LIMIT 1
                """, (symbol, data_type))
                row = cursor.fetchone()
                conn.close()
                
                if row and row['last_updated']:
                    last_updated = datetime.fromisoformat(row['last_updated'])
                    days_stale = (now - last_updated).days
                else:
                    last_updated = None
                    days_stale = 9999  # Never updated
                
                gaps.append(DataGap(
                    symbol=symbol,
                    data_type=data_type,
                    last_updated=last_updated,
                    days_stale=days_stale,
                    priority=self.PRIORITIES.get(data_type, 5)
                ))
        
        # Sort by priority (lower first), then by days stale (higher first)
        gaps.sort(key=lambda g: (g.priority, -g.days_stale))
        
        return gaps
    
    def get_update_summary(self) -> Dict[str, Dict]:
        """
        Get summary of data freshness across all types.
        
        Returns:
            {
                'price': {'total': 1732, 'fresh': 500, 'stale': 1232, 'never': 0},
                'financials': {...},
                ...
            }
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Get total active stocks
        cursor.execute("SELECT COUNT(*) as count FROM stocks WHERE is_active = 1")
        total_stocks = cursor.fetchone()['count']
        
        summary = {}
        now = datetime.now()
        
        for data_type, threshold in self.THRESHOLDS.items():
            cutoff = now - threshold
            
            # Fresh count
            cursor.execute("""
                SELECT COUNT(DISTINCT dv.symbol) as count
                FROM data_versions dv
                JOIN stocks s ON dv.symbol = s.symbol
                WHERE dv.data_type = ? AND dv.last_updated >= ? AND s.is_active = 1
            """, (data_type, cutoff.isoformat()))
            fresh = cursor.fetchone()['count']
            
            # Total with any version
            cursor.execute("""
                SELECT COUNT(DISTINCT dv.symbol) as count
                FROM data_versions dv
                JOIN stocks s ON dv.symbol = s.symbol
                WHERE dv.data_type = ? AND s.is_active = 1
            """, (data_type,))
            has_data = cursor.fetchone()['count']
            
            stale = has_data - fresh
            never = total_stocks - has_data
            
            summary[data_type] = {
                'total': total_stocks,
                'fresh': fresh,
                'stale': stale,
                'never': never,
                'percent_fresh': round(fresh / total_stocks * 100, 1) if total_stocks > 0 else 0
            }
        
        conn.close()
        return summary
    
    def should_update(self, data_type: str, threshold_override: Optional[timedelta] = None) -> bool:
        """
        Check if any data of this type needs updating.
        
        Returns True if there are stale or never-updated symbols.
        """
        threshold = threshold_override or self.THRESHOLDS.get(data_type, timedelta(days=1))
        stale_symbols = self.get_stale_symbols(data_type)
        
        return len(stale_symbols) > 0
    
    def get_missing_quarters(self, symbol: str) -> List[str]:
        """
        Get list of quarters with missing financial data.
        Checks last 8 quarters (2 years).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Generate last 8 quarters
        now = datetime.now()
        expected_quarters = []
        for i in range(8):
            q_date = now - timedelta(days=i * 90)
            quarter = (q_date.month - 1) // 3 + 1
            expected_quarters.append(f"{q_date.year}Q{quarter}")
        
        # Get existing quarters
        cursor.execute("""
            SELECT DISTINCT quarter FROM data_versions
            WHERE symbol = ? AND data_type = 'balance_sheet' AND quarter IS NOT NULL
        """, (symbol,))
        existing = {row['quarter'] for row in cursor.fetchall()}
        conn.close()
        
        # Find missing
        missing = [q for q in expected_quarters if q not in existing]
        return missing


# Utility functions for scheduler integration
def get_freshness_checker(db_path: str = "./data/vnstock_data.db") -> DataFreshnessChecker:
    """Factory function for getting a freshness checker."""
    return DataFreshnessChecker(db_path)


def print_freshness_report(db_path: str = "./data/vnstock_data.db"):
    """Print a human-readable freshness report."""
    checker = DataFreshnessChecker(db_path)
    summary = checker.get_update_summary()
    
    print("\n" + "="*60)
    print("📊 DATA FRESHNESS REPORT")
    print("="*60)
    
    for data_type, stats in summary.items():
        print(f"\n{data_type.upper()}")
        print(f"  Total: {stats['total']}")
        print(f"  Fresh: {stats['fresh']} ({stats['percent_fresh']}%)")
        print(f"  Stale: {stats['stale']}")
        print(f"  Never Updated: {stats['never']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Test the freshness checker
    print_freshness_report()
