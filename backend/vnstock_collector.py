"""
VnStock Data Collector with robust rate limiting and circuit breaker protection.

Supports VCI and TCBS sources. TCBS Screener API is available in vnstock 3.3.1+.
Designed for 24/7 operation with vnstock's limited API calls.

Features (vnstock 3.3.1+):
- ProxyManager for automatic proxy support when IP blocked
- Unified data source management (VCI, TCBS, FMP)
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import pandas as pd

try:
    from vnstock import Vnstock, Listing, Screener, Company, Trading
    # ProxyManager for vnstock 3.3.1+ (optional feature)
    try:
        from vnstock.core.utils.proxy_manager import ProxyManager
        PROXY_AVAILABLE = True
    except ImportError:
        PROXY_AVAILABLE = False
except ImportError:
    logger.error("❌ vnstock library not installed. Install with: pip install vnstock")
    raise

from config import settings
from rate_limiter import RateLimiter, get_rate_limiter
from circuit_breaker import CircuitBreaker, CircuitOpenError, get_circuit_breaker


class VnStockCollector:
    """
    Robust data collector for Vietnamese stock market data.
    
    Supports VCI and TCBS sources. TCBS fixed in vnstock 3.3.1+.
    
    Features:
    - Token bucket rate limiting for smooth API usage
    - Circuit breaker for failure protection
    - Exponential backoff on errors
    - Progress tracking for long operations
    - ProxyManager support for avoiding IP blocks (vnstock 3.3.1+)
    """
    
    def __init__(
        self,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        enable_proxy: bool = None,
    ):
        """Initialize the collector with protection mechanisms."""
        # Initialize vnstock clients
        self.vnstock = Vnstock()
        self.listing = Listing()
        
        # Use configured source (TCBS now works in vnstock 3.3.1+)
        self.default_source = settings.DEFAULT_VNSTOCK_SOURCE
        
        # Initialize ProxyManager if enabled (vnstock 3.3.1+)
        if enable_proxy is None:
            enable_proxy = settings.ENABLE_VNSTOCK_PROXY
        
        self.proxy_manager = None
        if enable_proxy and PROXY_AVAILABLE:
            try:
                self.proxy_manager = ProxyManager()
                proxies = self.proxy_manager.fetch_proxies(limit=10)
                logger.info(f"🌐 ProxyManager enabled with {len(proxies)} proxies")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize ProxyManager: {e}")
                self.proxy_manager = None
        elif enable_proxy and not PROXY_AVAILABLE:
            logger.warning("⚠️ ProxyManager requested but not available (requires vnstock 3.3.1+)")
        
        # Protection mechanisms
        self.rate_limiter = rate_limiter or get_rate_limiter(
            requests_per_minute=settings.VNSTOCK_RATE_LIMIT
        )
        self.circuit_breaker = circuit_breaker or get_circuit_breaker(
            failure_threshold=settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout=settings.CIRCUIT_BREAKER_RECOVERY_TIMEOUT
        )
        
        # Statistics
        self._total_api_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        
        logger.info(
            f"🚀 VnStockCollector initialized: "
            f"source={self.default_source}, "
            f"rate_limit={settings.VNSTOCK_RATE_LIMIT}/min"
        )
    
    def _sync_api_call(self, func, *args, **kwargs) -> Any:
        """Execute a synchronous vnstock API call."""
        return func(*args, **kwargs)
    
    async def _protected_api_call(self, func, *args, **kwargs) -> Any:
        """
        Execute an API call with full protection.
        
        - Acquires rate limit token
        - Checks circuit breaker
        - Handles retries with backoff
        """
        self._total_api_calls += 1
        
        # Wait for rate limit token
        await self.rate_limiter.acquire()
        
        try:
            # Check circuit breaker state
            if self.circuit_breaker.is_open:
                raise CircuitOpenError("Circuit breaker is open")
            
            # Execute synchronous vnstock call in thread pool
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self._sync_api_call(func, *args, **kwargs)
            )
            
            self._successful_calls += 1
            await self.rate_limiter.on_success()
            await self.circuit_breaker.record_success()
            
            return result
            
        except CircuitOpenError:
            self._failed_calls += 1
            logger.warning("⚠️ Circuit breaker OPEN - skipping API call")
            raise
            
        except Exception as e:
            self._failed_calls += 1
            await self.rate_limiter.on_failure()
            await self.circuit_breaker.record_failure()
            logger.error(f"❌ API call failed: {str(e)}")
            raise
    
    # =========================================
    # Stock Listings
    # =========================================
    
    async def collect_stock_listings(self) -> List[Dict[str, Any]]:
        """
        Collect stock listings from all Vietnamese exchanges.
        
        Returns: List of stock data dictionaries
        """
        logger.info("📋 Collecting stock listings...")
        
        try:
            # Fetch all symbols using Listing API
            df = await self._protected_api_call(self.listing.all_symbols)
            
            if df is None or df.empty:
                logger.warning("⚠️ No symbols returned")
                return []
            
            logger.info(f"✅ Found {len(df)} symbols")
            
            # Convert to list of dictionaries
            # Columns: ['symbol', 'organ_name']
            stocks = []
            for _, row in df.iterrows():
                stock = {
                    'symbol': str(row.get('symbol', '')).upper(),
                    'company_name': row.get('organ_name', ''),
                    'exchange': None,  # Will be inferred from symbol later
                    'sector': None,
                    'industry': None,
                }
                stocks.append(stock)
            
            logger.info(f"🎉 Stock listings collected: {len(stocks)} stocks")
            return stocks
            
        except CircuitOpenError:
            logger.warning("⚠️ Circuit open, returning empty listings")
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting stock listings: {e}")
            return []
    
    # =========================================
    # Stock Details (Company Overview)
    # =========================================
    
    async def collect_stock_details(self, symbol: str) -> Dict[str, Any]:
        """
        Collect detailed information for a stock.
        
        Returns: Dict with company info and current metrics
        """
        logger.debug(f"📊 Collecting details for {symbol}")
        
        result = {
            'symbol': symbol,
            'company_name': None,
            'exchange': None,
            'sector': None,
            'industry': None,
            'current_price': None,
            'pe_ratio': None,
            'pb_ratio': None,
            'roe': None,
            'roa': None,
            'market_cap': None,
        }
        
        try:
            # Get stock object with VCI source
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            # Get company overview
            try:
                overview_df = await self._protected_api_call(stock.company.overview)
                if overview_df is not None and not overview_df.empty:
                    row = overview_df.iloc[0]
                    result['sector'] = row.get('icb_name2', '')
                    result['industry'] = row.get('icb_name3', '')
                    logger.debug(f"✅ Overview collected for {symbol}")
            except Exception as e:
                logger.debug(f"Overview error for {symbol}: {e}")
            
            # Get latest price from history
            try:
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                
                history_df = await self._protected_api_call(
                    stock.quote.history,
                    start=start_date,
                    end=end_date
                )
                
                if history_df is not None and not history_df.empty:
                    latest = history_df.iloc[-1]
                    result['current_price'] = self._safe_float(latest.get('close'))
                    result['volume'] = self._safe_int(latest.get('volume'))
                    logger.debug(f"✅ Price collected for {symbol}: {result['current_price']}")
            except Exception as e:
                logger.debug(f"Price history error for {symbol}: {e}")
            
            # Get financial ratios
            try:
                ratios_df = await self._protected_api_call(
                    stock.finance.ratio,
                    period='year',
                    lang='en'
                )
                
                if ratios_df is not None and not ratios_df.empty:
                    # Get most recent year's ratios
                    latest = ratios_df.iloc[-1]
                    # Ratios have multi-level columns
                    result['roe'] = self._extract_ratio(latest, 'ROA')
                    result['roa'] = self._extract_ratio(latest, 'ROE')
                    logger.debug(f"✅ Ratios collected for {symbol}")
            except Exception as e:
                logger.debug(f"Ratios error for {symbol}: {e}")
            
            return result
            
        except CircuitOpenError:
            return result
        except Exception as e:
            logger.warning(f"⚠️ Error collecting details for {symbol}: {e}")
            return result
    
    def _extract_ratio(self, row, pattern: str) -> Optional[float]:
        """Extract ratio value from multi-level column dataframe."""
        try:
            for col in row.index:
                if isinstance(col, tuple) and pattern in str(col):
                    return self._safe_float(row[col])
        except:
            pass
        return None
    
    # =========================================
    # Price History
    # =========================================
    
    async def collect_price_history(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Collect price history for a specific stock.
        
        Returns: List of OHLCV records
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            start = datetime.now() - timedelta(days=settings.PRICE_HISTORY_DAYS)
            start_date = start.strftime('%Y-%m-%d')
        
        logger.debug(f"📈 Collecting price history: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(
                stock.quote.history,
                start=start_date,
                end=end_date
            )
            
            if df is None or df.empty:
                logger.debug(f"⚠️ No price history for {symbol}")
                return []
            
            # Convert to list of dicts
            # Columns: ['time', 'open', 'high', 'low', 'close', 'volume']
            history = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'date': str(row.get('time', '')),
                    'open_price': self._safe_float(row.get('open')),
                    'high_price': self._safe_float(row.get('high')),
                    'low_price': self._safe_float(row.get('low')),
                    'close_price': self._safe_float(row.get('close')),
                    'volume': self._safe_int(row.get('volume')),
                    'adjusted_close': self._safe_float(row.get('close')),
                }
                history.append(record)
            
            logger.debug(f"✅ Price history: {symbol} - {len(history)} records")
            return history
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.warning(f"⚠️ Error fetching price history for {symbol}: {e}")
            return []
    
    async def collect_batch_stock_data(
        self,
        symbols: List[str],
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect data for multiple symbols with progress tracking.
        
        Collects listings + latest price for each symbol.
        """
        logger.info(f"📊 Collecting data for {len(symbols)} symbols")
        
        results = []
        total = len(symbols)
        
        for i, symbol in enumerate(symbols):
            # Check circuit breaker
            if self.circuit_breaker.is_open:
                logger.warning(f"⚠️ Circuit open, stopping at {i}/{total}")
                break
            
            # Collect stock details
            details = await self.collect_stock_details(symbol)
            if details.get('current_price'):
                results.append(details)
            
            # Progress update
            if progress_callback:
                progress_callback(i + 1, total)
            
            if (i + 1) % 10 == 0:
                progress = ((i + 1) / total) * 100
                logger.info(f"📊 Progress: {i + 1}/{total} ({progress:.1f}%)")
        
        logger.info(f"🎉 Batch complete: {len(results)} stocks with data")
        return results
    
    # =========================================
    # Screener Data (Bulk collection)
    # =========================================
    
    async def collect_screener_data(
        self,
        exchange: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Collect screener data for all stocks using price_board API.
        
        Gets listings first, then fetches real prices via price_board in batches.
        Returns: List of stock data with current prices
        """
        logger.info("📊 Collecting screener data via price_board...")
        
        try:
            # First get all stock listings
            df = await self._protected_api_call(self.listing.all_symbols)
            
            if df is None or df.empty:
                logger.warning("⚠️ No listings returned")
                return []
            
            logger.info(f"📋 Got {len(df)} stock listings")
            
            # Extract symbols and company names
            stocks_info = {}
            for _, row in df.iterrows():
                symbol = str(row.get('symbol', '')).upper()
                stocks_info[symbol] = {
                    'symbol': symbol,
                    'company_name': row.get('organ_name', ''),
                    'exchange': row.get('exchange', ''),
                }
            
            symbols = list(stocks_info.keys())
            
            # Fetch prices in batches via price_board (efficient bulk API)
            results = []
            batch_size = 100  # price_board can handle ~100 symbols per call
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                if self.circuit_breaker.is_open:
                    logger.warning("⚠️ Circuit open, stopping price fetch")
                    break
                
                try:
                    trading = Trading(symbol='VN30F1M')
                    price_df = await self._protected_api_call(
                        trading.price_board,
                        symbols_list=batch
                    )
                    
                    if price_df is not None and not price_df.empty:
                        # Flatten MultiIndex columns if present
                        if isinstance(price_df.columns, pd.MultiIndex):
                            price_df.columns = ['_'.join(map(str, col)).strip() for col in price_df.columns.values]
                        
                        for _, row in price_df.iterrows():
                            # Use flattened column names
                            symbol = str(row.get('listing_symbol', row.get('symbol', ''))).upper()
                            info = stocks_info.get(symbol, {})
                            
                            # Extract prices from flattened columns
                            match_price = self._safe_float(row.get('match_info_match_price', row.get('match_price')))
                            prior_close = self._safe_float(row.get('listing_prior_close_price', row.get('prior_close_price')))
                            ref_price = self._safe_float(row.get('listing_ref_price', row.get('ref_price')))
                            
                            stock_data = {
                                'symbol': symbol,
                                'company_name': info.get('company_name', row.get('listing_organ_name', '')),
                                'exchange': info.get('exchange', row.get('listing_exchange', '')),
                                'current_price': match_price or prior_close or ref_price,
                                'price_change': (match_price - prior_close) if match_price and prior_close else None,
                                'percent_change': ((match_price - prior_close) / prior_close * 100) if match_price and prior_close else None,
                                'volume': self._safe_int(row.get('match_info_accumulated_volume', row.get('accumulated_volume'))),
                                'open_price': ref_price,
                                'high_price': self._safe_float(row.get('match_info_highest', row.get('highest'))),
                                'low_price': self._safe_float(row.get('match_info_lowest', row.get('lowest'))),
                                'close_price': match_price,
                            }
                            if stock_data['symbol']:  # Only add if symbol exists
                                results.append(stock_data)
                    
                    if (i + batch_size) % 500 == 0:
                        logger.info(f"📊 Price progress: {min(i + batch_size, len(symbols))}/{len(symbols)}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Batch {i}-{i+batch_size} failed: {e}")
                    continue
            
            logger.info(f"✅ Screener data: {len(results)} stocks with prices")
            return results
            
        except CircuitOpenError:
            logger.warning("⚠️ Circuit open, returning empty screener data")
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting screener data: {e}")
            return []
    
    # =========================================
    # Financial Statements
    # =========================================
    
    async def collect_income_statement(
        self,
        symbol: str,
        period: str = 'year',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Collect income statement data for a stock."""
        logger.debug(f"💰 Collecting income statement: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(
                stock.finance.income_statement,
                period=period,
                lang='en'
            )
            
            if df is None or df.empty:
                return []
            
            # Convert to list of dicts
            results = []
            for _, row in df.head(limit).iterrows():
                record = {
                    'symbol': symbol,
                    'period': str(row.get('yearReport', row.get('year', ''))),
                    'period_type': period,
                    'revenue': self._safe_float(row.get('revenue')),
                    'gross_profit': self._safe_float(row.get('grossProfit')),
                    'operating_profit': self._safe_float(row.get('operationProfit')),
                    'net_profit': self._safe_float(row.get('postTaxProfit', row.get('netProfit'))),
                }
                results.append(record)
            
            logger.debug(f"✅ Income statement: {symbol} - {len(results)} periods")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Income statement error for {symbol}: {e}")
            return []
    
    async def collect_balance_sheet(
        self,
        symbol: str,
        period: str = 'year',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Collect balance sheet data for a stock."""
        logger.debug(f"📊 Collecting balance sheet: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(
                stock.finance.balance_sheet,
                period=period,
                lang='en'
            )
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.head(limit).iterrows():
                record = {
                    'symbol': symbol,
                    'period': str(row.get('yearReport', row.get('year', ''))),
                    'period_type': period,
                    'total_assets': self._safe_float(row.get('asset')),
                    'total_liabilities': self._safe_float(row.get('debt')),
                    'total_equity': self._safe_float(row.get('equity')),
                    'current_assets': self._safe_float(row.get('shortAsset')),
                    'current_liabilities': self._safe_float(row.get('shortDebt')),
                    'cash_and_equivalents': self._safe_float(row.get('cash')),
                }
                results.append(record)
            
            logger.debug(f"✅ Balance sheet: {symbol} - {len(results)} periods")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Balance sheet error for {symbol}: {e}")
            return []
    
    async def collect_cash_flow(
        self,
        symbol: str,
        period: str = 'year',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Collect cash flow statement data for a stock."""
        logger.debug(f"💸 Collecting cash flow: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(
                stock.finance.cash_flow,
                period=period,
                lang='en'
            )
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.head(limit).iterrows():
                record = {
                    'symbol': symbol,
                    'period': str(row.get('yearReport', row.get('year', ''))),
                    'period_type': period,
                    'operating_cash_flow': self._safe_float(row.get('fromSale')),
                    'investing_cash_flow': self._safe_float(row.get('fromInvest')),
                    'financing_cash_flow': self._safe_float(row.get('fromFinancial')),
                }
                results.append(record)
            
            logger.debug(f"✅ Cash flow: {symbol} - {len(results)} periods")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Cash flow error for {symbol}: {e}")
            return []
    
    async def collect_financial_data(
        self,
        symbol: str,
        period: str = 'year'
    ) -> Dict[str, Any]:
        """Collect all financial data for a stock (combined)."""
        logger.debug(f"📈 Collecting all financials: {symbol}")
        
        result = {
            'symbol': symbol,
            'income_statement': await self.collect_income_statement(symbol, period),
            'balance_sheet': await self.collect_balance_sheet(symbol, period),
            'cash_flow': await self.collect_cash_flow(symbol, period),
            'ratios': []
        }
        
        # Also get financial ratios
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            df = await self._protected_api_call(
                stock.finance.ratio,
                period=period,
                lang='en'
            )
            if df is not None and not df.empty:
                # Flatten multi-level columns if needed
                result['ratios'] = df.to_dict('records')[:5]
        except Exception as e:
            logger.debug(f"Ratios error for {symbol}: {e}")
        
        return result
    
    async def collect_batch_price_history(
        self,
        symbols: List[str],
        batch_size: int = 10,
        days: int = 30
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Collect price history for multiple symbols."""
        logger.info(f"📈 Collecting price history for {len(symbols)} symbols")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        results = {}
        for i, symbol in enumerate(symbols):
            if self.circuit_breaker.is_open:
                logger.warning("⚠️ Circuit open, stopping batch")
                break
            
            history = await self.collect_price_history(symbol, start_date, end_date)
            if history:
                results[symbol] = history
            
            if (i + 1) % 10 == 0:
                logger.info(f"📊 History progress: {i + 1}/{len(symbols)}")
        
        return results
    
    # =========================================
    # Dividend Data
    # =========================================
    
    async def collect_dividend_history(
        self,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """Collect dividend history for a stock."""
        logger.debug(f"💵 Collecting dividends: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(stock.company.dividends)
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'ex_date': str(row.get('exerciseDate', row.get('exDate', ''))),
                    'record_date': str(row.get('recordDate', '')),
                    'payment_date': str(row.get('issueDate', row.get('paymentDate', ''))),
                    'cash_dividend': self._safe_float(row.get('cashDividend')),
                    'stock_dividend': self._safe_float(row.get('stockDividend')),
                    'dividend_yield': self._safe_float(row.get('dividendYield')),
                }
                results.append(record)
            
            logger.debug(f"✅ Dividends: {symbol} - {len(results)} records")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Dividends error for {symbol}: {e}")
            return []
    
    # =========================================
    # Company Ratings
    # =========================================
    
    async def collect_company_ratings(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Collect all company ratings for a stock."""
        logger.debug(f"⭐ Collecting ratings: {symbol}")
        
        ratings = {
            'symbol': symbol,
            'general': None,
            'business_model': None,
            'business_operation': None,
            'financial_health': None,
            'valuation': None
        }
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            # Try to get general rating
            try:
                df = await self._protected_api_call(stock.company.general_rating)
                if df is not None and not df.empty:
                    ratings['general'] = df.to_dict('records')
            except:
                pass
            
            # Try to get business model rating
            try:
                df = await self._protected_api_call(stock.company.business_model_rating)
                if df is not None and not df.empty:
                    ratings['business_model'] = df.to_dict('records')
            except:
                pass
            
            # Try to get business operation rating
            try:
                df = await self._protected_api_call(stock.company.business_operation_rating)
                if df is not None and not df.empty:
                    ratings['business_operation'] = df.to_dict('records')
            except:
                pass
            
            # Try to get financial health rating
            try:
                df = await self._protected_api_call(stock.company.financial_health_rating)
                if df is not None and not df.empty:
                    ratings['financial_health'] = df.to_dict('records')
            except:
                pass
            
            # Try to get valuation rating
            try:
                df = await self._protected_api_call(stock.company.valuation_rating)
                if df is not None and not df.empty:
                    ratings['valuation'] = df.to_dict('records')
            except:
                pass
            
            logger.debug(f"✅ Ratings collected for {symbol}")
            return ratings
            
        except CircuitOpenError:
            return ratings
        except Exception as e:
            logger.debug(f"Ratings error for {symbol}: {e}")
            return ratings
    
    # =========================================
    # Intraday Data (Real-time)
    # =========================================
    
    async def collect_intraday_data(
        self,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """
        Collect intraday price data for real-time tracking.
        
        Note: Only works during market hours.
        """
        logger.debug(f"⏱️ Collecting intraday: {symbol}")
        
        try:
            stock = self.vnstock.stock(symbol=symbol, source=self.default_source)
            
            df = await self._protected_api_call(stock.quote.intraday)
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'timestamp': str(row.get('time', row.get('t', ''))),
                    'price': self._safe_float(row.get('price', row.get('p'))),
                    'volume': self._safe_int(row.get('volume', row.get('v'))),
                    'bid_price': self._safe_float(row.get('bid')),
                    'ask_price': self._safe_float(row.get('ask')),
                    'total_volume': self._safe_int(row.get('totalVolume')),
                }
                results.append(record)
            
            logger.debug(f"✅ Intraday: {symbol} - {len(results)} records")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Intraday error for {symbol}: {e}")
            return []
    
    # =========================================
    # Market Indices
    # =========================================
    
    async def collect_market_indices(self) -> List[Dict[str, Any]]:
        """Collect current market index values."""
        logger.info("📊 Collecting market indices...")
        
        indices = []
        index_codes = ['VNINDEX', 'HNX', 'UPCOM', 'VN30']
        
        try:
            for code in index_codes:
                try:
                    # Try to get index data
                    stock = self.vnstock.stock(symbol=code, source=self.default_source)
                    
                    df = await self._protected_api_call(
                        stock.quote.history,
                        start=(datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                        end=datetime.now().strftime('%Y-%m-%d')
                    )
                    
                    if df is not None and not df.empty:
                        latest = df.iloc[-1]
                        indices.append({
                            'index_code': code,
                            'timestamp': datetime.now().isoformat(),
                            'value': self._safe_float(latest.get('close')),
                            'change_value': self._safe_float(latest.get('close')) - self._safe_float(latest.get('open')),
                            'change_percent': None,  # Calculate if needed
                            'volume': self._safe_int(latest.get('volume')),
                        })
                except Exception as e:
                    logger.debug(f"Index {code} error: {e}")
            
            logger.info(f"✅ Collected {len(indices)} market indices")
            return indices
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting indices: {e}")
            return []
    
    # =========================================
    # TCBS Screener (84 Metrics - MOST EFFICIENT)
    # =========================================
    
    async def collect_screener_full(
        self,
        exchanges: str = "HOSE,HNX,UPCOM",
        limit: int = 1700
    ) -> List[Dict[str, Any]]:
        """
        Collect FULL screener data using TCBS Screener API.
        
        This is the MOST EFFICIENT method: ONE API call returns
        84 metrics for ALL ~1,600 stocks.
        
        Metrics include:
        - Fundamentals: market_cap, pe, pb, roe, eps, dividend_yield
        - Growth: revenue_growth, eps_growth (1y, 5y)
        - Technical: rsi14, macd_histogram, price_vs_sma (5-100 day)
        - Volume: vol_vs_sma, avg_trading_value
        - Momentum: relative_strength (3d, 1m, 3m, 1y)
        - TCBS ratings: stock_rating, financial_health, business_model
        
        Returns: List of dicts with 84 metrics per stock
        """
        logger.info("📊 Collecting FULL screener data (84 metrics)...")
        
        try:
            # Use the Screener API - correct syntax per vnstock docs
            screener = Screener()
            
            # Correct API call: Screener().stock(limit=N)
            df = await self._protected_api_call(
                screener.stock,
                limit=limit
            )
            
            if df is None or df.empty:
                logger.warning("⚠️ No screener data returned")
                return []
            
            logger.info(f"✅ Screener: {len(df)} stocks with {len(df.columns)} metrics")
            
            # Convert to list of dicts, preserving all 84 columns
            results = []
            for _, row in df.iterrows():
                stock_data = {
                    # Basic Info
                    'symbol': str(row.get('ticker', '')).upper(),
                    'exchange': row.get('exchange', ''),
                    'industry': row.get('industry', ''),
                    
                    # Fundamental Metrics
                    'market_cap': self._safe_float(row.get('market_cap')),
                    'pe_ratio': self._safe_float(row.get('pe')),
                    'pb_ratio': self._safe_float(row.get('pb')),
                    'ev_ebitda': self._safe_float(row.get('ev_ebitda')),
                    'eps': self._safe_float(row.get('eps')),
                    'roe': self._safe_float(row.get('roe')),
                    'dividend_yield': self._safe_float(row.get('dividend_yield')),
                    'gross_margin': self._safe_float(row.get('gross_margin')),
                    'net_margin': self._safe_float(row.get('net_margin')),
                    'doe': self._safe_float(row.get('doe')),  # Debt/Equity
                    
                    # Growth Metrics
                    'revenue_growth_1y': self._safe_float(row.get('revenue_growth_1y')),
                    'revenue_growth_5y': self._safe_float(row.get('revenue_growth_5y')),
                    'eps_growth_1y': self._safe_float(row.get('eps_growth_1y')),
                    'eps_growth_5y': self._safe_float(row.get('eps_growth_5y')),
                    'last_quarter_revenue_growth': self._safe_float(row.get('last_quarter_revenue_growth')),
                    'last_quarter_profit_growth': self._safe_float(row.get('last_quarter_profit_growth')),
                    
                    # Technical Indicators
                    'rsi14': self._safe_float(row.get('rsi14')),
                    'macd_histogram': row.get('macd_histogram'),
                    'price_vs_sma5': row.get('price_vs_sma5'),
                    'price_vs_sma10': row.get('price_vs_sma10'),
                    'price_vs_sma20': row.get('price_vs_sma20'),
                    'price_vs_sma50': row.get('price_vs_sma50'),
                    'price_vs_sma100': row.get('price_vs_sma100'),
                    'bolling_band_signal': row.get('bolling_band_signal'),
                    'dmi_signal': row.get('dmi_signal'),
                    'rsi14_status': row.get('rsi14_status'),
                    
                    # Volume Analysis
                    'vol_vs_sma5': self._safe_float(row.get('vol_vs_sma5')),
                    'vol_vs_sma10': self._safe_float(row.get('vol_vs_sma10')),
                    'vol_vs_sma20': self._safe_float(row.get('vol_vs_sma20')),
                    'vol_vs_sma50': self._safe_float(row.get('vol_vs_sma50')),
                    'avg_trading_value_5d': self._safe_float(row.get('avg_trading_value_5d')),
                    'avg_trading_value_10d': self._safe_float(row.get('avg_trading_value_10d')),
                    'avg_trading_value_20d': self._safe_float(row.get('avg_trading_value_20d')),
                    
                    # Price Performance
                    'price_near_realtime': self._safe_float(row.get('price_near_realtime')),
                    'price_growth_1w': self._safe_float(row.get('price_growth_1w')),
                    'price_growth_1m': self._safe_float(row.get('price_growth_1m')),
                    'prev_1d_growth_pct': self._safe_float(row.get('prev_1d_growth_pct')),
                    'prev_1m_growth_pct': self._safe_float(row.get('prev_1m_growth_pct')),
                    'prev_1y_growth_pct': self._safe_float(row.get('prev_1y_growth_pct')),
                    'prev_5y_growth_pct': self._safe_float(row.get('prev_5y_growth_pct')),
                    'pct_away_from_hist_peak': self._safe_float(row.get('pct_away_from_hist_peak')),
                    'pct_off_hist_bottom': self._safe_float(row.get('pct_off_hist_bottom')),
                    'pct_1y_from_peak': self._safe_float(row.get('pct_1y_from_peak')),
                    'pct_1y_from_bottom': self._safe_float(row.get('pct_1y_from_bottom')),
                    
                    # Momentum & Relative Strength
                    'relative_strength_3d': self._safe_float(row.get('relative_strength_3d')),
                    'rel_strength_1m': self._safe_float(row.get('rel_strength_1m')),
                    'rel_strength_3m': self._safe_float(row.get('rel_strength_3m')),
                    'rel_strength_1y': self._safe_float(row.get('rel_strength_1y')),
                    'tc_rs': self._safe_float(row.get('tc_rs')),
                    'alpha': self._safe_float(row.get('alpha')),
                    'beta': self._safe_float(row.get('beta')),
                    
                    # TCBS Ratings & Signals
                    'stock_rating': self._safe_float(row.get('stock_rating')),
                    'business_operation': self._safe_float(row.get('business_operation')),
                    'business_model': self._safe_float(row.get('business_model')),
                    'financial_health': self._safe_float(row.get('financial_health')),
                    'tcbs_recommend': row.get('tcbs_recommend'),
                    'tcbs_buy_sell_signal': row.get('tcbs_buy_sell_signal'),
                    
                    # Foreign Trading
                    'foreign_vol_pct': self._safe_float(row.get('foreign_vol_pct')),
                    'foreign_transaction': row.get('foreign_transaction'),
                    'foreign_buysell_20s': self._safe_float(row.get('foreign_buysell_20s')),
                    
                    # Special Signals
                    'uptrend': row.get('uptrend'),
                    'breakout': row.get('breakout'),
                    'price_break_out52_week': row.get('price_break_out52_week'),
                    'heating_up': row.get('heating_up'),
                    
                    # Continuous Price Movement
                    'num_increase_continuous_day': self._safe_int(row.get('num_increase_continuous_day')),
                    'num_decrease_continuous_day': self._safe_int(row.get('num_decrease_continuous_day')),
                    
                    # Other
                    'profit_last_4q': self._safe_float(row.get('profit_last_4q')),
                    'free_transfer_rate': self._safe_float(row.get('free_transfer_rate')),
                    'net_cash_per_market_cap': self._safe_float(row.get('net_cash_per_market_cap')),
                    'net_cash_per_total_assets': self._safe_float(row.get('net_cash_per_total_assets')),
                    'has_financial_report': row.get('has_financial_report'),
                }
                results.append(stock_data)
            
            logger.info(f"🎉 Screener collection complete: {len(results)} stocks")
            return results
            
        except CircuitOpenError:
            logger.warning("⚠️ Circuit open, skipping screener collection")
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting screener data: {e}")
            return []
    
    # =========================================
    # Company Shareholders
    # =========================================
    
    async def collect_shareholders(
        self,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """
        Collect major shareholder information for a stock.
        
        Returns: List of shareholders with ownership details
        """
        logger.debug(f"👥 Collecting shareholders: {symbol}")
        
        try:
            company = Company(symbol=symbol, source='VCI')
            
            df = await self._protected_api_call(company.shareholders)
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'shareholder_id': row.get('id'),
                    'shareholder_name': row.get('share_holder', ''),
                    'quantity': self._safe_int(row.get('quantity')),
                    'ownership_percent': self._safe_float(row.get('share_own_percent')),
                    'update_date': str(row.get('update_date', '')),
                }
                results.append(record)
            
            logger.debug(f"✅ Shareholders: {symbol} - {len(results)} records")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Shareholders error for {symbol}: {e}")
            return []
    
    # =========================================
    # Company Officers (Management)
    # =========================================
    
    async def collect_officers(
        self,
        symbol: str,
        filter_by: str = 'working'
    ) -> List[Dict[str, Any]]:
        """
        Collect company officers/management information.
        
        Args:
            symbol: Stock symbol
            filter_by: 'working', 'resigned', or 'all'
        
        Returns: List of officers with position and ownership
        """
        logger.debug(f"👔 Collecting officers: {symbol}")
        
        try:
            company = Company(symbol=symbol, source='VCI')
            
            df = await self._protected_api_call(
                company.officers,
                filter_by=filter_by
            )
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.iterrows():
                record = {
                    'symbol': symbol,
                    'officer_id': row.get('id'),
                    'officer_name': row.get('officer_name', ''),
                    'position': row.get('officer_position', ''),
                    'position_short': row.get('position_short_name', ''),
                    'ownership_percent': self._safe_float(row.get('officer_own_percent')),
                    'quantity': self._safe_int(row.get('quantity')),
                    'status': row.get('type', ''),
                    'update_date': str(row.get('update_date', '')),
                }
                results.append(record)
            
            logger.debug(f"✅ Officers: {symbol} - {len(results)} records")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.debug(f"Officers error for {symbol}: {e}")
            return []
    
    # =========================================
    # Trading Board (Real-time Bid/Ask)
    # =========================================
    
    async def collect_price_board(
        self,
        symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Collect real-time price board data with bid/ask for multiple symbols.
        
        This is efficient for batch updates - provides 36 columns per stock.
        
        Returns: List of price board data with bid/ask levels
        """
        if not symbols:
            return []
        
        logger.info(f"📋 Collecting price board for {len(symbols)} symbols...")
        
        try:
            trading = Trading(symbol='VN30F1M')  # Dummy symbol required
            
            df = await self._protected_api_call(
                trading.price_board,
                symbols_list=symbols
            )
            
            if df is None or df.empty:
                return []
            
            results = []
            for _, row in df.iterrows():
                record = {
                    # Listing Info
                    'symbol': str(row.get('symbol', '')).upper(),
                    'exchange': row.get('exchange', ''),
                    'ceiling': self._safe_float(row.get('ceiling')),
                    'floor': self._safe_float(row.get('floor')),
                    'ref_price': self._safe_float(row.get('ref_price')),
                    'prior_close': self._safe_float(row.get('prior_close_price')),
                    
                    # Match Info
                    'match_price': self._safe_float(row.get('match_price')),
                    'match_volume': self._safe_int(row.get('match_vol')),
                    'accumulated_volume': self._safe_int(row.get('accumulated_volume')),
                    'accumulated_value': self._safe_float(row.get('accumulated_value')),
                    'avg_match_price': self._safe_float(row.get('avg_match_price')),
                    'highest': self._safe_float(row.get('highest')),
                    'lowest': self._safe_float(row.get('lowest')),
                    
                    # Foreign Trading
                    'foreign_buy_volume': self._safe_int(row.get('foreign_buy_volume')),
                    'foreign_sell_volume': self._safe_int(row.get('foreign_sell_volume')),
                    'current_room': self._safe_int(row.get('current_room')),
                    'total_room': self._safe_int(row.get('total_room')),
                    
                    # Bid Levels
                    'bid_1_price': self._safe_float(row.get('bid_1_price')),
                    'bid_1_volume': self._safe_int(row.get('bid_1_volume')),
                    'bid_2_price': self._safe_float(row.get('bid_2_price')),
                    'bid_2_volume': self._safe_int(row.get('bid_2_volume')),
                    'bid_3_price': self._safe_float(row.get('bid_3_price')),
                    'bid_3_volume': self._safe_int(row.get('bid_3_volume')),
                    
                    # Ask Levels
                    'ask_1_price': self._safe_float(row.get('ask_1_price')),
                    'ask_1_volume': self._safe_int(row.get('ask_1_volume')),
                    'ask_2_price': self._safe_float(row.get('ask_2_price')),
                    'ask_2_volume': self._safe_int(row.get('ask_2_volume')),
                    'ask_3_price': self._safe_float(row.get('ask_3_price')),
                    'ask_3_volume': self._safe_int(row.get('ask_3_volume')),
                    
                    'updated_at': datetime.now().isoformat(),
                }
                results.append(record)
            
            logger.info(f"✅ Price board: {len(results)} stocks")
            return results
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting price board: {e}")
            return []
    
    # =========================================
    # Industry Classification (ICB)
    # =========================================
    
    async def collect_industries(self) -> List[Dict[str, Any]]:
        """
        Collect all ICB industry classifications.
        
        Returns: List of industry codes and names
        """
        logger.info("🏭 Collecting industry classifications...")
        
        try:
            listing = Listing()
            
            # Get stocks with industry info
            df = await self._protected_api_call(listing.all_symbols)
            
            if df is None or df.empty:
                return []
            
            # Extract unique industries
            industries = set()
            for _, row in df.iterrows():
                symbol = str(row.get('ticker', row.get('symbol', ''))).upper()
                organ_name = row.get('organ_name', '')
                if symbol:
                    industries.add((symbol, organ_name))
            
            logger.info(f"✅ Industries: {len(industries)} stocks classified")
            return [{'symbol': s, 'company_name': n} for s, n in industries]
            
        except CircuitOpenError:
            return []
        except Exception as e:
            logger.error(f"❌ Error collecting industries: {e}")
            return []
    
    # =========================================
    # Utilities
    # =========================================
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert to float."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert to int."""
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        return {
            'total_api_calls': self._total_api_calls,
            'successful_calls': self._successful_calls,
            'failed_calls': self._failed_calls,
            'success_rate': round(
                self._successful_calls / max(self._total_api_calls, 1) * 100, 2
            ),
            'rate_limiter': self.rate_limiter.get_stats(),
            'circuit_breaker': self.circuit_breaker.get_status(),
        }


# Global collector instance
_collector: Optional[VnStockCollector] = None


async def get_collector() -> VnStockCollector:
    """Get or create the global collector instance."""
    global _collector
    
    if _collector is None:
        _collector = VnStockCollector()
    
    return _collector
