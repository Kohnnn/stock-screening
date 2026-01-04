"""
SieuCoPhieu.vn Scraper

Collects industry cashflow and relative strength data from sieucophieu.vn API.
This is the primary source for sector-level money flow analysis.

Public API endpoint: /api/v1/stock/industry_cashflow/
"""

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from base_scraper import BaseScraper, RateLimiter


class SieucophieuScraper(BaseScraper):
    """
    Scraper for sieucophieu.vn industry cashflow API.
    
    This site provides unique sector-level money flow data via a public API.
    No authentication required for the industry_cashflow endpoint.
    """
    
    BASE_URL = "https://sieucophieu.vn"
    API_BASE = f"{BASE_URL}/api/v1"
    
    # Industry name translations (Vietnamese -> English)
    INDUSTRY_TRANSLATIONS = {
        "Ngân hàng": "Banking",
        "Bất động sản": "Real Estate",
        "Chứng khoán": "Securities",
        "Thép": "Steel",
        "Xây dựng": "Construction",
        "Bán lẻ": "Retail",
        "Hóa chất": "Chemicals",
        "Dầu khí": "Oil & Gas",
        "Thủy sản": "Seafood",
        "Điện": "Electricity",
        "Dệt may": "Textiles",
        "Cao su": "Rubber",
        "Nhựa - Bao bì": "Plastics & Packaging",
        "Vận tải": "Transportation",
        "Công nghệ": "Technology",
        "Thực phẩm": "Food",
        "Đầu tư": "Investment",
        "Y tế": "Healthcare",
        "Bảo hiểm": "Insurance",
        "Cảng biển": "Seaports",
        "Ô tô & Phụ tùng": "Automotive",
        "Khoáng sản": "Mining",
    }
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        # Lighter rate limiting for API endpoint
        if rate_limiter is None:
            rate_limiter = RateLimiter(
                min_delay=1.0,
                max_jitter=0.5,
                max_per_minute=30
            )
        super().__init__(name="SieuCoPhieu", rate_limiter=rate_limiter)
    
    async def collect_industry_cashflow(self) -> List[Dict[str, Any]]:
        """
        Collect industry cashflow data from public API.
        
        Returns list of industry records with:
        - industry_name: Vietnamese name
        - industry_name_en: English translation
        - cashflow: Absolute cashflow value
        - rate_of_change: ROC percentage
        - rs_short: Short-term relative strength
        - rs_mid: Medium-term relative strength
        - rs_relative: Overall relative strength
        """
        url = f"{self.API_BASE}/stock/industry_cashflow/"
        
        logger.info(f"[{self.name}] Fetching industry cashflow from API...")
        
        try:
            data = await self.fetch_json(url)
            
            if not data:
                logger.error(f"[{self.name}] No data returned from API")
                return []
            
            results = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                industry_name = item.get('stock_list_name', '')
                if not industry_name:
                    continue
                
                record = {
                    'industry_name': industry_name,
                    'industry_name_en': self.INDUSTRY_TRANSLATIONS.get(industry_name, industry_name),
                    'cashflow': item.get('cashflow'),
                    'rate_of_change': item.get('roc'),
                    'rs_short': item.get('rs_short'),
                    'rs_mid': item.get('rs_mid'),
                    'rs_relative': item.get('rs_relative'),
                    'source': 'sieucophieu',
                    'timestamp': datetime.now().isoformat()
                }
                results.append(record)
            
            logger.info(f"[{self.name}] Collected {len(results)} industry records")
            return results
            
        except Exception as e:
            logger.error(f"[{self.name}] Error collecting industry cashflow: {e}")
            return []
    
    async def collect(self) -> List[Dict[str, Any]]:
        """Main collection method - returns industry cashflow data."""
        return await self.collect_industry_cashflow()
    
    async def test(self) -> bool:
        """Test connectivity to sieucophieu API."""
        logger.info(f"[{self.name}] Testing API connectivity...")
        
        try:
            data = await self.collect_industry_cashflow()
            if data:
                logger.info(f"[{self.name}] ✅ Test passed: {len(data)} industries")
                if data:
                    sample = data[0]
                    logger.info(f"[{self.name}] Sample: {sample['industry_name']} - cashflow: {sample.get('cashflow')}")
                return True
            else:
                logger.warning(f"[{self.name}] ⚠️ Test passed but no data returned")
                return True
        except Exception as e:
            logger.error(f"[{self.name}] ❌ Test failed: {e}")
            return False
        finally:
            await self.close()


# Standalone test
async def main():
    """Test the scraper."""
    async with SieucophieuScraper() as scraper:
        success = await scraper.test()
        if success:
            data = await scraper.collect()
            print(f"\n📊 Collected {len(data)} industries:")
            for item in data[:5]:  # Show first 5
                print(f"  - {item['industry_name']}: CF={item.get('cashflow')}, ROC={item.get('rate_of_change')}%")


if __name__ == "__main__":
    asyncio.run(main())
