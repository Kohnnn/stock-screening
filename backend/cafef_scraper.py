"""
CafeF Financial Reports Scraper

Scrapes financial statements (BCTC) and extracts PDF download links from CafeF.
Best source for historical Vietnamese financial data.

URL Pattern:
https://s.cafef.vn/bao-cao-tai-chinh/{SYMBOL}/{REPORT_TYPE}/{YEAR}/{PERIOD}/0/0/slug.chn

Report Types:
- IncSta: Income Statement
- BSheet: Balance Sheet
- CashFlow: Cash Flow (Indirect)
- CashFlowDirect: Cash Flow (Direct)
"""

import asyncio
import aiohttp
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from io import StringIO
from loguru import logger


class CafeFScraper:
    """
    Scraper for CafeF financial reports.
    
    Provides:
    - Income statements
    - Balance sheets
    - Cash flow statements
    - PDF download links
    """
    
    BASE_URL = "https://s.cafef.vn"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    }
    
    REPORT_TYPES = {
        'income': 'IncSta',
        'balance': 'BSheet',
        'cashflow': 'CashFlow',
        'cashflow_direct': 'CashFlowDirect',
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.HEADERS
            )
        return self._session
    
    async def close(self):
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _build_url(
        self,
        symbol: str,
        report_type: str = 'income',
        year: int = None,
        quarterly: bool = True
    ) -> str:
        """Build CafeF BCTC URL."""
        if year is None:
            year = datetime.now().year
        
        type_code = self.REPORT_TYPES.get(report_type, 'IncSta')
        period = '1' if quarterly else '0'  # 1=quarterly, 0=yearly
        
        # Generic slug that always works
        slug = 'ket-qua-hoat-dong-kinh-doanh.chn'
        
        return f"{self.BASE_URL}/bao-cao-tai-chinh/{symbol}/{type_code}/{year}/{period}/0/0/{slug}"
    
    async def get_financial_statement(
        self,
        symbol: str,
        report_type: str = 'income',
        year: int = None,
        quarterly: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Fetch and parse a financial statement.
        
        Args:
            symbol: Stock ticker (e.g., VNM, FPT)
            report_type: 'income', 'balance', 'cashflow', 'cashflow_direct'
            year: Ending year (default: current)
            quarterly: True for quarterly, False for yearly
        
        Returns: DataFrame with financial data
        """
        url = self._build_url(symbol, report_type, year, quarterly)
        logger.debug(f"📊 Fetching CafeF: {symbol} {report_type}")
        
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"CafeF {symbol} failed: {resp.status}")
                    return None
                
                html = await resp.text()
                
                # Parse table using pandas
                try:
                    tables = pd.read_html(StringIO(html), attrs={'id': 'tableContent'})
                    
                    if not tables:
                        logger.warning(f"No table found for {symbol}")
                        return None
                    
                    df = tables[0]
                    logger.info(f"✅ CafeF {symbol}: {len(df)} rows, {len(df.columns)} cols")
                    return df
                    
                except ValueError as e:
                    # No tables found
                    logger.warning(f"CafeF parse error for {symbol}: {e}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ CafeF error for {symbol}: {e}")
            return None
    
    async def get_all_statements(
        self,
        symbol: str,
        year: int = None,
        quarterly: bool = True
    ) -> Dict[str, Optional[pd.DataFrame]]:
        """
        Fetch all financial statements for a symbol.
        
        Returns: Dict of report_type -> DataFrame
        """
        results = {}
        
        for report_type in ['income', 'balance', 'cashflow']:
            df = await self.get_financial_statement(symbol, report_type, year, quarterly)
            results[report_type] = df
            await asyncio.sleep(1)  # Polite delay
        
        return results
    
    def convert_to_records(
        self,
        df: pd.DataFrame,
        symbol: str,
        report_type: str
    ) -> List[Dict[str, Any]]:
        """
        Convert DataFrame to list of records for database.
        
        Handles CafeF's specific format:
        - First column: metric names
        - Subsequent columns: time periods (Q1 2024, Q2 2024, etc.)
        """
        if df is None or df.empty:
            return []
        
        records = []
        columns = df.columns.tolist()
        
        # First column is typically the metric name
        metric_col = columns[0] if columns else 'Chỉ tiêu'
        period_cols = columns[1:] if len(columns) > 1 else []
        
        for _, row in df.iterrows():
            metric_name = str(row.iloc[0]) if len(row) > 0 else ''
            
            for i, period_col in enumerate(period_cols):
                value = row.iloc[i + 1] if len(row) > i + 1 else None
                
                # Clean value
                if pd.isna(value):
                    value = None
                elif isinstance(value, str):
                    # Parse Vietnamese number format
                    value = value.replace('.', '').replace(',', '.')
                    try:
                        value = float(value)
                    except:
                        pass
                
                records.append({
                    'symbol': symbol,
                    'report_type': report_type,
                    'period': str(period_col),
                    'metric_name': metric_name,
                    'value': value,
                    'updated_at': datetime.now().isoformat()
                })
        
        return records
    
    async def get_company_page(self, symbol: str) -> Optional[str]:
        """Get company profile page HTML (contains PDF links)."""
        url = f"{self.BASE_URL}/hose/{symbol}.chn"
        
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.text()
        except Exception as e:
            logger.warning(f"Company page error for {symbol}: {e}")
        
        return None


# Singleton instance
_scraper: Optional[CafeFScraper] = None


async def get_cafef_scraper() -> CafeFScraper:
    """Get or create CafeF scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = CafeFScraper()
    return _scraper


# Test script
async def main():
    """Test the CafeF scraper."""
    scraper = CafeFScraper()
    
    try:
        # Test income statement
        print("\n📊 Testing income statement for VNM...")
        df = await scraper.get_financial_statement('VNM', 'income', quarterly=True)
        
        if df is not None:
            print(f"   Columns: {df.columns.tolist()}")
            print(f"   Rows: {len(df)}")
            print(f"   Sample:\n{df.head(3)}")
        else:
            print("   No data returned")
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    asyncio.run(main())
