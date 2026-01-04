"""
SSI iBoard Real-time Price Collector

Fetches real-time stock prices and market depth from SSI iBoard API.
High-quality data source with bid/ask levels.

API Endpoints:
- /stock/stock-info - Full symbol list
- /stock/group/{GROUP} - Snapshot for VN30, HOSE, HNX, UPCOM
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger


class SSIiBoardCollector:
    """
    Collector for SSI iBoard real-time stock data.
    
    Provides:
    - Real-time prices
    - Bid/Ask levels (3 levels)
    - Foreign trading room
    - Daily high/low
    """
    
    BASE_URL = "https://iboard-query.ssi.com.vn"
    
    # Required headers to avoid blocking
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://iboard.ssi.com.vn/',
        'Origin': 'https://iboard.ssi.com.vn',
        'Accept': 'application/json',
    }
    
    GROUPS = ['VN30', 'HOSE', 'HNX', 'UPCOM', 'VN100']
    
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
    
    async def get_stock_info(self) -> List[Dict[str, Any]]:
        """
        Get full list of supported symbols with metadata.
        
        Returns: List of stock info dicts
        """
        url = f"{self.BASE_URL}/stock/stock-info"
        
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"SSI stock-info failed: {resp.status}")
                    return []
                
                data = await resp.json()
                
                if data.get('code') != 'SUCCESS':
                    logger.warning(f"SSI API error: {data.get('message')}")
                    return []
                
                stocks = data.get('data', [])
                logger.info(f"✅ SSI stock-info: {len(stocks)} symbols")
                return stocks
                
        except Exception as e:
            logger.error(f"❌ SSI stock-info error: {e}")
            return []
    
    async def get_market_snapshot(self, group: str = 'HOSE') -> List[Dict[str, Any]]:
        """
        Get real-time price snapshot for a market group.
        
        Args:
            group: VN30, HOSE, HNX, UPCOM, VN100
        
        Returns: List of stock price data with bid/ask
        """
        if group not in self.GROUPS:
            logger.warning(f"Invalid group: {group}. Using HOSE.")
            group = 'HOSE'
        
        url = f"{self.BASE_URL}/stock/group/{group}"
        
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.warning(f"SSI group/{group} failed: {resp.status}")
                    return []
                
                data = await resp.json()
                
                if data.get('code') != 'SUCCESS':
                    logger.warning(f"SSI API error: {data.get('message')}")
                    return []
                
                stocks = data.get('data', [])
                logger.info(f"✅ SSI {group}: {len(stocks)} stocks")
                
                # Normalize the data
                return [self._normalize_price_data(s) for s in stocks]
                
        except Exception as e:
            logger.error(f"❌ SSI group/{group} error: {e}")
            return []
    
    def _normalize_price_data(self, raw: Dict) -> Dict[str, Any]:
        """Normalize SSI price data to our schema."""
        # SSI returns prices in VND (not 1000s)
        return {
            'symbol': raw.get('stockSymbol', ''),
            'current_price': raw.get('matchedPrice'),
            'price_change': raw.get('priceChange'),
            'percent_change': raw.get('priceChangePercent'),
            'open_price': raw.get('openPrice'),
            'high_price': raw.get('highest'),
            'low_price': raw.get('lowest'),
            'close_price': raw.get('matchedPrice'),
            'volume': raw.get('totalVolume'),
            'accumulated_value': raw.get('totalValue'),
            
            # Reference prices
            'ceiling': raw.get('ceiling'),
            'floor': raw.get('floor'),
            'ref_price': raw.get('refPrice'),
            
            # Bid levels
            'bid_1_price': raw.get('bestBid1Price'),
            'bid_1_volume': raw.get('bestBid1Qty'),
            'bid_2_price': raw.get('bestBid2Price'),
            'bid_2_volume': raw.get('bestBid2Qty'),
            'bid_3_price': raw.get('bestBid3Price'),
            'bid_3_volume': raw.get('bestBid3Qty'),
            
            # Ask levels
            'ask_1_price': raw.get('bestAsk1Price'),
            'ask_1_volume': raw.get('bestAsk1Qty'),
            'ask_2_price': raw.get('bestAsk2Price'),
            'ask_2_volume': raw.get('bestAsk2Qty'),
            'ask_3_price': raw.get('bestAsk3Price'),
            'ask_3_volume': raw.get('bestAsk3Qty'),
            
            # Foreign trading
            'foreign_buy_volume': raw.get('foreignBuyVol'),
            'foreign_sell_volume': raw.get('foreignSellVol'),
            'foreign_room': raw.get('currentRoom'),
            
            # Metadata
            'exchange': raw.get('exchange'),
            'data_source': 'ssi_iboard',
            'updated_at': datetime.now().isoformat(),
        }
    
    async def get_all_markets(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get snapshots for all market groups.
        
        Returns: Dict of group -> stock list
        """
        results = {}
        
        for group in ['HOSE', 'HNX', 'UPCOM']:
            data = await self.get_market_snapshot(group)
            results[group] = data
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        total = sum(len(v) for v in results.values())
        logger.info(f"🎉 SSI all markets: {total} stocks")
        return results
    
    async def get_vn30_snapshot(self) -> List[Dict[str, Any]]:
        """Quick snapshot for VN30 (high priority stocks)."""
        return await self.get_market_snapshot('VN30')

    async def get_index_summary(self, group: str) -> Dict[str, Any]:
        """
        Calculate pseudo-index stats from market snapshot.
        
        Since SSI doesn't provide direct index values, we calculate:
        - Average price change %
        - Total volume
        - Advancing/Declining counts
        """
        data = await self.get_market_snapshot(group)
        
        if not data:
            return {'code': group, 'value': 0, 'change': 0, 'change_percent': 0}
        
        total_pct = 0
        advancing = 0
        declining = 0
        total_volume = 0
        
        for stock in data:
            pct = stock.get('percent_change') or 0
            total_pct += pct
            total_volume += stock.get('volume') or 0
            if pct > 0:
                advancing += 1
            elif pct < 0:
                declining += 1
        
        avg_pct = total_pct / len(data) if data else 0
        
        return {
            'code': group,
            'value': 0,  # Index value not available
            'change': 0,
            'change_percent': round(avg_pct, 2),
            'advancing': advancing,
            'declining': declining,
            'total_volume': total_volume,
            'stock_count': len(data),
            'source': 'ssi_iboard'
        }


# Singleton instance
_collector: Optional[SSIiBoardCollector] = None


async def get_ssi_collector() -> SSIiBoardCollector:
    """Get or create SSI collector instance."""
    global _collector
    if _collector is None:
        _collector = SSIiBoardCollector()
    return _collector


# Test script
async def main():
    """Test the SSI iBoard collector."""
    collector = SSIiBoardCollector()
    
    try:
        # Test stock info
        print("\n📋 Testing stock-info...")
        stocks = await collector.get_stock_info()
        print(f"   Found {len(stocks)} symbols")
        
        # Test VN30 snapshot
        print("\n📊 Testing VN30 snapshot...")
        vn30 = await collector.get_vn30_snapshot()
        print(f"   Found {len(vn30)} VN30 stocks")
        
        if vn30:
            sample = vn30[0]
            print(f"   Sample: {sample['symbol']} @ {sample['current_price']}")
            print(f"   Bid1: {sample['bid_1_price']} x {sample['bid_1_volume']}")
            print(f"   Ask1: {sample['ask_1_price']} x {sample['ask_1_volume']}")
        
    finally:
        await collector.close()


if __name__ == "__main__":
    asyncio.run(main())
